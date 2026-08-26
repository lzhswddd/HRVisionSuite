# -*- coding: utf-8 -*-
"""HRFlowController 合并版类型存根（原框架 + 进程模式 + DataBus）。

源码对应: HRVision/HRFlowController.py（IDE 跳转用源码；运行时用同目录 .pyd）。
内置能力:
    - 线程流程（原框架）：ThreadExecutor / ThreadStartor / _Controller.run
    - 进程流程：build_processes + ProcessStartor/ProcessExecutor（spawn 子进程）
    - 数据总线：DataBus（thread/process 双模式，共享内存环形队列，大对象 uid 槽）
    - 帧共享内存：_FrameBuffer（单写单读 numpy 帧）
    - 信号转发：_SignalProxy/_SignalRelay（子进程信号 → 主进程真实 emit）
    - 资源治理：cleanup_all_segments / _kill_pending_processes / 优先级 / CPU 锁核
"""
from typing import Any, Generic, TypeVar
import multiprocessing

_UserT = TypeVar("_UserT")

# ===== 原框架（线程模式） =====

class _Node:
    id: str
    type: str
    title: str
    content: str
    isRunning: bool
    isSubthread: bool
    isNormal: bool
    isSwapped: bool
    file_path: str
    next_ids: dict
    prev_id: list
    code: Any
    def run(self, _globals, _locals={}) -> str: ...

class _Process:
    nodes: dict
    start_id: str
    is_main: bool
    localCode: Any
    localCodePath: str

class ThreadExecutor:
    def __init__(self, process) -> None: ...
    def run(self, _globals, _locals={}, is_thread=False, **kwargs) -> None: ...
    def run_main(self, _globals, _locals={}, **kwargs) -> None: ...
    def stop(self) -> None: ...
    def isAlive(self) -> bool: ...

class ThreadStartor:
    priority: str | None          # idle/below/normal/above/high/realtime（Windows）
    def __init__(self, getProcess, gData, priority=None) -> None: ...
    def start(self, is_thread=True, **kwargs) -> ThreadExecutor: ...

# 兼容别名（原框架命名）
Executor = ThreadExecutor
Startor = ThreadStartor

# ===== 基类（类型标注/IDE 跳转） =====

class GlobalDataBase(Generic[_UserT]):
    thCtrls: dict
    proCtrls: dict
    exit_flag: bool
    user: _UserT
    def __init__(self) -> None: ...

class ThreadDataBase:
    frame_name: str | None
    frame_event: multiprocessing.synchronize.Event | None
    frame_done_event: multiprocessing.synchronize.Event | None
    def __init__(self) -> None: ...

# ===== 流程构建 =====

class _Controller:
    def __init__(self, dir_path: str, main_process_name: str) -> None: ...
    @staticmethod
    def read_and_decode_file(file_path: str) -> Any: ...
    def run(self) -> None: ...
    def run_release(self, codeConfig: dict) -> None: ...

def main(flow: str = None, main_process: str = "", code: str = "",
         project: str = "") -> None:
    """框架入口：参数优先，缺省从 sys.argv 解析（--flow/--main/--code/--project）。
    project 空 = 不锁项目（仅公司锁）。""" ...

def build_processes(dir_path: str, main_process_name: str, codeDict: dict = None,
                    startor_cls: type = None, pro_startor_cls: type = None,
                    process_signals: dict = None): ...

# ===== 帧共享内存（单写单读） =====

class _FrameBuffer:
    def __init__(self, name: str) -> None: ...
    def write(self, frame: Any) -> int: ...
    def read(self): ...
    def close(self) -> None: ...
    def resize(self, rows: int, cols: int, dtype: Any) -> None: ...
    @staticmethod
    def unlink_orphan(name: str) -> None: ...

# ===== 进程信号转发 =====

class _SignalProxy: ...
class _SignalProxyEmit: ...
class _SignalRelay:
    def __init__(self, signal_instance) -> None: ...
    def run_once(self, conn, timeout=0.1) -> bool: ...
    def run_once_from_msg(self, msg) -> bool: ...

def _process_main(flow_id: str, dir_path: str, main_process_name: str,
                  control_conn, proc_config: dict = None, **kwargs) -> None: ...

# ===== 进程执行器/启动器 =====

class ProcessExecutor:
    proc: multiprocessing.Process
    conn: Any
    def __init__(self, proc, conn) -> None: ...
    def isAlive(self) -> bool: ...
    def stop(self) -> None: ...
    def join(self, timeout=None) -> None: ...

class ProcessStartor:
    priority: str | None          # idle/below/normal/above/high/realtime（Windows）
    cpu_affinity: list[int] | None  # 锁核列表（如 [0, 1]；None 不锁）
    python_exe: str | None        # 指定子进程解释器（None = 当前环境 spawn）
    def __init__(self, getProcess, gData, dir_path: str, main_process_name: str,
                 signals: list = None, start_method: str = "spawn",
                 priority: str = None, cpu_affinity: list = None,
                 python_exe: str = None) -> None: ...
    def start(self, is_thread=True, **kwargs) -> ProcessExecutor: ...

# ===== 数据总线（thread/process 双模式） =====

class DataBus:
    """进程间/线程间消息总线。

    进程模式基于共享内存环形队列（零管道拷贝）；线程模式基于 queue.Queue。
    overflow: "drop_oldest"（默认，覆盖最旧）/ "drop_new" / "block"。
    max_obj_size: 大对象槽单槽字节上限（numpy 帧按实际布局传，默认 8MB）。
    """
    name: str
    maxlen: int
    mode: str
    overflow: str
    max_msg_size: int
    max_obj_size: int
    def __init__(self, name: str = "", maxlen: int = 100, mode: str = "auto",
                 overflow: str = "drop_oldest", max_msg_size: int = 1048576,
                 max_obj_size: int | None = None) -> None: ...
    def put(self, data) -> bool: ...
    def get(self, timeout=None): ...
    def close(self) -> None: ...

# ===== 资源治理 =====

def cleanup_all_segments() -> None: ...
def _kill_pending_processes() -> None: ...
def _apply_process_priority(pid: int, priority: str) -> None: ...
def _apply_cpu_affinity(pid: int, cores: list) -> None: ...
def _apply_thread_priority(tid: int, priority: str) -> None: ...

# ===== 通用组件：帧探测 / 显示槽 / 运行监控 =====

def frame_bytes(video_path: str) -> int | None:
    """视频首帧缓冲字节数 = height × stride（DataBus 槽位自适应用）。"""

def frame_shape(video_path: str) -> tuple | None:
    """视频/图片首帧尺寸 (h, w)。"""

class DisplaySlot:
    """单写单读显示槽（_FrameBuffer 封装）：写方覆盖写最新帧，读方按 seq 感知。

    多窗格引用同一 DisplaySlot 对象 = 共享一段共享内存。
    """
    name: str
    frame_shape: tuple | None
    def __init__(self, name: str, frame_shape: tuple = None) -> None: ...
    @classmethod
    def origin(cls, cam: str, frame_shape: tuple = None) -> "DisplaySlot": ...
    @classmethod
    def res(cls, cam: str, algo_id: int = None, frame_shape: tuple = None) -> "DisplaySlot": ...
    def write(self, frame) -> int: ...
    def read(self): ...
    def read_seq(self) -> int | None: ...

class Monitor:
    """运行监控：显示槽 seq 增量统计 FPS + 周期性 [FPS]/[MEM]/线程栈日志。

    gData_user 鸭子类型注入（algo_keys/display_slots/fps_stats/executors/
    cameraList/run_mode）。
    """
    def __init__(self, gData_user, fps_interval: float = 2.0,
                 mem_interval: float = 5.0, dump_interval: float = 5.0) -> None: ...
    def tick(self, now: float = None) -> None: ...

# ===== 通用管线：spec 单步配置 / 聚合通道 / 图解释器 / 配置工具 =====

class PipelineSpecBuilder:
    """pipeline_spec 单步配置器：一步步添加节点/通道/窗格，build() 生成完整 spec。"""
    def __init__(self, run_mode: str = "process", **globals_) -> None: ...
    def add_node(self, node_id: str, flow: str, **params) -> "PipelineSpecBuilder": ...
    def add_channel(self, ch_id: str, from_node: str, to_node: str,
                    kind: str = "queue", **params) -> "PipelineSpecBuilder": ...
    def add_pane(self, pane_id: str, origin: str, res: str,
                 node: str = None) -> "PipelineSpecBuilder": ...
    def nodes(self) -> list: ...
    def channels(self) -> list: ...
    def panes(self) -> list: ...
    def build(self) -> dict: ...
    def export(self, path: str = None) -> str: ...

def make_pipeline_spec(camera_nodes: dict, algo_nodes: dict,
                       run_mode: str = "process", **globals_) -> dict:
    """快捷生成「相机 → 算法」拓扑（队列通道 + 显示通道 + 窗格自动装配）。"""

def export_pipeline_spec(spec: dict, path: str = None) -> str: ...
def load_pipeline_spec(path: str) -> dict: ...
def validate_pipeline_spec(spec: dict) -> bool: ...

class _ChannelIn:
    """聚合读通道：从第一个有数据的 in 通道取数据（队列 get）。"""
    def __init__(self, channels: list) -> None: ...
    def get(self, timeout: float = None): ...

class _ChannelOut:
    """聚合写通道：put 写队列（每帧），write 写映射（throttle 降频，内部计数）。"""
    def __init__(self, channels: list) -> None: ...
    def put(self, data) -> None: ...
    def write(self, data, throttle: int = 1) -> None: ...

class PipelineManager:
    """pipeline_spec（通用流程图）解释器：任意流程 + 声明式通道拓扑装配。

    依赖注入：gData（框架保证）、spec（管线配置）、state（运行态容器）显式传入；
    管理器只写约定字段（run_mode/pane_list/algo_keys/pane_nodes/display_slots/
    executors/frame_shape/buses），不假设 user 结构。
    """
    def __init__(self, gData, signal_instance, spec: dict, state) -> None: ...
    def start(self) -> "PipelineManager": ...
    def stop(self) -> None: ...
