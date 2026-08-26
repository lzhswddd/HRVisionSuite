# -*- coding: utf-8 -*-
from ProgramGlobalData import *
from HRVision.HRFlowController import ThreadDataBase, _ChannelIn, _ChannelOut
from services.vm_bridge import VmBridge


class ThreadData(ThreadDataBase):
    """算法流程实例数据（vm_mode 等由管线启动时 kwargs 注入）。"""

    cam_str: str               # 节点 id（打印标识）
    algo_key: str              # 算法实例唯一标识（UI 窗格/信号标识，如 algo_1）
    vm_mode: str               # vm（真实 VM）/ sim（模拟）
    sim_source: str            # sim 模式视频源（相对 Flow/，与相机节点一致）
    vm_solution: str           # vm 模式方案文件路径（空=默认；方案相机=VM 全局相机）
    vm_procedure: str          # vm 模式流程文件路径（空=默认）
    vm_resource_module: str    # vm 模式推图资源模块名（方案内图像源模块）
    vm_device_id: int          # vm 通信设备 id（VisionMasterCore 通信对象）
    signal_divisor: int        # 输出降频（每 N 帧写一次显示槽 / 发一次结果信号）
    vm: VmBridge | None        # VM 桥接实例（缓存，进程存活期）
    channel_in: _ChannelIn     # 聚合读通道（框架注入：get 取输入）
    channel_out: _ChannelOut   # 聚合写通道（框架注入：write 推输出）
    signal_count: int          # 处理计数（降频/信号节流用）

    def __init__(self):
        super().__init__()
        self.cam_str = "algo_1"
        self.algo_key = "algo_1"
        self.vm_mode = "sim"
        self.sim_source = "videos/vm1.avi"
        self.vm_solution = ""
        self.vm_procedure = ""
        self.vm_resource_module = "ImageSource"
        self.vm_device_id = 1
        self.signal_divisor = 2
        self.vm = None
        self.signal_count = 0


thData = ThreadData()
