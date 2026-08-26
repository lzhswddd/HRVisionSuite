# -*- coding: utf-8 -*-
"""UsbYolo 全局数据：GlobalData(GlobalDataBase) + UI 信号。

设计要点：
    - 不创建 QApplication（子进程不付 Qt GUI 开销；UI 在 services/ui.py 懒创建）
    - 业务配置集中在 ProgramData（GlobalData.user），服务层读它
    - services 包导入路径在此注入（主进程与 spawn 子进程都经本模块）
"""
import os
import sys

# 项目根加入 sys.path（services 可导入）。__file__ 在框架 exec 模块里不存在时
# 回退 cwd（框架已 os.chdir 到 Flow/，其上级即项目根）。
try:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    _ROOT = os.path.dirname(os.getcwd())
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import multiprocessing as _mp

# Qt 依赖仅主进程需要（spawn/外部子进程的信号已被 _SignalProxy 替换）；
# 进程隔离环境（python_exe 指向 AI 环境如 D:/AIProgram）可能没有 PySide6 —— 条件导入
try:
    from PySide6.QtCore import Signal, QObject
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except ImportError:
    class Signal:
        """无 Qt 环境（AI 环境）信号桩：子进程 signal_instance 会被 _SignalProxy
        替换，桩只保证类定义可实例化。"""
        def __init__(self, *args, **kwargs):
            pass
    QObject = object
    QApplication = None
    _HAS_QT = False

from HRVision.HRFlowController import GlobalDataBase
from HRVision.HRFlowController import (make_pipeline_spec,
                                       load_pipeline_spec, PipelineManager)

# QApplication 必须在任何 QObject（信号源）创建之前存在，且必须模块级持有
#（局部引用会在流程结束后被 GC，Qt 信号源随之销毁——relay 线程 emit 会崩
#  "Signal source has been deleted"）。仅主进程 + 有 Qt 的环境创建
#  （spawn 子进程无 Qt GUI 需求：跳过；外部解释器子进程可能无 PySide6）。
if _HAS_QT and _mp.parent_process() is None:
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
    frame_shape: "tuple | None"  # (h, w)：显示槽帧尺寸（USB 相机为 None，读方按头部通道数还原）
    pipeline: "PipelineManager | None"  # 管线管理器（启动节点创建，UI 节点挂退出钩子）

    def __init__(self):
        # ---- 外部配置（拓扑声明） ----
        # 优先加载外部文件 Flow/pipeline.json（可用 spec_tool --export 导出后编辑）；
        # 无文件时用内置默认（USB 相机 0 × YOLO）。
        spec_path = os.path.join(_ROOT, "Flow", "pipeline.json")
        if os.path.exists(spec_path):
            self.pipeline_spec = load_pipeline_spec(spec_path)
        else:
            # 内置默认：1 相机流程 × 1 算法流程（1:1）——单步配置生成
            self.pipeline_spec = make_pipeline_spec(
                {"grab_0": {"flow": "camera", "source": "usb:0"}},
                {"yolo_1": {"flow": "algo", "model_path": "D:/AiProgram/yolov8n.pt",
                            "conf": 0.25, "imgsz": 640, "signal_divisor": 1}})
        self.fps_limit = 30            # UI 显示帧率限制（fps，0 = 不限制）

        # ---- 运行时字段（PipelineManager 启动时派生填充） ----
        self.run_mode = "process"      # 派生自 pipeline_spec
        self.cameraList = []           # 相机节点 id 列表（UI/监控用）
        self.algo_keys = []            # 算法节点 id 列表（窗格顺序）
        self.pane_list = []            # 显示窗格 id 列表（UI 窗格顺序）
        self.pane_nodes = {}           # pane_id -> 结果信号源节点 id（UI 信号路由）
        self.buses = {}                # 通道 id -> DataBus（帧/消息队列）
        self.display_slots = {}        # pane_id -> {"origin": 原图槽, "res": 结果槽}
        self.windows = {}              # pane_id -> (CameraView, checkbox, {seq})
        self.executors = {}            # 节点 id -> ProcessExecutor/ThreadExecutor
        self.fps_stats = {}            # pane_id -> {"count", "t0", "fps"}（槽 seq 增量）
        self.frame_shape = None        # (h, w) 或 None（USB 相机由头部通道数还原）
        self.pipeline = None           # PipelineManager（启动节点创建，UI 节点挂退出钩子）


class GlobalData(GlobalDataBase[ProgramData]):
    """继承框架 GlobalDataBase[ProgramData]：thCtrls/proCtrls/exit_flag 类型标注。"""

    def __init__(self):
        super().__init__()
        self.user = ProgramData()


class SignalProgram(QObject):
    """业务信号容器（小数据消息走 relay 机制：子进程 emit → pipe → 主进程真实 emit）。

    大图/帧数据走显示槽（共享内存），信号只传轻量消息（检测结果摘要/状态/事件）。
    """

    yoloResult = Signal(str, dict)   # (algo_key, 结果摘要)——检测结果小数据

    def __init__(self):
        super().__init__()


gData = GlobalData()
signal_instance = SignalProgram()
