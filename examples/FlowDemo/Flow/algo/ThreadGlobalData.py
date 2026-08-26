# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase, _ChannelIn, _ChannelOut


class ThreadData(ThreadDataBase):
    """算法流程实例数据（algo_load/algo_key 等由管线启动时 kwargs 注入）。"""

    cam_str: str            # 节点 id（打印标识）
    algo_key: str           # 算法实例唯一标识（UI 窗格/信号标识，如 algo_1）
    algo_load: int          # 算法负载强度（处理循环次数）
    signal_divisor: int     # 输出降频（每 N 帧写一次显示槽 / 发一次结果信号）
    channel_in: _ChannelIn  # 聚合读通道（框架注入：get 取输入）
    channel_out: _ChannelOut  # 聚合写通道（框架注入：write 推输出）
    signal_count: int       # 处理计数（降频/信号节流用）

    def __init__(self):
        super().__init__()
        self.cam_str = "CCD1"
        self.algo_key = "CCD1_A0"
        self.algo_load = 1
        self.signal_divisor = 1
        self.signal_count = 0


thData = ThreadData()
