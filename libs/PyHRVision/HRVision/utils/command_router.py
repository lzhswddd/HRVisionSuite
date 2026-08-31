# -*- coding: utf-8 -*-
"""声明式命令路由 CommandRouter：UI 命令回调 → 配置表 → 目标总线发送。

把「命令 → 消息」的适配逻辑（参数解析/校验/类型映射）从流程节点代码抽出，
变成**配置**：任何外部 UI（相机/PLC/算法面板）只需要一份命令映射表即可复用；
新面板 = 新配置，不动路由器代码。

配置示例（相机面板 / m3 流程节点）：
    CAMERA_COMMANDS = {
        "new":       {"bus": "cam", "build": "new_camera"},  # 内置解析器
        "set_param": {"bus": "cam", "build": "set_param"},
        "open":      {"bus": "cam"},   # 无 build = 原样转 send(cmd, **payload)
        "destroy":   {"bus": "cam"},
    }
    router = CommandRouter(CAMERA_COMMANDS, controllers={"cam": ctrl})
    ui = MainWindow(..., on_command=router.route)   # UI 只上报，发送可配置

内置 build：
    - "new_camera"    相机创建参数解析（hr*/LocalCamera/VideoCamera → params）
    - "set_param"     float 值校验（None/err 不发送）
自定义：CommandRouter.register_build("name", fn)；fn(payload, registry) -> dict|None
        （dict = 发送的 **kwargs；None = 取消发送）
"""
import typing

__all__ = ["CommandRouter", "CAMERA_MAP"]


# 相机面板默认命令表（内置 build 引用；controllers 由使用方注入）
CAMERA_MAP = {
    "new":       {"bus": "cam", "build": "new_camera"},
    "destroy":   {"bus": "cam"},
    "open":      {"bus": "cam"},
    "close":     {"bus": "cam"},
    "start":     {"bus": "cam"},
    "stop":      {"bus": "cam"},
    "set_param": {"bus": "cam", "build": "set_param"},
    "apply_config": {"bus": "cam"},
    "info":      {"bus": "cam"},
    "get_tree":  {"bus": "cam"},     # 参数树查询
    "set_config":{"bus": "cam"},     # 连接参数更新（扫描选设备后，不打开设备）
}


class CommandRouter:
    """声明式命令路由：route(cmd, payload) → 查表 → build 转换 → 总线 send。"""

    def __init__(self, command_map: dict, controllers: "dict[str, typing.Any]"):
        self._map = dict(command_map)
        self._controllers = dict(controllers)   # bus 名 -> send(cmd, **payload) 对象
        for entry in self._map.values():
            entry.setdefault("bus", "cam")

    # ---------------- 路由 ----------------

    def route(self, cmd: str, payload: typing.Optional[dict] = None) -> bool:
        """处理一条 UI 命令（on_command 回调直达）。返回是否已发送。"""
        entry = self._map.get(cmd)
        if entry is None:
            print("[CommandRouter] 未配置命令: %s" % cmd)
            return False
        ctrl = self._controllers.get(entry["bus"])
        if ctrl is None:
            print("[CommandRouter] 总线未注册: %s" % entry["bus"])
            return False
        payload = dict(payload or {})
        build = entry.get("build")
        if build:
            fn = _BUILDS.get(build)
            if fn is None:
                print("[CommandRouter] 未注册 build: %s" % build)
                return False
            send_kwargs = fn(payload, self._effective_registry())
            if send_kwargs is None:
                return False             # build 判定不发送（校验失败等）
            ctrl.send(cmd, **send_kwargs)
            return True
        ctrl.send(cmd, **payload)
        return True

    def _effective_registry(self) -> dict:
        """build 可用的上下文（格式类型注册表等——默认为空，build 自取）。"""
        return getattr(self, "_registry", {})

    @property
    def registry(self) -> dict:
        return getattr(self, "_registry", {})

    @registry.setter
    def registry(self, value: dict) -> None:
        self._registry = value

    # ---------------- 注册扩展 ----------------

    @classmethod
    def register_build(cls, name: str, fn) -> None:
        """注册自定义 build（fn(payload, registry) -> dict|None）。"""
        _BUILDS[name] = fn

    def __repr__(self):
        return "CommandRouter(%s)" % ", ".join(sorted(self._map))


# ------------------------------------------------------------------
# 内置 build 解析器
# ------------------------------------------------------------------

_BUILDS: "dict[str, typing.Callable]" = {}


def _new_camera(payload: dict, registry: dict) -> "dict | None":
    """相机创建参数解析：hr*（厂商 mode,key,color）/ LocalCamera（dir）/ 其他（source）。"""
    ctype = payload.get("camera_type", "")
    raw = str(payload.get("raw", "")).strip()
    types = registry.get("types", {})
    cls = types.get(ctype, (None, {}))[0]
    if cls is None:
        print("[CommandRouter] 类型 %s 不可用（HRCamera 未安装）" % ctype)
        return None
    if ctype.startswith("hr"):                       # 厂商库：mode,key,color
        parts = [p.strip() for p in raw.split(",")] + ["Serial", "", "False"]
        params = {"mode": parts[0] or "Serial", "key": parts[1],
                  "color": (parts[2] or "False").lower() in ("true", "1", "yes")}
    elif ctype == "GenICam":                          # 通用 GenICam：raw = .cti 路径（外部提供）
        params = {"producer": raw}
    elif ctype == "LocalCamera":
        params = {"dir": raw}
    else:                                            # VideoCamera 等
        params = {"source": raw}
    return {"camera_type": ctype, "params": params}


def _set_param(payload: dict, registry: dict) -> "dict | None":
    """参数设置：value 非空（float 化）才发送。"""
    value = payload.get("value")
    if value is None:
        return None
    try:
        fv = float(value)
    except (TypeError, ValueError):
        print("[CommandRouter] 参数格式错误: %s=%s" % (payload.get("key"), value))
        return None
    return {"key": payload.get("key", ""), "value": fv}


_BUILDS["new_camera"] = _new_camera
_BUILDS["set_param"] = _set_param
