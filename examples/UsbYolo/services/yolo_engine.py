# -*- coding: utf-8 -*-
"""YOLO 检测引擎（统一入口）：按配置选择推理后端，检测 → 画框 → 结果数据。

后端选择（pipeline.json 注入）：
    1. gpu_python（如 D:/AIProgram/python.exe，CUDA）→ 拉起 GPU worker 子进程
       转发推理（算法进程本身无 GPU 时的路径；worker 脚本 gpu_worker.py 独立运行，
       协议见该文件）
    2. device="openvino" → 本进程 OpenVINO IR（.pt 首次自动导出，CPU 加速）
    3. device="auto"/"0"/"cpu" → 本进程 PyTorch（auto = 有 CUDA 走 GPU）

三种后端统一返回 (结果图, {"detections", "count", "time_ms"})；画框与计时都在
本进程做（time_ms = 端到端推理+画框耗时）。模型/worker 由 preload() 在进程
一开始预加载，之后每帧 process() 只做状态检查。

注意：本模块在 HRVision（3.12）与 AI 环境（3.9）都会运行——联合类型注解
必须用字符串形式（"X | Y"），不要用 3.10+ 语法。
"""
import json
import os
import threading

import cv2
import numpy as np
from ultralytics import YOLO
from HRVision.ExternalWorker import ExternalWorker

cv2.setNumThreads(1)   # 进程模式多消费者：限制 OpenCV 线程池爆炸

_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "gpu_worker.py")
_WORKER_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "gpu_worker.log")
_READY_DEADLINE = 40.0   # worker 首次启动：python3.9 + torch 导入 + 模型加载 ~5-15s


class YoloEngine:
    """类级单例引擎：本进程模型 + GPU worker 各缓存一份，进程存活期只初始化一次。"""

    # ---- 本进程模型（PyTorch / OpenVINO 后端） ----
    _model: "YOLO | None" = None
    _model_path: str = ""
    _device: str = ""

    # ---- GPU worker 后端状态（ExternalWorker 工具封装：拉起/握手/重启） ----
    _wlock = threading.Lock()
    _worker = None         # ExternalWorker | None
    _wgpu_python: str = ""
    _wmodel_path: str = ""

    # =====================================================================
    # 统一入口
    # =====================================================================

    @classmethod
    def preload(cls, model_path: str, device: str = "auto",
                gpu_python: "str | None" = None) -> None:
        """进程一开始预加载推理后端（模型加载 ~3s，与首帧到达并行）。

        gpu_python 配置 → 拉起 GPU worker 并加载模型（READY 即就绪）；
        否则本进程加载模型（device 决定 PyTorch GPU/CPU 或 OpenVINO）。
        """
        if gpu_python:
            cls._worker_ensure(gpu_python, model_path)
            print("[yolo] GPU worker 就绪（模型已加载）", flush=True)
        else:
            cls.ensure_model(model_path, device)

    @classmethod
    def process(cls, frame: np.ndarray, model_path: str, conf: float,
                imgsz: int, device: str = "auto",
                gpu_python: "str | None" = None) -> "tuple[np.ndarray, dict]":
        """检测 + 画框；返回 (结果图, 检测数据)。

        结果数据（SignalProgram 小数据）：
            {"detections": [{"cls", "conf", "box": [x1,y1,x2,y2]}], "count", "time_ms"}
        time_ms 为端到端耗时（推理 + 画框，含 worker 转发开销）。
        """
        t0: float = cv2.getTickCount()
        if gpu_python:
            result = cls._predict_worker(frame, gpu_python, model_path, conf, imgsz)
        else:
            result = cls._predict_local(frame, model_path, conf, imgsz, device)
        cls._draw(frame, result["detections"])
        result["time_ms"] = round((cv2.getTickCount() - t0)
                                  / cv2.getTickFrequency() * 1000, 1)
        return frame, result

    @staticmethod
    def _draw(frame: np.ndarray, detections: list) -> None:
        """在帧上画检测框 + 标签（两种后端共用）。"""
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                          (0, 255, 0), 2)
            cv2.putText(frame, "%s %.2f" % (d["cls"], d["conf"]),
                        (int(x1), int(y1) - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 255), 2)

    # =====================================================================
    # 本进程后端（PyTorch / OpenVINO）
    # =====================================================================

    @classmethod
    def ensure_model(cls, model_path: str, device: str = "auto") -> None:
        """按需加载模型（路径/设备变化时重载）。device="openvino" 时 .pt 先导出 IR。"""
        if cls._model is None or cls._model_path != model_path:
            ov_dir = ""
            if device == "openvino" and model_path.endswith(".pt"):
                ov_dir = model_path[:-3] + "_openvino_model"
                if not os.path.isdir(ov_dir):
                    print("[yolo] 首次导出 OpenVINO 模型: %s → %s（一次性，约 20s）"
                          % (model_path, ov_dir), flush=True)
                    YOLO(model_path).export(format="openvino", imgsz=640, half=False)
            cls._model = YOLO(ov_dir) if ov_dir and os.path.isdir(ov_dir) \
                else YOLO(model_path)
            cls._model_path = model_path
            cls._device = device
            print("[yolo] 模型加载: %s（推理设备 %s）" % (
                model_path, cls._resolve_device(device)), flush=True)

    @staticmethod
    def _resolve_device(device: str) -> str:
        """解析设备参数：auto → GPU 可用则 "0" 否则 "cpu"；其余原样。"""
        if device == "auto":
            try:
                import torch
                return "0" if torch.cuda.is_available() else "cpu"
            except Exception:
                return "cpu"
        return device

    @classmethod
    def _predict_local(cls, frame: np.ndarray, model_path: str,
                       conf: float, imgsz: int, device: str) -> dict:
        """本进程 ultralytics 推理 → 检测数据（不含画框/计时，由入口统一做）。"""
        cls.ensure_model(model_path, device)
        results = cls._model.predict(frame, conf=conf, imgsz=imgsz,
                                     verbose=False, device=cls._resolve_device(device))
        dets: list[dict] = []
        for r in results:
            names: dict = r.names
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id: int = int(box.cls[0])
                score: float = float(box.conf[0])
                dets.append({"cls": names[cls_id], "conf": round(score, 3),
                             "box": [round(v, 1) for v in (x1, y1, x2, y2)]})
        return {"detections": dets, "count": len(dets)}

    # =====================================================================
    # GPU worker 后端（转发推理；worker 脚本 gpu_worker.py 在 GPU 环境运行）
    # =====================================================================

    @classmethod
    def _worker_ensure(cls, gpu_python: str, model_path: str) -> None:
        """按需拉起 worker（ExternalWorker：拉起/握手/自动重启/清理）。"""
        with cls._wlock:
            if (cls._worker is not None and cls._wgpu_python == gpu_python
                    and cls._wmodel_path == model_path):
                return
            cls._worker_close()
            cls._worker = ExternalWorker(
                launch=[gpu_python, "-u", _WORKER_SCRIPT, model_path],
                ready_timeout=_READY_DEADLINE, log_path=_WORKER_LOG)
            cls._worker.start()
            cls._wgpu_python = gpu_python
            cls._wmodel_path = model_path

    @classmethod
    def _worker_close(cls) -> None:
        if cls._worker is not None:
            cls._worker.close()
            cls._worker = None
        cls._wmodel_path = ""

    @classmethod
    def _predict_worker(cls, frame: np.ndarray, gpu_python: str,
                        model_path: str, conf: float, imgsz: int) -> dict:
        """转发推理 → 检测数据（ExternalWorker 内置通信失败自动重启重试）。"""
        cls._worker_ensure(gpu_python, model_path)
        h, w = frame.shape[:2]
        header = json.dumps({"w": w, "h": h, "ch": frame.shape[2],
                             "conf": conf, "imgsz": imgsz}).encode("utf-8")
        assert cls._worker is not None
        result = json.loads(cls._worker.call(
            [header, frame.tobytes()]).decode("utf-8"))
        return result
