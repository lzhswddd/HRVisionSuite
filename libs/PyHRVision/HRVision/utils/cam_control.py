# -*- coding: utf-8 -*-
"""相机跨进程/线程小数据交互：命令总线上行 + 事件信号下行（通用控制规范）。

进程边界规范：
    - 相机实例只能在「相机进程」内创建与调用（节点进程私有，主进程/算法进程
      不得 import 或直接访问相机对象）
    - 跨进程/跨线程控制相机 = 走命令总线（DataBus）+ 事件信号（SignalProgram）
      兼容双模式：thread（queue.Queue）/ process（共享内存环形队列，按名 attach）

协议（消息一律 json 可序列化 dict）：
    命令（Controller -> Worker，DataBus 单条，主/控制方 put）：
        {cmd: "new"|"open"|"close"|"destroy"|"start"|"stop"|"apply_config"|
             "set_param"|"info", ts: 1621..., seq: n, payload: {...}}
    事件（Worker -> Controller，signal 下行，实时性低/频率低）：
        camState(dict)  状态快照（已创建/已打开/推流中/掉线重连中 + 参数摘要）
        camEvent(str)   一次性事件（"已恢复（第 N 次）"/"参数已设置"…）

命令集合与 payload：
    new           {camera_type: "VideoCamera"|"LocalCamera"|"HikCamera",
                   params: {...}}            # 创建相机实例（未打开）
    open          {}                           # 打开（失败回事件）
    close         {}                           # 关闭（实例保留，可再 open/start）
    destroy       {}                           # 销毁：关闭并释放实例（可再 new 其他类型）
    start         {push: false}               # 启动推流/取图（线程模式同）
    stop          {}
    apply_config  {config: {...}}             # 切换配置立即生效（Stop→Open→Grab）
    set_param     {key, value}                # 曝光/增益等（SetValue 族）
    info          {}                           # 触发一次状态快照

Worker 约定：相机节点循环里调 worker.cycle(timeout)——消费命令→执行→可能
触发抓帧；推流中每轮 cycle 拉一帧经 channel_out 推走。事件经 signal_instance
转发育（thread/process 均可用）。

用法（主进程）：
    ctrl = CameraController(bus_name="cam_cmd", signal_instance=sig)
    ctrl.send("new", camera_type="HikCamera", params={...})
    ctrl.send("start")
    ctrl.bind(signal_instance.camState, ui.on_state)   # 或直接 connect

用法（相机进程节点）：
    worker = CameraWorker(bus_name="cam_cmd", signal_instance=signal_instance)
    worker.cycle(0.05)                      # 每轮节点迭代调用
    if worker.running:
        ok, frames, msg = worker.grab()
        ...
"""
import os
import numpy
import time
import typing

from HRVision.utils.camera_host import CameraHost
from HRVision.utils.video_camera import VideoCamera
from HRVision.utils.local_camera import LocalCamera
from HRVision.utils.genicam_camera import GenICamCamera

try:
    from HRVision.HRCamera import Camera as HikCamera
except ImportError:
    HikCamera = None

__all__ = ["CameraController", "CameraWorker", "CAMERA_TYPES"]


# 可选相机类型注册表（demo/通用界面下拉用）：name -> (class, 参数模板说明)
CAMERA_TYPES = {
    "VideoCamera": (VideoCamera, {
        "source": "视频文件/RTSP地址/USB索引",
    }),
    "LocalCamera": (LocalCamera, {
        "dir": "图片目录或文件列表（递归扫描）",
    }),
    # GenICam 是协议类型：扫描 = 全部标准 GenTL producer 的设备合集
    "GenICam": (GenICamCamera, {
        "producer": "GenTL producer (.cti) 文件路径（初始参数填写/浏览选择或扫描带回）",
        "key": "设备序列号（扫描选择）",
    }),
}

# 厂商相机库（HRCamera 运行时按 cameraType 加载：hrBasler/hrDaHua/hrHik/...）。
# 参数约定与 HRCamera.Camera 一致（连接键选择 + 颜色格式），class 挂 HikCamera
#（HRCamera 未安装时发现列表为空，UI 只显示内置类型）。
_VENDOR_HINT = {
    "mode": "Serial/UserID",
    "key": "设备连接键（厂商设备列表）",
    "color": "True=彩色 RGB8_Packed / False=黑白 Mono8",
}


def discover_camera_types() -> "dict":
    """扫描 HRVision 包 bin/ 下 hr*.dll → 厂商相机类型注册表。

    例：hrBasler.dll → "hrBasler"、hrHik.dll → "hrHik"。
    camera_type 原样传给 HRCamera.Camera（GenCamera 按名加载 DLL）。
    """
    types = {}
    try:
        import HRVision
        bin_dir = os.path.join(os.path.dirname(HRVision.__file__), "bin")
        for fn in sorted(os.listdir(bin_dir)):
            if fn.lower().startswith("hr") and fn.lower().endswith(".dll"):
                types[fn[:-4]] = (HikCamera, dict(_VENDOR_HINT))
    except Exception:
        pass
    return types


def all_camera_types() -> "dict":
    """内置 + bin 扫描发现的全部相机类型（UI 下拉用）。"""
    merged = dict(CAMERA_TYPES)
    merged.update(discover_camera_types())
    return merged

# 命令常量
CMD_NEW = "new"
CMD_OPEN = "open"
CMD_CLOSE = "close"
CMD_DESTROY = "destroy"      # 销毁：关闭并释放相机实例（可再 new 其他类型）
CMD_START = "start"
CMD_STOP = "stop"
CMD_APPLY_CONFIG = "apply_config"
CMD_SET_PARAM = "set_param"
CMD_INFO = "info"
CMD_GET_TREE = "get_tree"    # 参数树查询（GetParameterTree → 数据点 cam1.param_tree 回传）
CMD_SET_CONFIG = "set_config"  # 配置连接参数（扫描选设备后生效；不动运行状态）
CMD_GET_VALUE = "get_value"    # 单节点读值（改值后精确回读更新，免全量刷新）


def enumerate_devices(camera_type: str, producer: str = "") -> list:
    """扫描相机类型下可用设备（厂商库 DLL 的 EnumerateDevices）。

    返回 [{"key","serial","model","vendor","ip","user_defined_name","producer"}...]；
    内置类型（VideoCamera/LocalCamera）无枚举 → 空列表。
    GenICam：显式 .cti（producer 参数）——不自动扫描任何目录。
    """
    if camera_type == "GenICam":
        # 协议类型扫描：显式提供 .cti 路径（无则空——提示先选择 cti）
        try:
            return GenICamCamera.enumerate_devices(producer) or []
        except Exception:
            return []
    if not camera_type.startswith("hr"):
        return []
    try:
        from HRVision.HRCamera import enumerate_cameras
        items = enumerate_cameras(camera_type) or []
        return [{"key": d.key, "serial": d.serial, "model": d.model,
                 "vendor": d.vendor, "ip": d.ip,
                 "user_defined_name": d.user_defined_name,
                 "interface": getattr(d, "interface_id", "")} for d in items]
    except Exception:
        return []


def build_camera_config(ctype: str, params: dict) -> "tuple[dict, str]":
    """相机类型 + 初始参数 → (CameraHost 配置, camera_type)。

    与 Worker._do_new 共用：VideoCamera→genVideoCameraConfig、LocalCamera→
    genLocalCameraConfig、厂商库（hr*）→genCameraConfig(mode/key/color)。
    """
    def _as_list(v):
        """"d:/path" 或 ["d:/a", ...] → 列表（防 list("字符串") 拆成字符）。"""
        if v is None:
            return []
        if isinstance(v, (str, int)):
            return [v]
        return list(v)

    cls = all_camera_types().get(ctype, (None, {}))[0]
    if cls is HikCamera:
        # 厂商库连接参数统一键：mode/key/color（兼容旧 hik_* 键）
        mode = str(params.get("mode", params.get("hik_mode", "Serial")))
        key = str(params.get("key", params.get("hik_key", "")))
        color = bool(params.get("color", params.get("hik_color", False)))
        # 采集卡相机（hrHikInterface）：设备带 interface（采集卡序列号）→ 配对连接
        interface = str(params.get("interface", "") or "")
        if interface:
            return CameraHost.genInterfaceCameraConfig(interface, key,
                                                       mode=mode, isColor=color), ctype
        return CameraHost.genCameraConfig(key, mode=mode, isColor=color), ctype
    if cls is LocalCamera:
        return (CameraHost.genLocalCameraConfig(
                    _as_list(params.get("dir") or params.get("source"))), "File")
    if cls is GenICamCamera:
        # producer = 显式 .cti 路径（初始参数/扫描设备带回）
        producer = str(params.get("producer", "") or "")
        key = str(params.get("key", params.get("source", "")) or "")
        return (CameraHost.genGenICamConfig(producer=producer, key=key), "GenICam")
    return (CameraHost.genVideoCameraConfig(
                _as_list(params.get("source") or params.get("dir"))), "Video")


def _gen_bus(name: str, mode: str = "process"):
    """命令总线：DataBus（小数据，maxlen=32）。

    mode="process"（默认）：共享内存队列——跨进程必需（auto 会各自退化成
    thread 队列，跨进程不通！）；mode="thread"：进程内多线程——同名单例复用
    （统一走 EvtBridge 的单例注册表，保证 Controller == Worker 同一队列）。
    """
    try:
        if mode == "thread":
            from HRVision.utils.evt_bridge import _thread_bus
            return _thread_bus(name)
        from HRVision.HRFlowController import DataBus
        return DataBus(name, maxlen=32, mode="process",
                       overflow="drop_new", max_msg_size=256 * 1024)
    except Exception:
        return None


class CameraController:
    """命令发起方（主进程/UI 侧）：send 发送命令，事件经 signal_instance 接收。"""

    def __init__(self, bus_name: str = "hrvision_cam_cmd", mode: str = "process"):
        self.bus = _gen_bus(bus_name, mode)
        self._seq = 0

    def send(self, cmd: str, **payload) -> bool:
        """发送命令（序列号自增 + 时间戳）。"""
        self._seq += 1
        msg = {"cmd": cmd, "ts": int(time.time()), "seq": self._seq,
               "payload": payload}
        if self.bus is None:
            return False
        try:
            return self.bus.put(msg)
        except Exception:
            return False


class CameraWorker:
    """命令接收方（相机进程内）：持 CameraHost 实例，消费命令并执行。

    进程边界：相机实例仅在 Worker 内创建（Worker 只在相机进程里实例化）；
    cycle() 与推流抓帧共存——「停止推流」只是不再取帧，相机仍可参数设置。
    """

    def __init__(self, bus_name: str = "hrvision_cam_cmd",
                 signal_instance=None, mode: str = "process"):
        # 进程退出尽力关闭相机（SDK 释放；强杀（TerminateProcess）不触发——
        # 虚拟相机等未正常关闭时需厂商工具重置，见 docs）
        import atexit as _atexit

        def _cleanup():
            try:
                if self.host is not None:
                    self.host.stop()
                    self.host.close()
                print("[cam] 进程退出：相机已尽力关闭", flush=True)
            except Exception:
                pass

        _atexit.register(_cleanup)
        # 内核：EvtBridge（通用事件桥）——后台线程阻塞消费命令（零轮询）+
        # Condition 事件等待（wait），并自动转发命令分发；相机命令集即其一例
        from HRVision.utils.evt_bridge import EvtBridge
        self._bridge = EvtBridge(bus_name, side="worker", mode=mode)
        self.bus = self._bridge.bus
        self._bridge.on_message(self._execute)   # 命令统一进 _execute 分发
        self.sig = signal_instance
        self.camera_cls = None
        self.camera_type = "Video"
        self.config = {}
        self.host: typing.Optional[CameraHost] = None
        self.created = False       # 相机实例已创建
        self.running = False       # 推流中（节点据其决定是否取帧）
        self._loop_count = 0

    def wait(self, timeout: typing.Optional[float] = None) -> bool:
        """阻塞等待命令执行完成（有命令立即返回 True；超时返回 False）。

        委托 EvtBridge（Condition）——命令后台线程执行完 notify，节点立即醒；
        空转纯睡眠（零轮询）。推流期给短超时（如 0.05s）按帧节奏检查取帧。
        """
        return self._bridge.wait(timeout)

    # ---------------- 事件 ---------------- #

    def _emit_state(self):
        if self.sig is None:
            return
        try:
            state = {"created": self.created,
                     "has_device": self.host is not None and self.host.dev is not None,
                     "opened": self.host.isOpened() if self.host else False,
                     "running": self.running,
                     "reconnecting": self.host.isReconnecting() if self.host else False,
                     "camera_type": self.camera_type,
                     "loop": self._loop_count}
            self.sig.camState.emit(state)
        except Exception:
            pass

    def _emit_event(self, text: str):
        if self.sig is None:
            return
        try:
            self.sig.camEvent.emit(text)
        except Exception:
            pass

    # ---------------- 命令执行 ---------------- #

    def _execute(self, msg: dict) -> None:
        """命令分发（收口）：无论成功/异常，结束时都发一次状态快照——
        保证 UI 状态锁/显示永远与 worker 真实状态同步（异常不清零解锁）。"""
        cmd = msg.get("cmd", "")
        payload = msg.get("payload", {}) or {}
        print("[cam] 收到命令: %s" % cmd, flush=True)
        try:
            self._dispatch_cmd(cmd, payload)
        finally:
            self._emit_state()

    def _dispatch_cmd(self, cmd: str, payload: dict) -> None:
        if cmd == CMD_NEW:
            self._do_new(payload)
        elif cmd == CMD_OPEN:
            self._do_open()
        elif cmd == CMD_CLOSE:
            self._do_close()
        elif cmd == CMD_DESTROY:
            self._do_destroy()
        elif cmd == CMD_START:
            self._do_start(payload)
        elif cmd == CMD_STOP:
            self._do_stop()
        elif cmd == CMD_APPLY_CONFIG:
            self._do_apply_config(payload)
        elif cmd == CMD_SET_PARAM:
            self._do_set_param(payload)
        elif cmd == CMD_INFO:
            self._emit_state()
        elif cmd == CMD_GET_TREE:
            self._do_get_tree()
        elif cmd == CMD_SET_CONFIG:
            self._do_set_config(payload)
        elif cmd == CMD_GET_VALUE:
            self._do_get_value(payload)
        else:
            self._emit_event("未知命令: %s" % cmd)
        self._emit_state()

    def _do_get_value(self, payload) -> None:
        """单节点读值 → 数据点回传（改值后精确更新树对应行）。"""
        key = (payload or {}).get("key", "")
        if not key or self.host is None or self.host.dev is None:
            return
        try:
            val, msg = self.host.getValue(key)
            ok = not bool(msg)
            print("[cam] get_value(%s) → %r (ok=%s)" % (key, val, ok), flush=True)
            from HRVision.utils.data_subject import DataSubject
            r = DataSubject("cam1.node_value").set({
                "key": key, "value": "" if val is None else str(val),
                "ok": ok, "msg": str(msg)})
            print("[cam] node_value 数据点 set: %s" % r, flush=True)
        except Exception as e:
            print("[cam] get_value(%s) 失败: %s" % (key, e), flush=True)

    def _do_set_config(self, payload) -> None:
        """设置连接参数（扫描选设备后）：仅更新 host 配置（不打开/不动运行态）。"""
        ctype = payload.get("camera_type") or self.camera_type
        if self.host is None:
            return
        try:
            inner = payload.get("params") or payload      # params 内嵌或平铺兼容
            config, camera_type = build_camera_config(ctype, inner)
            self.config = config
            self.host.setConfig(config)
            print("[cam] 连接配置已更新: %s" % config, flush=True)
            self._emit_event("连接配置已更新: %s" % self.camera_type)
        except Exception as e:
            print("[cam] set_config 失败: %s" % e, flush=True)
            self._emit_event("连接配置失败: %s" % e)

    def _do_get_tree(self) -> None:
        """参数树查询：GetParameterTree → 数据点回传（UI 订阅显示/修改）。"""
        if self.host is None or self.host.dev is None:
            print("[cam] 参数树: 相机未创建", flush=True)
            self._emit_event("参数树: 相机未创建")
            return
        try:
            ok = self.host.dev.IsOpened()
            if isinstance(ok, tuple):
                ok = ok[0]
            if not ok:
                print("[cam] 参数树: 相机未打开", flush=True)
                self._emit_event("参数树: 相机未打开（先打开相机）")
                return
            tree, _ = self.host.dev.GetParameterTree()
            text = tree if isinstance(tree, str) else str(tree)
            # 统一规范化：任何厂商（hr*/GenICam）导出 → 同一种格式给 UI（内部同步整理）
            from HRVision.utils.camera_tree import normalize_tree
            text = normalize_tree(text)
            print("[cam] 参数树已查询(规范化): %d chars" % len(text), flush=True)
            try:
                from HRVision.utils.data_subject import DataSubject
                ok2 = DataSubject("cam1.param_tree").set({
                    "type": self.camera_type, "tree": text})
                print("[cam] 数据点回传: %s" % ok2, flush=True)
            except Exception as e:
                print("[cam] 数据点回传异常: %s" % e, flush=True)
            self._emit_event("参数树已查询")
        except Exception as e:
            print("[cam] 参数树查询失败: %s" % e, flush=True)
            self._emit_event("参数树查询失败: %s" % e)

    def _do_new(self, payload) -> None:
        """创建相机实例：类型注册表查找（内置 + bin 扫描的厂商库）+ 实例化（未打开）。"""
        ctype = payload.get("camera_type", "VideoCamera")
        params = dict(payload.get("params") or {})
        cls = all_camera_types().get(ctype, (None, {}))[0]
        if cls is None:
            print("[cam] new 失败: 类型不支持 %s" % ctype, flush=True)
            self._emit_event("相机类型不支持: %s" % ctype)
            return
        self.config, self.camera_type = build_camera_config(ctype, params)
        print("[cam] new 完成: %s config=%s" % (ctype, self.camera_type), flush=True)
        self.camera_cls = cls
        self.host = CameraHost(camera_cls=cls, camera_type=self.camera_type,
                               config=self.config, check_interval=3.0,
                               reconnect_delay=1.0, probe_timeout=500)
        self.host.on_disconnect = lambda r: self._emit_event("掉线: %s" % r)
        self.host.on_reconnect = lambda n: self._emit_event("已恢复（第 %d 次尝试）" % n)
        self.created = True
        self._emit_event("相机已创建: %s" % ctype)

    def _do_open(self) -> None:
        if self.host is None:
            self._emit_event("相机未创建（先发送 new）")
            return
        ok, msg = self.host.open()
        self._emit_event("相机打开%s: %s" % ("成功" if ok else "失败", msg))

    def _do_close(self) -> None:
        if self.host is None:
            return
        self.host.stop()
        self.host.close()
        self.host = None
        self.created = False
        self.running = False
        self._emit_event("相机已关闭")

    def _do_destroy(self) -> None:
        """销毁相机：关闭 + 释放实例全部引用（可再 new 其他类型/来源）。"""
        if self.host is not None:
            self.running = False
            self.host.stop()
            self.host.close()
            self.host = None
        self.camera_cls = None
        self.camera_type = "Video"
        self.config = {}
        self.created = False
        self.running = False
        self._emit_event("相机已销毁")

    def _do_start(self, payload) -> None:
        if self.host is None:
            self._emit_event("相机未创建")
            return
        ok, msg = self.host.start(push=bool(payload.get("push", False)))
        self.running = ok
        self._emit_event("推流%s" % ("已启动" if ok else "启动失败: %s" % msg))

    def _do_stop(self) -> None:
        if self.host is None:
            return
        self.running = False
        self.host.stop()
        self._emit_event("推流已停止")

    def _do_apply_config(self, payload) -> None:
        if self.host is None:
            self._emit_event("相机未创建")
            return
        ok, msg = self.host.applyConfig(dict(payload.get("config") or {}))
        self._emit_event("配置切换%s" % ("成功" if ok else "失败: %s" % msg))

    def _do_set_param(self, payload) -> None:
        if self.host is None:
            self._emit_event("相机未创建")
            return
        key = payload.get("key", "")
        value = payload.get("value")
        if key == "exposure_time":
            ok, msg = self.host.setExposure(value)
        elif key == "gain":
            ok, msg = self.host.setGain(value)
        else:
            ok, msg = self.host.setValue(key, value)
        self._emit_event("参数 %s=%s %s" % (key, value, "成功" if ok else "失败: %s" % msg))

    # ---------------- 取帧（节点用） ---------------- #

    def grab(self, timeout: int = 1000) -> "tuple[bool, list[numpy.ndarray], str]":
        """推流中取一帧（失败 host 已自动掉线感知/后台重连）。

        厂商相机（hr*）默认 3000ms 等待：虚拟相机/低帧率相机帧间隔大，
        1s 等不到帧会误判掉线（与重连验证"假成功"构成抖动循环）。
        """
        if timeout == 1000 and (self.camera_type or "").startswith("hr"):
            timeout = 3000
        # 与命令执行互斥（EvtBridge._cond 锁）：stop/destroy/apply 与取帧不并发。
        with self._bridge._cond:
            if self.host is None:
                return False, [], "camera is not created"
            ok, frames, msg = self.host.read(timeout)
        if ok and frames:
            self._loop_count += 1
        return ok, frames, msg
