# -*- coding: utf-8 -*-
"""主题订阅总线 TopicBus（v2）：进程内无感数据管道——"要用的时候有数据用"。

设计语义（对比 v1 的修正/升级）：
    1. 每订阅者独立队列 + 独立线程：慢消费者不拖死其他订阅者
       （handler 在自己队列线程执行；publish 非阻塞）
    2. retained（关latch）：订阅主题时立即投递最近一条消息（无需等下一帧）
       帧流/状态类主题：新消费方接入即有当前值——"要用时就有数据"
    3. 通配订阅：topic 支持 fnmatch（"*.verdicts"、"u*"），多单元组合零配置
    4. 背压策略：队列满 drop_oldest（帧类）/ drop_new / block 可选
    5. 兼容 v1 API：subscribe(topic, handler, once=False) / unsubscribe(token) /
       publish(topic, payload) / close()

用法：
    bus = TopicBus("scene", retained=True)
    tok = bus.subscribe("*.verdicts", on_verdict)     # 通配 + 立即投递 retained 值
    bus.publish("u1.verdicts", {...})
    bus.unsubscribe(tok)
    bus.close()
"""
import fnmatch
import queue
import threading
import typing

__all__ = ["TopicBus"]


class _Sub:
    """单订阅者：独立队列 + 线程（消费慢不影响其他订阅者）。"""

    def __init__(self, bus: "TopicBus", pattern: str, handler, once: bool,
                 queue_len: int):
        self.pattern = pattern
        self.handler = handler
        self.once = once
        self.queue: "queue.Queue[tuple]" = queue.Queue(maxsize=max(1, queue_len))
        self.token = (pattern, handler)
        self._bus = bus
        self._th = threading.Thread(target=self._run, daemon=True,
                                    name="TopicSub-%s" % pattern)
        self._th.start()

    def matches(self, topic: str) -> bool:
        return fnmatch.fnmatchcase(topic, self.pattern)

    def put(self, payload, overflow: str) -> bool:
        if self.once and self._consumed():
            return True
        try:
            self.queue.put_nowait((payload,))
            return True
        except queue.Full:
            if overflow == "block":
                self.queue.put((payload,))
                return True
            if overflow == "drop_new":
                return False
            try:                                     # drop_oldest
                self.queue.get_nowait()
                self.queue.put_nowait((payload,))
                return True
            except Exception:
                return False

    def _consumed(self) -> bool:
        return False

    def _run(self) -> None:
        while True:
            try:
                (payload,) = self.queue.get(timeout=0.2)
            except queue.Empty:
                if self.once:
                    return
                continue
            try:
                self.handler(payload)
            except Exception as e:
                import traceback as _tb
                _tb.print_exc()
                print("[TopicBus] handler 异常(%s): %s" % (self.pattern, e))


class TopicBus:
    """主题订阅总线（v2）。"""

    def __init__(self, name: str = "topic", overflow: str = "drop_oldest",
                 retained: bool = True, sub_queue_len: int = 16):
        self.name = name
        self.overflow = overflow
        self.retained = retained
        self.sub_queue_len = int(sub_queue_len)
        self._subs: "list[_Sub]" = []
        self._retained_map: "dict[str, list]" = {}   # topic -> [payload, ...]（环）
        self._lock = threading.RLock()
        self._closed = False

    # ---------------- 订阅 ----------------

    def subscribe(self, topic: str, handler, once: bool = False,
                  queue_len: "int | None" = None, retained: "bool | None" = None) -> tuple:
        """订阅 topic（支持 fnmatch 通配）。返回 token。

        retained=True（默认）：订阅立即收到该主题最近一条（先用时有数据）；
        通配模式仅匹配实际发布过的最近值（全局 retain 表）。
        """
        sub = _Sub(self, topic, handler, once,
                   queue_len or self.sub_queue_len)
        with self._lock:
            self._subs.append(sub)
        if (retained if retained is not None else self.retained) and not once:
            with self._lock:
                for t, payloads in list(self._retained_map.items()):
                    if sub.matches(t) and payloads:
                        sub.put(payloads[-1], self.overflow)
        return sub.token

    def unsubscribe(self, token) -> None:
        with self._lock:
            self._subs = [s for s in self._subs if s.token != token]

    # ---------------- 发布 ----------------

    def publish(self, topic: str, payload) -> bool:
        """非阻塞发布；retained 默认记录最近 1 条（可 `name` 级配置）。"""
        if self._closed:
            return False
        with self._lock:
            subs = list(self._subs)
            if self.retained:
                self._retained_map.setdefault(topic, [])
                self._retained_map[topic] = [payload]
        ok = True
        for s in subs:
            if s.matches(topic):
                ok = s.put(payload, self.overflow) and ok
        return ok

    # ---------------- 治理 ----------------

    def subscription_count(self) -> int:
        with self._lock:
            return len(self._subs)

    def close(self) -> None:
        self._closed = True
        with self._lock:
            self._subs.clear()
            self._retained_map.clear()
