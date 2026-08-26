# -*- coding: utf-8 -*-
"""VM（VisionMaster）桥接：采图 / 算法 / 通信结果。

两种模式（pipeline.json 节点参数 vm_mode）：
    vm  : 真实 VM —— 方案相机使用 **VM 全局相机**（在 VM 软件「设置-全局相机」注册，
          方案内相机模块配置为引用该全局相机）；流程端 createSolution/loadSolution
          加载方案 → runProcedure() 按方案配置采图 → processProcedure 推图处理
          （算法在 VM 方案内）→ 结果经 VM 通信设备发出（commSendBytes/commSetInt）
    sim : 模拟模式（无 VM SDK/方案环境演示）——本地视频流模拟 VM 采图，
          本地轻量检测链模拟 VM 算法，通信结果打印并计入结果数据

真实模式依赖（PyHRVision/HRVision）：
    VisionMasterProcess  —— 方案/流程加载、采图、推图处理、取结果
    VisionMasterCore     —— 方案对象（createSolution/loadSolution）+ 通信设备
"""
import json

import cv2
import numpy as np

cv2.setNumThreads(1)   # 进程模式多消费者：限制 OpenCV 线程池爆炸


class VmBridge:
    """VM 桥接：grab() 采图 / process() 算法 / send_result() 通信结果。"""

    def __init__(self, mode: str = "sim", sim_source: str = "",
                 sim_fps: float = 25.0, vm_solution: str = "",
                 vm_procedure: str = "",
                 vm_resource_module: str = "ImageSource",
                 vm_device_id: int = 1):
        self.mode: str = mode
        self.sim_source: str = sim_source
        self.sim_fps: float = sim_fps
        self.vm_solution: str = vm_solution
        self.vm_procedure: str = vm_procedure
        self.vm_resource_module: str = vm_resource_module
        self.vm_device_id: int = vm_device_id
        self._vm_proc = None      # VisionMasterProcess 实例（vm 模式）
        self._vm_core = None      # VisionMasterCore 实例（vm 模式）
        self._sim_cap: cv2.VideoCapture | None = None   # sim 模式视频源
        self._sim_t0: float = 0.0                       # sim 帧率节流计时
        self._tmpl: np.ndarray | None = None            # sim 算法模板（首帧校准）
        self._init_vm() if mode == "vm" else self._init_sim()

    # ---------- 初始化 ----------

    def _init_vm(self) -> None:
        """vm 模式：加载 VM 方案（相机/算法都在方案里）。

        方案相机使用 **VM 全局相机**：在 VM 软件「设置-全局相机」注册相机，
        方案内相机模块配置为引用该全局相机；此处只需加载方案文件。
        """
        try:
            from HRVision.VisionMasterProcess import VisionMasterProcess
            from HRVision.VisionMasterCore import VisionMasterCore
            self._vm_proc = VisionMasterProcess()
            self._vm_core = VisionMasterCore()
            if self.vm_solution:
                self._vm_core.createSolution()
                ret = self._vm_core.loadSolution(self.vm_solution)
                if ret != 0:
                    raise RuntimeError("loadSolution 失败（返回值 %s）: %s"
                                       % (ret, self.vm_solution))
            if self.vm_procedure:
                ret2 = self._vm_proc.loadProcedure(self.vm_procedure)
                if ret2 != 0:
                    raise RuntimeError("loadProcedure 失败（返回值 %s）: %s"
                                       % (ret2, self.vm_procedure))
            print("[vm] VM 方案加载: %s%s（方案相机 = VM 全局相机）" % (
                self.vm_solution or "(默认方案)", self.vm_procedure or ""), flush=True)
        except Exception as e:
            raise RuntimeError("VM 初始化失败（检查 VM SDK/方案/全局相机）: %s" % e)

    def _init_sim(self) -> None:
        """sim 模式：本地视频流模拟 VM 采图。"""
        if not self.sim_source:
            raise RuntimeError("sim 模式需要 sim_source（视频文件，如 videos/vm1.avi）")
        self._sim_cap = cv2.VideoCapture(self.sim_source)
        if not self._sim_cap.isOpened():
            raise RuntimeError("sim 视频打开失败: %s" % self.sim_source)
        print("[vm] 模拟模式（无 VM）：%s" % self.sim_source, flush=True)

    # ---------- 采图（VM 调用相机） ----------

    def grab(self) -> np.ndarray | None:
        """取一帧图像（vm 模式走 VM 方案采图；sim 模式读本地视频）。"""
        if self.mode == "vm":
            try:
                assert self._vm_proc is not None
                if not self._vm_proc.runProcedure():
                    return None
                out = self._vm_proc.getOutputReult()
                img = out.get("Image") or out.get("image")
                if img is None:
                    return None
                return np.ascontiguousarray(np.asarray(img))
            except Exception:
                return None
        assert self._sim_cap is not None
        # 帧率节流：模拟真实相机节奏（sim_fps，0=不限速）
        if self.sim_fps > 0:
            import time as _t
            wait = 1.0 / self.sim_fps - (_t.time() - self._sim_t0)
            if wait > 0:
                _t.sleep(wait)
            self._sim_t0 = _t.time()
        ok, frame = self._sim_cap.read()
        if not ok or frame is None:
            self._sim_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)   # 播完回卷
            ok, frame = self._sim_cap.read()
            if not ok or frame is None:
                return None
        return np.ascontiguousarray(frame)

    # ---------- 算法（VM 方案处理 / 本地轻量检测） ----------

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """调用算法；返回 (结果图, 结果数据)。"""
        if self.mode == "vm":
            return self._process_vm(frame)
        return self._process_sim(frame)

    def _process_vm(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """推图进 VM 方案处理（算法在 VM 方案内），取模块输出。"""
        try:
            assert self._vm_proc is not None
            t0: float = cv2.getTickCount()
            ok = self._vm_proc.processProcedure(frame, self.vm_resource_module)
            out = self._vm_proc.getOutputReult()
            time_ms: float = round((cv2.getTickCount() - t0)
                                   / cv2.getTickFrequency() * 1000, 1)
            return frame, {"ok": bool(ok), "vm_result": dict(out),
                           "time_ms": time_ms, "mode": "vm"}
        except Exception as e:
            return frame, {"ok": False, "error": str(e), "mode": "vm"}

    def _process_sim(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """本地轻量检测链（模板匹配，模拟 VM 算法）；结果图标注。"""
        t0: float = cv2.getTickCount()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi = gray[h // 4:h // 4 + h // 3, w // 4:w // 4 + w // 3]
        if self._tmpl is None:
            self._tmpl = roi.copy()
            ok: bool = True
            score: float = 1.0
        else:
            res = cv2.matchTemplate(roi, self._tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            score = float(max_val)
            ok = score >= 0.8
        color = (0, 255, 0) if ok else (0, 0, 255)
        cv2.rectangle(frame, (w // 4, h // 4), (w // 4 + w // 3, h // 4 + h // 3),
                      color, 2)
        cv2.putText(frame, "SIM %s %.3f" % ("OK" if ok else "NG", score),
                    (w // 4, h // 4 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        time_ms = round((cv2.getTickCount() - t0) / cv2.getTickFrequency() * 1000, 1)
        return frame, {"ok": ok, "score": round(score, 3), "time_ms": time_ms,
                       "mode": "sim"}

    # ---------- 通信结果（发送 vm 的通信结果） ----------

    def send_result(self, result: dict) -> str:
        """把结果发给 VM 通信设备；返回发送描述。

        vm 模式：commSendBytes(JSON) + commSetInt([ok])；
        sim 模式：打印 + 记录（演示）。
        """
        if self.mode == "vm":
            try:
                assert self._vm_core is not None
                payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                n1 = self._vm_core.commSendBytes(self.vm_device_id, payload)
                n2 = self._vm_core.commSetInt(self.vm_device_id,
                                              [1 if result.get("ok") else 0])
                return "VM 通信发送 bytes=%d int=%d (device %d)" % (
                    n1, n2, self.vm_device_id)
            except Exception as e:
                return "VM 通信失败: %s" % e
        return "SIM 通信: %s (device %d)" % (
            "OK" if result.get("ok") else "NG", self.vm_device_id)
