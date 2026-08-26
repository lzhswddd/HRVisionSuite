# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase
from services.camera_driver import CameraDriver
from HRVision.HRFlowController import _ChannelOut


class ThreadData(ThreadDataBase):
    """相机流程实例数据（source/cam_str 等由管线启动时 kwargs 注入）。"""

    source: str | None          # 视频源（相对 Flow/，spec 节点参数注入）
    camera: CameraDriver | None  # 相机驱动实例（视频流相机，缓存）
    cam_str: str                 # 节点 id（打印标识）
    frame_interval: float        # 帧间隔秒（0=不限速压力测试）
    display_divisor: int         # 显示通道降频（每 N 帧写一次）
    channel_out: _ChannelOut     # 聚合写通道（框架注入：put 队列 / write 映射）
    loop_count: int              # 抓帧计数

    def __init__(self):
        super().__init__()
        self.source = None
        self.camera = None
        self.cam_str = "CCD1"
        self.frame_interval = 0.0
        self.display_divisor = 3
        self.loop_count = 0


thData = ThreadData()
