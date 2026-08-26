# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase
from services.camera_driver import UsbCamera
from HRVision.HRFlowController import _ChannelOut


class ThreadData(ThreadDataBase):
    """相机流程实例数据（source 等由管线启动时 kwargs 注入）。"""

    source: str | None            # 视频源（"usb:N" 或视频文件，spec 节点参数注入）
    width: int                    # USB 相机宽（0=相机默认）
    height: int                   # USB 相机高（0=相机默认）
    camera: UsbCamera | None      # 相机驱动实例（缓存）
    cam_str: str                  # 节点 id（打印标识）
    display_divisor: int          # 显示通道降频（每 N 帧写一次）
    channel_out: _ChannelOut      # 聚合写通道（框架注入：put 队列 / write 映射）
    loop_count: int               # 抓帧计数

    def __init__(self):
        super().__init__()
        self.source = None
        self.width = 0
        self.height = 0
        self.camera = None
        self.cam_str = "grab_0"
        self.display_divisor = 3
        self.loop_count = 0


thData = ThreadData()
