# -*- coding: utf-8 -*-
"""共享状态容器 SharedState：跨进程/线程"真共享"数据与"进程本地"数据的区分约定。

进程模式事实（见规范 2.0.1）：
    - gData/ProgramData 本身 = 进程本地（各进程独立构造，字段不穿透）
    - 真共享仅有三种载体：DataBus（共享内存队列，按名 attach）、
      DisplaySlot/_FrameBuffer（共享内存段）、SignalProgram（relay 转发）
SharedState 把这些"真共享载体"集中到同一容器（ProgramData.shared）：
    - 语义清晰：看到 .shared 就知道能跨进程；其余 ProgramData 字段 = 进程本地
    - 集中管理：bus/显示槽/命令总线一处注册，外部（UI/监控/节点）统一入口
    - pickle 友好：spawn 子进程按名 attach（buses/display_slots 内部的
      DataBus/DisplaySlot 对象自带 __getstate__ 按名重建）

用法（ProgramGlobalData.py）：
    class ProgramData:
        shared: SharedState          # ★ 跨进程共享容器
        # 以下为进程本地字段：windows/pipeline/executors/monitor/fps_stats...
        def __init__(self):
            self.shared = SharedState()

    # 框架兼容桥接（不改框架核心）：
    #   user.buses  / user.display_slots  → property 代理到 shared.buses / shared.display_slots
    #   （框架 PipelineManager 原地写入 dict：getter 引用即生效，无需 setter）
"""
import typing

__all__ = ["SharedState", "SharedStateMixin"]


class SharedState:
    """跨进程/线程共享容器：所有字段均为"真共享"（按名 attach 的共享内存/队列）。"""

    def __init__(self):
        self.buses: "dict[str, typing.Any]" = {}          # 通道 id -> DataBus（共享队列）
        self.display_slots: "dict[str, dict]" = {}        # pane_id -> {"origin": DisplaySlot, "res": DisplaySlot}
        self.commands: "dict[str, str]" = {}              # 命名命令总线表：name -> 说明
                                                          #（EvtBridge 按名 worker/sender，无需存实例）
        self.status: "dict[str, dict]" = {}               # 跨进程状态快照存放处（Worker camState 类；
                                                          # 仅作登记——真状态仍走信号/消息，勿直接跨
                                                          # 进程写普通 dict）

    # ---------------- 便捷方法（进程内/线程内使用） ----------------

    def register_bus(self, name: str, desc: str = "") -> None:
        """登记命令总线名（EvtBridge/DataBus 使用侧自行创建/附接）。"""
        self.commands[name] = desc

    def lookup_bus(self, name: str) -> bool:
        """查询总线名是否已登记。"""
        return name in self.commands

    def summary(self) -> dict:
        """摘要（UI/监控展示）：bus 数与显示槽数。"""
        return {"buses": len(self.buses),
                "display_slots": len(self.display_slots),
                "commands": list(self.commands.keys())}


class SharedStateMixin:
    """mixin：给 ProgramData 提供 shared 字段 + buses/display_slots 桥接 property。

    继承即可获得（框架写 user.buses/user.display_slots 定向到 shared 容器）：
        @property buses -> shared.buses
        @property display_slots -> shared.display_slots
    """

    shared: SharedState

    def _init_shared(self) -> None:
        """__init__ 里调用一次。"""
        self.shared = SharedState()

    @property
    def buses(self):
        return self.shared.buses

    @buses.setter
    def buses(self, value):
        self.shared.buses = value

    @property
    def display_slots(self):
        return self.shared.display_slots

    @display_slots.setter
    def display_slots(self, value):
        self.shared.display_slots = value
