# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase, _ChannelIn, _ChannelOut


class ThreadData(ThreadDataBase):
    """算法流程实例数据（model_path 等由管线启动时 kwargs 注入）。"""

    cam_str: str            # 节点 id（打印标识）
    algo_key: str           # 算法实例唯一标识（UI 窗格/信号标识，如 yolo_1）
    model_path: str         # YOLO 模型路径（D:/AiProgram/yolov8n.pt 等）
    conf: float             # 检测置信度阈值
    imgsz: int              # 推理输入尺寸（640）
    device: str             # 推理设备：auto（有 CUDA 用 GPU）/ 0 / cpu / openvino
    gpu_python: "str | None"  # GPU 环境 python（如 D:/AIProgram/python.exe，有 CUDA）；
                            # 非 None 时推理转发给该环境拉起的 GPU worker
    signal_divisor: int     # 输出降频（每 N 帧写一次显示槽 / 发一次结果信号）
    channel_in: _ChannelIn  # 聚合读通道（框架注入：get 取输入）
    channel_out: _ChannelOut  # 聚合写通道（框架注入：write 推输出）
    signal_count: int       # 处理计数（降频/信号节流用）

    def __init__(self):
        super().__init__()
        self.cam_str = "yolo_1"
        self.algo_key = "yolo_1"
        self.model_path = "D:/AiProgram/yolov8n.pt"
        self.conf = 0.25
        self.imgsz = 640
        self.device = "auto"
        self.gpu_python = None    # 由 pipeline.json 注入（None = 本进程 OpenVINO/PyTorch 推理）
        self.signal_divisor = 1   # 输出降频（每 N 帧写一次显示槽；提速后每帧写）
        self.signal_count = 0


thData = ThreadData()
