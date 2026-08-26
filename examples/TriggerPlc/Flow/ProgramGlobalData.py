# -*- coding: utf-8 -*-
"""TriggerPlc 全局数据：GlobalData(GlobalDataBase) + UI 信号。

设计要点：
    - 不创建 QApplication（子进程不付 Qt GUI 开销；UI 在 services/ui.py 懒创建）
    - 业务配置集中在 ProgramData（GlobalData.user），服务层读它
    - services 包导入路径在此注入（主进程与 spawn 子进程都经本模块）
"""
import os
import sys

try:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    _ROOT = os.path.dirname(os.getcwd())
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import multiprocessing as _mp

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QApplication
from HRVision.HRFlowController import GlobalDataBase
from HRVision.HRFlowController import (make_pipeline_spec,
                                       load_pipeline_spec, PipelineManager)

# QApplication 模块级持有（relay 线程 emit 需要信号源存活）；spawn 子进程跳过
if _mp.parent_process() is None:
    qApp = QApplication([])


class ProgramData:
    """项目自定义数据（GlobalData.user 的类型）。

    拓扑与节点参数全部由 pipeline_spec（外部配置）声明，运行时字段由
    PipelineManager 启动时派生填充——管理器不做业务判断，只解释配置。
    """

    # ---- 外部配置（拓扑声明） ----
    pipeline_spec: dict          # 管线配置（JSON 加载或内置默认）
    fps_limit: int               # UI 显示帧率限制（fps，0 = 不限制）

    # ---- 运行时字段（PipelineManager 启动时派生填充） ----
    run_mode: str                # 派生自 pipeline_spec（"process"/"thread"）
    cameraList: list[str]        # 相机节点 id 列表（UI/监控用）
    algo_keys: list[str]         # 算法节点 id 列表（窗格顺序）
    pane_list: list[str]         # 显示窗格 id 列表（UI 窗格顺序）
    pane_nodes: dict[str, str]   # pane_id -> 结果信号源节点 id（UI 信号路由）
    buses: dict                  # 通道 id -> DataBus（帧/消息队列）
    display_slots: dict          # pane_id -> {"origin": DisplaySlot, "res": DisplaySlot}
    windows: dict                # pane_id -> [CameraView, QCheckBox, {seq, result}]
    executors: dict              # 节点 id -> ProcessExecutor/ThreadExecutor
    fps_stats: dict              # pane_id -> {"count", "t0", "fps"}（槽 seq 增量）
    frame_shape: tuple | None    # (h, w)：显示槽帧尺寸（读方按头部通道数还原）
    pipeline: PipelineManager | None   # 管线管理器（启动节点创建，UI 节点挂退出钩子）

    def __init__(self):
        spec_path = os.path.join(_ROOT, "Flow", "pipeline.json")
        if os.path.exists(spec_path):
            self.pipeline_spec = load_pipeline_spec(spec_path)
        else:
            # 内置默认：1 相机 × 1 算法，PLC mock 模式 + 1s 自动触发
            self.pipeline_spec = make_pipeline_spec(
                {"grab_0": {"flow": "camera", "source": "videos/cam1.avi",
                            "plc_mode": "mock", "plc_port": 5020,
                            "auto_trigger_ms": 1000}},
                {"algo_1": {"flow": "algo", "algo_load": 1}})
        self.fps_limit = 15

        self.run_mode = "process"
        self.cameraList = []
        self.algo_keys = []
        self.pane_list = []
        self.pane_nodes = {}
        self.buses = {}
        self.display_slots = {}
        self.windows = {}
        self.executors = {}
        self.fps_stats = {}
        self.frame_shape = None
        self.pipeline = None


class GlobalData(GlobalDataBase[ProgramData]):
    """继承框架 GlobalDataBase[ProgramData]：thCtrls/proCtrls/exit_flag 类型标注。"""

    def __init__(self):
        super().__init__()
        self.user = ProgramData()


class SignalProgram(QObject):
    """业务信号容器（小数据消息走 relay 机制：子进程 emit → pipe → 主进程真实 emit）。

    大图/帧数据走显示槽（共享内存），信号只传轻量消息（结果摘要/事件）。
    """

    triggerFired = Signal(str, dict)   # (cam_id, {"count"})——触发拍照事件
    triggerResult = Signal(str, dict)  # (algo_key, {"ok","score","plc_write",...})

    def __init__(self):
        super().__init__()


gData = GlobalData()
signal_instance = SignalProgram()
