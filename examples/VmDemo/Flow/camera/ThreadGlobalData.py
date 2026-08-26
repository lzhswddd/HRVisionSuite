# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase
from services.vm_bridge import VmBridge
from HRVision.HRFlowController import _ChannelOut


class ThreadData(ThreadDataBase):
    """相机流程实例数据（vm_mode 等由管线启动时 kwargs 注入）。"""

    vm_mode: str               # vm（真实 VM）/ sim（模拟）
    sim_source: str            # sim 模式视频源（相对 Flow/）
    sim_fps: float             # sim 模式帧率（模拟相机节奏，0=不限速）
    vm_solution: str           # vm 模式方案文件路径（空=默认；方案相机=VM 全局相机）
    vm_procedure: str          # vm 模式流程文件路径（空=默认）
    vm: VmBridge | None        # VM 桥接实例（缓存，进程存活期）
    cam_str: str               # 节点 id（打印标识）
    display_divisor: int       # 显示通道降频（每 N 帧写一次）
    channel_out: _ChannelOut   # 聚合写通道（框架注入：put 队列 / write 映射）
    loop_count: int            # 收图计数

    def __init__(self):
        super().__init__()
        self.vm_mode = "sim"
        self.sim_source = "videos/vm1.avi"
        self.sim_fps = 25.0
        self.vm_solution = ""
        self.vm_procedure = ""
        self.vm = None
        self.cam_str = "grab_0"
        self.display_divisor = 3
        self.loop_count = 0


thData = ThreadData()
