# -*- coding: utf-8 -*-
"""数据点 DataSubject：框架间数据的「订阅即当前值、更新自动驱动」。

解决什么：相机/算法/PLC 各流程之间要共享的数据（状态/配置/结果/触发），
用户只需：
    sub = DataSubject("cam1.state")          # 具名数据点（跨进程/线程统一）
    sub.set(value)                            # 更新数据（任何位置）
    value = sub.get()                         # 其他地方使用（立即得当前值）
    sub.on_change(cb)                         # 数据驱动的自动驱动：
                                              # 数据一更新就自动触发（实现隐藏）
——不用管消息格式、线程、进程、握手，就是"写一个数据点，别处读/被驱动"。

语义（对齐"要用的时候有数据"）：
    - last-value：set 覆盖当前值；get 任何时刻读到的都是最新值（相对"队列"）
    - 数据驱动：on_change 在数据更新后被自动调用（后台守护线程投递，慢
      消费者队列隔离——与 TopicBus 同款语义，但对象是"数据点"而非"消息流"）
    - 跨进程/线程：mode="process"（共享内存，按名 attach）/ "thread"
      （进程内多线程，同名单例）
    - 结构：单值域（一般用途）或 dict 域（sub.field("name") 便捷访问）

底层：DataBus（HRFlowController）为传输入口；变更回调经点内循环线程转发生效，
用户无感。用法见模块 docstring；进程边界注意：数据点值应 JSON 可序列化
（大帧不走这里——帧用显示槽/共享内存，见规范）。
"""
import multiprocessing as _mp
import sys
import threading
import time
import typing

__all__ = ["DataSubject"]

_THREAD_BUSES = {}   # thread 模式 DataBus 同名单例（无按名 attach 语义）


def _detect_mode() -> str:
    """自动判定数据点模式（用户不需指定，避免 thread/process 想错）。

    拓扑模型：主进程（HRStar 进程，UI/面板/主流程在其上）——流程节点按配置
    以 process（spawn 子进程）或 thread（主进程线程）运行；flow 内同模式，
    不同 flow 可混搭。判定链：
        1) 我在子进程（spawn 子进程内）：当前 flow 节点模式（thData.mode，
           管线启动时注入）——子进程侧最精确
        2) 主进程侧：全局 run_mode（pipeline_spec 顶层 = 用户声明的拓扑模式；
           主进程数据点与子进程共享 → process，全线程流程 → thread）
        3) 兜底 "process"（共享内存按名 attach——单进程多线程同样正确）
    """
    # 1) 子进程内：thData.mode（管线把每个节点解析后的 mode 注入）
    if _mp.parent_process() is not None:
        for _name in ("camera.ThreadGlobalData", "algo.ThreadGlobalData",
                      "plc.ThreadGlobalData", "main.ThreadGlobalData"):
            _mod = sys.modules.get(_name)
            thd = getattr(_mod, "thData", None) if _mod is not None else None
            m = getattr(thd, "mode", "")
            if m in ("process", "thread"):
                return m
    # 2) 全局 run_mode（主进程侧与统一模式配置）
    try:
        from ProgramGlobalData import gData
        m = getattr(getattr(gData, "user", None), "run_mode", "")
        if m in ("process", "thread"):
            return m
    except Exception:
        pass
    return "process"


class DataSubject:
    """具名数据点：set/get/on_change（进程/线程统一，按名共享）。"""

    def __init__(self, name: str, mode: "str | None" = None,
                 initial: typing.Any = None):
        """mode=None（默认）自动探测：框架流程 run_mode / 无框架兜底 process。
        用户不需要指定——线程/进程下行为自动正确。"""
        self.name = name
        self.mode = mode or _detect_mode()
        try:
            from HRVision.HRFlowController import DataBus
            if self.mode == "thread":
                # DataBus thread 无按名 attach：同名单例（与 evt_bridge 语义一致）
                bus = _THREAD_BUSES.get(name)
                if bus is None:
                    bus = DataBus(name, maxlen=8, mode="thread",
                                  overflow="drop_oldest")
                    _THREAD_BUSES[name] = bus
                self._bus = bus
            else:
                self._bus = DataBus(name, maxlen=8, mode="process",
                                    overflow="drop_oldest")
        except ImportError:
            self._bus = None
        self._guard = threading.Lock()
        self._last: typing.Any = initial
        self._subs: "list[typing.Callable]" = []
        self._closed = False
        # 消费循环惰性启动：仅「有订阅者」的实例消费（写者/空实例不开——
        # 否则同一数据点多实例会互相抢消息，订阅者反而漏收）
        self._th: "threading.Thread | None" = None

    def _ensure_loop(self) -> None:
        if self._th is None:
            self._th = threading.Thread(target=self._loop,
                                        name="DataSubject-%s" % self.name,
                                        daemon=True)
            self._th.start()

    # ---------------- 用户接口 ----------------

    def set(self, value, notify: bool = True) -> bool:
        """更新数据（override 当前值）。任何进程/线程均可调用。"""
        if self._bus is None:
            return False
        try:
            return self._bus.put({"v": value})
        except Exception:
            return False

    def get(self):
        """读取当前值（任何时候都返回最新）。"""
        return self._last

    def on_change(self, callback) -> tuple:
        """数据更新后被自动驱动的回调（数据驱动）。返回 token。"""
        token = (id(callback), callback)
        with self._guard:
            self._subs.append((token, callback))
        self._ensure_loop()
        return token

    def off_change(self, token) -> None:
        with self._guard:
            self._subs = [(t, cb) for t, cb in self._subs if t != token]

    @property
    def value(self):
        return self._last

    # ---------------- 内部：变更消费 + 驱动 ----------------

    def _loop(self) -> None:
        while not self._closed:
            try:
                msg = self._bus.get(timeout=0.2) if self._bus is not None else None
            except Exception:
                msg = None
            if msg is None:
                continue
            value = msg.get("v") if isinstance(msg, dict) else msg
            self._last = value
            with self._guard:
                subs = [cb for _t, cb in self._subs]
            for cb in subs:
                try:
                    cb(value)
                except Exception as e:
                    print("[DataSubject] %s 回调异常: %s" % (self.name, e))

    # ---------------- dict 域便捷 ----------------

    def field(self, key: str):
        """dict 值域的字段访问子（sub.field("name").set(...)）。"""
        return _Field(self, key)

    def close(self) -> None:
        self._closed = True
        with self._guard:
            self._subs.clear()


class _Field:
    """数据点 dict 字段访问：sub.field("key").set(v) / .get() / .on_change(cb)。"""

    def __init__(self, sub: DataSubject, key: str):
        self._sub = sub
        self._key = key

    def set(self, value, notify: bool = True) -> bool:
        cur = dict(self._sub.get() or {})
        cur[self._key] = value
        return self._sub.set(cur, notify)

    def get(self):
        cur = self._sub.get()
        return (cur or {}).get(self._key)

    def on_change(self, callback):
        def _wrap(value):
            callback((value or {}).get(self._key))
        return self._sub.on_change(_wrap)


def thread_bus(name: str, **kw):
    """进程内多线程同名单例注释（简易引用；创建即线程模式数据点）。"""
    return DataSubject(name, mode="thread", **kw)
