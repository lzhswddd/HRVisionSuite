# -*- coding: utf-8 -*-
"""结果外设通知（插件式）：算法结果 → 配置的外设（PLC/VM/串口/日志）。

设计：结果通知器统一接口 notify(result)（result = info dict，JSON 可序列化）；
内置 ConsoleNotifier（日志）；PLC/VM 等真外设由项目方实现并注册：
    register_notifier("plc_ex", PlcNotifierCls)
配置：{"notify": [{"type": "log"}, {"type": "plc_ex", "params": {...}}]}
"""
import typing

__all__ = ["Notifier", "ConsoleNotifier", "register_notifier", "build_notifiers"]


class Notifier:
    """结果通知器基类：子类实现 notify(result)（默认无实现仅日志）。"""

    NOTIFY_TYPE = "base"

    def __init__(self, params: typing.Optional[dict] = None):
        self.params = dict(params or {})

    def notify(self, result: dict) -> bool:
        """通知一条结果（info 摘要）。返回是否成功。"""
        raise NotImplementedError

    def close(self) -> None:
        pass


class ConsoleNotifier(Notifier):
    """控制台/日志通知器（默认内置，开发先用它）——工厂/项目主题适配。"""

    NOTIFY_TYPE = "log"

    def notify(self, result: dict) -> bool:
        print("[notify] %s" % result)
        return True


_REGISTRY: "dict[str, typing.Type[Notifier]]" = {"log": ConsoleNotifier}


def register_notifier(notify_type: str, cls: "typing.Type[Notifier]") -> None:
    """注册外设通知器类型（项目侧实现：PLC/VM/串口…）。"""
    _REGISTRY[notify_type] = cls


def build_notifiers(entries: list) -> "list[Notifier]":
    """按配置构建通知器列表：
    entry = {"type": "log"} 或 {"type": "my_plc", "params": {...}}
    """
    out = []
    for e in entries or []:
        t = e.get("type", "log") if isinstance(e, dict) else str(e)
        params = e.get("params", {}) if isinstance(e, dict) else {}
        cls = _REGISTRY.get(t)
        if cls is None:
            print("[notify] 未注册通知器类型: %s（register_notifier）" % t)
            continue
        try:
            out.append(cls(params))
        except Exception as ex:
            print("[notify] 构建 %s 失败: %s" % (t, ex))
    return out
