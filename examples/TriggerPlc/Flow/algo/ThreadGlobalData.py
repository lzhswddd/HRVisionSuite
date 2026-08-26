# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase, _ChannelIn, _ChannelOut
from services.plc import Plc


class ThreadData(ThreadDataBase):
    """算法流程实例数据（algo_load 等由管线启动时 kwargs 注入）。"""

    cam_str: str            # 节点 id（打印标识）
    algo_key: str           # 算法实例唯一标识（UI 窗格/信号标识，如 algo_1）
    algo_load: int          # 算法负载强度（处理循环次数）
    judge_threshold: float  # OK/NG 判定阈值（模板匹配分）
    signal_divisor: int     # 输出降频（每 N 帧写一次显示槽 / 发一次结果信号）
    # PLC 参数（与相机节点一致：判定结果写 OK/NG 地址）
    plc_type: str
    plc_host: str
    plc_port: int
    ok_addr: str
    ng_addr: str
    addr_type: str
    plc: Plc | None         # PLC 客户端（缓存）
    channel_in: _ChannelIn  # 聚合读通道（框架注入：get 取输入）
    channel_out: _ChannelOut  # 聚合写通道（框架注入：write 推输出）
    signal_count: int       # 处理计数（降频/信号节流用）

    def __init__(self):
        super().__init__()
        self.cam_str = "algo_1"
        self.algo_key = "algo_1"
        self.algo_load = 1
        self.judge_threshold = 0.8
        self.signal_divisor = 1
        self.plc_type = "Modbus"
        self.plc_host = "127.0.0.1"
        self.plc_port = 8000
        self.ok_addr = "1"
        self.ng_addr = "2"
        self.addr_type = "bool"
        self.plc = None
        self.signal_count = 0


thData = ThreadData()
