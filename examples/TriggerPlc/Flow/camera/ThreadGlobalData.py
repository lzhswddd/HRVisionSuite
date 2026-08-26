# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase
from services.camera_driver import CameraDriver
from services.plc import Plc, MockPlcServer
from HRVision.HRFlowController import _ChannelOut


class ThreadData(ThreadDataBase):
    """相机流程实例数据（source/plc_* 等由管线启动时 kwargs 注入）。"""

    source: str | None           # 视频源（相对 Flow/，spec 节点参数注入）
    camera: CameraDriver | None  # 相机驱动实例（缓存）
    cam_str: str                 # 节点 id（打印标识）
    # PLC 参数（cModule/PLCInterface 库）
    plc_mode: str                # mock（内置从站模拟 PLC）/ tcp（真实 PLC）
    plc_type: str                # 协议：Modbus / ModbusRtu / Profinet_* 等
    plc_host: str                # PLC 地址
    plc_port: int                # PLC 端口
    trigger_addr: str            # 触发拍照地址（HslCommunication 语义，如 "0" 线圈 / "M100"）
    ok_addr: str                 # OK 结果地址
    ng_addr: str                 # NG 结果地址
    addr_type: str               # 读写类型（bool/short/int/float）
    auto_trigger_ms: int         # 自动触发间隔（0=只等 PLC 触发）
    plc: Plc | None              # PLC 客户端（缓存，初始化一次）
    plc_server: MockPlcServer | None  # mock 模式内置从站（缓存）
    # 显示/计数
    display_divisor: int         # 显示通道降频（每 N 帧写一次）
    channel_out: _ChannelOut     # 聚合写通道（框架注入：put 队列 / write 映射）
    loop_count: int              # 拍照计数
    trigger_count: int           # 触发计数
    trigger_t0: float            # 自动触发计时起点

    def __init__(self):
        super().__init__()
        self.source = None
        self.camera = None
        self.cam_str = "grab_0"
        self.plc_mode = "mock"
        self.plc_type = "Modbus"
        self.plc_host = "127.0.0.1"
        self.plc_port = 8000
        self.trigger_addr = "0"
        self.ok_addr = "1"
        self.ng_addr = "2"
        self.addr_type = "bool"
        self.auto_trigger_ms = 1000
        self.plc = None
        self.plc_server = None
        self.display_divisor = 3
        self.loop_count = 0
        self.trigger_count = 0
        self.trigger_t0 = 0.0


thData = ThreadData()
