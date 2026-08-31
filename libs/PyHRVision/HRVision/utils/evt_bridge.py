# -*- coding: utf-8 -*-
"""通用跨进程/线程事件桥：事件通知统一模式（零轮询、阻塞消费、事件等待）。

场景：相机节点、算法节点、PLC 流程……任何「控制方 → 工作进程」的事件通知：
    - 下行消息（命令/通知）：DataBus（进程=共享内存队列 / 线程=Queue 单例），
      由 EvtBridge 后台线程 **阻塞消费**（bus.get(timeout=None)，无消息不醒）
    - 上行事件：SignalProgram 信号（子进程 emit → relay → 主进程真实 emit；
      也可用反向 DataBus 由调用方 poll——推荐信号，见规范）
    - 工作方节点循环：`bridge.wait(timeout)` 事件等待（Condition，命令执行完
      立即唤醒，空转纯睡眠）——取代高频轮询（相机实测响应 3ms，CPU 零空转）

消息协议（json 可序列化 dict）：
    {type: <消息类型>, ts, seq, payload}——handler 按 type 分发；无 handler 时
    消息进内建 FIFO（.recv() 取），桥只做通知。

用法（工作方/子流程进程）：
    bridge = EvtBridge("plc_cmd", mode="process")
    @bridge.route("start")
    def on_start(payload): plc.start()
    bridge.on_event = lambda text: signal_instance.plcEvent.emit(text)  # 或统一 emit
    # 节点循环：
    while True:
        bridge.wait(timeout=0.5)
        if plc.running: frame = plc.tick(...)

用法（控制方/主进程）：
    sender = EvtBridge("plc_cmd", side="sender")
    sender.send("start")
    sender.send("set_param", key="x", value=1)

兼容：DataBus mode="auto" 会各自退化为线程队列（跨进程不通）——进程模式必须
显式 mode="process"；thread 模式下总线同名单例（Controller/Worker 共享）。
"""
import json
import threading
import time
import typing

__all__ = ["EvtBridge"]


class EvtBridge:
    """事件桥（双侧通用：side="worker" 阻塞消费/事件等待；side="sender" 只发送）。"""

    def __init__(self, name: str, side: str = "worker", mode: str = "process"):
        if side not in ("worker", "sender"):
            raise ValueError("side must be worker/sender")
        self.name = name
        self.side = side
        self.bus = None
        if mode == "thread":
            self.bus = _thread_bus(name)
        elif mode == "process":
            from HRVision.HRFlowController import DataBus
            self.bus = DataBus(name, maxlen=64, mode="process",
                               overflow="drop_new", max_msg_size=256 * 1024)
        else:
            raise ValueError("mode must be process/thread")
        self._cond = threading.Condition()
        self._handlers: typing.Dict[str, typing.Callable] = {}
        self._on_msg = None            # 兜底 handler（未匹配 type 时调用）
        self._fifo: list = []
        self._seq = 0
        if side == "worker":
            threading.Thread(target=self._loop, name="EvtBridge-%s" % name,
                             daemon=True).start()

    # ---------------- 路由调用方接口 ---------------- #

    def route(self, msg_type: str):
        """装饰器：注册消息类型 handler（worker 侧）。"""
        def deco(fn):
            self._handlers[msg_type] = fn
            return fn
        return deco

    def on_message(self, fn: typing.Callable) -> None:
        """兜底 handler（未注册 type 的消息）。"""
        self._on_msg = fn

    def wait(self, timeout: typing.Optional[float] = None) -> bool:
        """事件等待：等消息处理完成（立即 True / 超时 False）——节点循环用。"""
        with self._cond:
            self._cond.wait(timeout)
        return True

    # ---------------- 发送方接口 ---------------- #

    def send(self, msg_type: str, **payload) -> bool:
        """发送消息（自动补 ts/seq）。"""
        self._seq += 1
        msg = {"type": msg_type, "ts": int(time.time()),
               "seq": self._seq, "payload": payload}
        return self._put(msg)

    def send_msg(self, msg: dict) -> bool:
        """发送完整 dict（需含 type）。"""
        return self._put(msg)

    def _put(self, msg: dict) -> bool:
        if self.bus is None:
            return False
        try:
            return self.bus.put(msg)
        except Exception:
            return False

    # ---------------- 工作侧：阻塞消费 + 事件等待 ---------------- #

    def _loop(self) -> None:
        while True:
            try:
                msg = self.bus.get(timeout=None) if self.bus is not None else None
            except Exception:
                msg = None
            if msg is None:
                time.sleep(0.2)     # bus 异常兜底（正常路径不触发）
                continue
            try:
                with self._cond:
                    self._dispatch(msg)
                    self._cond.notify_all()
            except Exception:
                pass

    def _dispatch(self, msg: dict) -> None:
        mtype = msg.get("type", "")
        payload = msg.get("payload", {}) or {}
        fn = self._handlers.get(mtype)
        if fn is not None:
            fn(payload)
            return
        if self._on_msg is not None:
            self._on_msg(msg)
            return
        self._fifo.append(msg)

    def recv(self, timeout: typing.Optional[float] = None):
        """取未认领的消息（无 handler 时入 FIFO）。"""
        if self._fifo:
            return self._fifo.pop(0)
        return None

    @property
    def pending(self) -> int:
        return len(self._fifo)


_THREAD_BUSES = {}


def _thread_bus(name: str):
    """线程模式同名单例（thread DataBus 无 attach 语义）。"""
    bus = _THREAD_BUSES.get(name)
    if bus is None:
        from HRVision.HRFlowController import DataBus
        bus = DataBus(name, maxlen=64, mode="thread",
                      overflow="drop_new", max_msg_size=256 * 1024)
        _THREAD_BUSES[name] = bus
    return bus
