# -*- coding: utf-8 -*-
"""相机托管控制类 CameraHost：开关相机 / 控制推流 / 配置管理 / 掉线检测与自动重连。

兼容统一 CameraBase 接口的任意相机类：
    - HRVision.HRCamera.Camera      工业相机（GigE/USB 等，HKVision 系）
    - HRVision.utils.LocalCamera    本地图片集（camera_type="File"）
    - HRVision.utils.VideoCamera    视频文件 / RTSP·HTTP 网络流 / USB 设备索引

推流模型：统一拉取式（GetCameraBuffer），托管线程循环取帧并转发 on_frame 回调；
探活线程周期读帧验证健康，掉线后自动重连（Stop → SetConfig → Open → Grab，
保留配置；不用 Close——Local/Video 的 Close 会清空源列表）。

用法:
    from HRVision.utils.camera_host import CameraHost
    from HRVision.utils.video_camera import VideoCamera

    host = CameraHost(camera_cls=VideoCamera, camera_type="Video",
                      config=CameraHost.genVideoCameraConfig(["videos/ccd1.avi"]))
    host.on_frame = lambda frames: display(frames[0])
    host.on_disconnect = lambda reason: print("掉线:", reason)
    host.open()
    host.start()          # 推流 + 掉线检测自动启动
    ...
    host.stop()           # 停推流（相机保持打开）
    host.close()          # 关闭相机 + 停所有线程

说明：
    - 探活读帧会从推流中取走一帧（对实时流/循环视频无感知；探活周期可配 check_interval）
    - RTSP 卡死时 VideoCapture.read() 无超时，探活可能被阻塞——属底层固有限制
"""
import numpy
import threading
import typing

__all__ = ["CameraHost"]


class CameraHost:
    """相机托管控制类（相机类无关：构造传入实现了 CameraBase 接口的类即可）。"""

    def __init__(self, camera_cls: type = None, camera_type: str = "Camera",
                 config: typing.Optional[dict] = None, auto_open: bool = False,
                 **kwargs):
        """
        Args:
            camera_cls: 相机类（HRCamera.Camera / LocalCamera / VideoCamera 等）；
                        None 默认 HRCamera.Camera
            camera_type: 传给相机构造函数的类型名（"Camera"/"File"/"Video" 等）
            config: 相机配置字典（SetConfig）；None = 空
            auto_open: 构造后立即 open()
            **kwargs: 调优参数（check_interval 探活周期 / probe_timeout 探活超时 /
                      reconnect_delay 重连间隔 / max_reconnect 最大重连次数 /
                      stream_timeout 推流取帧超时）
        """
        try:
            from HRVision.HRCamera import Camera as _DefaultCam
        except ImportError:
            _DefaultCam = None
        self.camera_cls = camera_cls or _DefaultCam
        self.camera_type = camera_type
        self.config = dict(config or {})
        self.dev = None                      # 相机设备实例
        self.on_frame = None                 # 推流回调 on_frame(frames: list[np.ndarray])
        self.on_disconnect = None            # 掉线回调 on_disconnect(reason: str)
        self.on_reconnect = None             # 重连成功回调 on_reconnect(attempt: int)
        self.check_interval = kwargs.pop("check_interval", 3.0)    # 掉线检测周期（秒）
        self.probe_timeout = kwargs.pop("probe_timeout", 500)      # 探活取帧超时（毫秒）
        self.reconnect_delay = kwargs.pop("reconnect_delay", 2.0)  # 重连间隔（秒）
        self.max_reconnect = kwargs.pop("max_reconnect", 0)        # 最大重连次数；0=无限
        self.stream_timeout = kwargs.pop("stream_timeout", 1000)   # 推流取帧超时（毫秒）
        self._lock = threading.RLock()
        self._read_lock = threading.Lock()   # 串行化 GetCameraBuffer：VideoCamera/RTSP
                                             # 底层非线程安全，并发读会崩
        self._streaming = False
        self._reconnecting = False
        self._reconnect_count = 0
        self._stop_event = threading.Event()
        self._stream_thread: typing.Optional[threading.Thread] = None
        self._health_thread: typing.Optional[threading.Thread] = None
        self._reconnect_thread: typing.Optional[threading.Thread] = None
        self._was_streaming = False
        if auto_open:
            self.open()

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------

    def setCameraClass(self, camera_cls: type) -> None:
        """更换相机类（未打开时生效）。"""
        self.camera_cls = camera_cls

    def setCameraType(self, camera_type: str) -> None:
        """更换相机类型名（未打开时生效）。"""
        self.camera_type = camera_type

    def setConfig(self, config: dict) -> None:
        """设置相机配置（下次 open/重连时生效）。"""
        self.config = dict(config or {})

    def getConfig(self) -> dict:
        """获取当前配置。"""
        if self.dev is not None:
            try:
                return self.dev.GetConfig()
            except Exception:
                pass
        return dict(self.config)

    @classmethod
    def genCameraConfig(cls, key: str, mode="Serial", isColor: bool = False) -> dict:
        """工业相机连接配置（参考 CameraEx.genCameraConfig）。

        mode: "Serial"（序列号连接）/ "UserID"（自定义名连接）
        """
        config = {}
        if mode == "Serial":
            config["ConnectKey"] = "SerialNumber"
            config["SerialNumber"] = key
        elif mode == "UserID":
            config["ConnectKey"] = "UserID"
            config["UserDefinedName"] = key
        else:
            raise ValueError("Invalid connection mode: %s" % mode)
        if isColor:
            config["DefaultMonoFormat"] = "RGB8_Packed"
        else:
            config["DefaultColorFormat"] = "Mono8"
            config["DefaultMonoFormat"] = "Mono8"
        return config

    @classmethod
    def genInterfaceCameraConfig(cls, interfacekey: str, key: str, mode="Serial",
                                 isColor: bool = False) -> dict:
        """带接口筛选的工业相机连接配置（多相机同型号时按接口区分）。"""
        config = cls.genCameraConfig(key, mode, isColor)
        suffix = "SerialNumber" if mode == "Serial" else "UserDefinedName"
        config[suffix + "_Interface"] = interfacekey
        return config

    @classmethod
    def genLocalCameraConfig(cls, filePaths: list) -> dict:
        """本地图片集配置（LocalCamera：文件或目录列表，目录递归扫描图片）。"""
        return {"camera_type": "File", "file_paths": list(filePaths)}

    @classmethod
    def genVideoCameraConfig(cls, filePaths: list) -> dict:
        """视频/网络流配置（VideoCamera：视频文件、RTSP·HTTP 地址或 USB 索引）。"""
        return {"camera_type": "Video", "file_paths": list(filePaths)}

    @classmethod
    def genGenICamConfig(cls, producer: str = "", key: str = "") -> dict:
        """通用 GenICam 相机配置（GenTL producer .cti 路径 + 设备序列号）。"""
        return {"camera_type": "GenICam", "producer": str(producer or ""),
                "key": str(key or "")}

    # ------------------------------------------------------------------
    # 开关相机
    # ------------------------------------------------------------------

    def open(self) -> "tuple[bool, str]":
        """打开相机（已打开则跳过）。"""
        with self._lock:
            if self.dev is not None:
                try:
                    if self.dev.IsOpened()[0]:
                        return True, "Camera already opened."
                except Exception:
                    pass
            if self.camera_cls is None:
                return False, "No camera class provided."
            try:
                self.dev = self.camera_cls(self.camera_type)
                self.dev.SetConfig(self.config)
            except Exception as e:
                self.dev = None
                return False, "Failed to create camera: %s" % e
            try:
                ret, msg = self.dev.Open()
            except Exception as e:
                ret, msg = False, str(e)
            if not ret:
                try:
                    self.dev.Close()
                except Exception:
                    pass
                self.dev = None
                return False, msg
            self._reconnect_count = 0
            return True, msg

    def close(self) -> "tuple[bool, str]":
        """停止推流、停止检测线程并关闭相机。"""
        self.stop()
        self._stop_health_check()
        with self._lock:
            if self.dev is None:
                return True, "Camera is not opened."
            try:
                ret, msg = self.dev.Close()
                return ret, msg
            except Exception as e:
                return False, str(e)
            finally:
                self.dev = None

    def isOpened(self) -> bool:
        """相机是否已打开。"""
        with self._lock:
            if self.dev is None:
                return False
            try:
                return bool(self.dev.IsOpened()[0])
            except Exception:
                return False

    def applyConfig(self, config: dict) -> "tuple[bool, str]":
        """应用新配置并立即生效：Stop → SetConfig → Open →（运行中则 Grab）。

        注意：多数相机 SetConfig 只改参数、不动运行中的源/句柄（如 VideoCamera
        的 file_paths 切换须 Stop/Open 后生效）——配置切换统一走本方法。
        失败返回 (False, msg)，当前配置保持不变。
        """
        with self._lock:
            if self.dev is None:
                return False, "Camera is not opened."
            dev = self.dev
            was_streaming = self._streaming
        with self._read_lock:      # 与推流/探活/重连的底层操作串行
            try:
                dev.Stop()
            except Exception:
                pass
            try:
                dev.SetConfig(config)
                ret, msg = dev.Open()
                if ret and was_streaming:
                    ret2, msg = dev.Grab()
                    ret = ret and ret2
            except Exception as e:
                ret, msg = False, str(e)
            if ret:
                self.config = dict(config)
                return True, msg
            # 失败：还原旧配置并重新打开，保持相机可用
            try:
                dev.SetConfig(self.config)
                dev.Open()
                if was_streaming:
                    dev.Grab()
            except Exception:
                pass
            return False, msg

    # ------------------------------------------------------------------
    # 控制推流
    # ------------------------------------------------------------------

    def start(self, push: bool = True) -> "tuple[bool, str]":
        """推流启动。

        Args:
            push: True = 推送模式（Grab + 推流线程 + 掉线检测线程，on_frame 取帧）；
                  False = 轮询模式（仅置运行状态，read() 独占取帧——取图失败即感知，
                  不启推流/探活线程；适合外部循环手动取图的场景）
        """
        with self._lock:
            if self.dev is None:
                return False, "Camera is not opened. Call open() first."
            if self._streaming:
                return True, "Camera is already streaming."
            try:
                ret, msg = self.dev.Grab()
            except Exception as e:
                return False, "Failed to start grabbing: %s" % e
            if not ret:
                return False, msg
            self._streaming = True
        self._stop_event.clear()
        if push:
            self._stream_thread = threading.Thread(target=self._stream_loop,
                                                   name="CameraHost-stream", daemon=True)
            self._stream_thread.start()
            self._health_thread = threading.Thread(target=self._health_loop,
                                                   name="CameraHost-health", daemon=True)
            self._health_thread.start()
        return True, msg

    def stop(self) -> "tuple[bool, str]":
        """停止推流（相机保持打开）。"""
        with self._lock:
            self._streaming = False
        self._stop_event.set()
        for t in (self._stream_thread, self._health_thread, self._reconnect_thread):
            if t is not None:
                t.join(timeout=2.0)
        self._stream_thread = self._health_thread = self._reconnect_thread = None
        with self._lock:
            if self.dev is None:
                return True, "Camera is not opened."
            try:
                return self.dev.Stop()
            except Exception as e:
                return False, str(e)

    def isStreaming(self) -> bool:
        """是否正在推流。"""
        return self._streaming

    # ------------------------------------------------------------------
    # 拉取式读取（托管线程之外也可手动取帧）
    # ------------------------------------------------------------------

    def read(self, timeout: int = 1000, notify: bool = True
             ) -> "tuple[bool, list[numpy.ndarray], str]":
        """读取一帧（取图接口）：返回 (ok, frames, msg)；未推流/掉线时 ok=False。

        notify=True 时：取图失败即判定掉线——立即回调 on_disconnect 并启动后台
        重连（不等探活周期），调用方可马上感知。重连期间依然返回失败帧。
        """
        with self._lock:
            dev = self.dev
            if dev is None:
                return False, [], "Camera is not opened."
            # 推送模式下推流线程独占读（底层非线程安全）；轮询模式（start(push=False)）才能 read
            pushing = self._stream_thread is not None and self._stream_thread.is_alive()
        if pushing:
            return False, [], ("Camera is streaming in push mode; use on_frame "
                               "or stop() first. (start(push=False) for read-mode).")
        try:
            with self._read_lock:
                ok, frames, msg = dev.GetCameraBuffer(timeout)  # 形参名 timeOut（驼峰），必须位置传参
        except Exception as e:
            ok, frames, msg = False, [], str(e)
        if not ok and notify:
            self._notify_disconnect("read")
        return ok, frames, msg

    def isReconnecting(self) -> bool:
        """是否正在自动重连。"""
        return self._reconnecting

    # ------------------------------------------------------------------
    # HRCamera 扩展接口（仅工业相机有这些方法时可用）
    # ------------------------------------------------------------------

    def _ext(self, name: str, *args):
        """调用相机扩展方法；不存在时返回 (False, "unsupported")。"""
        with self._lock:
            if self.dev is None:
                return False, "Camera is not opened."
            fn = getattr(self.dev, name, None)
            if fn is None:
                return False, "Camera class does not support %s." % name
            try:
                return fn(*args)
            except Exception as e:
                return False, str(e)

    def setExposure(self, timeMs) -> "tuple[bool, str]":
        return self._ext("SetExposureTime", timeMs)

    def getExposure(self) -> "tuple[float, str]":
        return self._ext("GetExposureTime")

    def setGain(self, gain) -> "tuple[bool, str]":
        return self._ext("SetGain", gain)

    def getGain(self) -> "tuple[float, str]":
        return self._ext("GetGain")

    def setValue(self, key: str, value) -> "tuple[bool, str]":
        return self._ext("SetValue", key, value)

    def getValue(self, key: str) -> "tuple[typing.Any, str]":
        return self._ext("GetValue", key)

    def loadConfig(self, fileName: str) -> bool:
        return bool(self._ext("LoadConfig", fileName)[0])

    def saveConfig(self, fileName: str) -> bool:
        return bool(self._ext("SaveConfig", fileName)[0])

    # ------------------------------------------------------------------
    # 推流线程
    # ------------------------------------------------------------------

    def _stream_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                dev = self.dev
                streaming = self._streaming
                reconnecting = self._reconnecting
            if dev is None or not streaming:
                break
            if reconnecting:            # 重连期间让出读权（worker 独占验证帧），避免并发读
                self._stop_event.wait(0.05)
                continue
            try:
                with self._read_lock:
                    ok, frames, msg = dev.GetCameraBuffer(self.stream_timeout)
            except Exception:
                ok = False
                msg = "GetCameraBuffer raised."
            if ok and frames:
                cb = self.on_frame
                if cb is not None:
                    try:
                        cb(frames)
                    except Exception:
                        pass
            else:
                # 推流失败（掉线/源耗尽）→ 立即通知掉线并重连（有防抖）；
                # "not grabbing" 仅在用户 stop 后（streaming=False）视为正常暂停
                text = str(msg).lower()
                if "not grabbing" in text and not self._streaming:
                    pass
                else:
                    self._notify_disconnect("stream")
                self._stop_event.wait(0.2)

    # ------------------------------------------------------------------
    # 掉线检测与重连
    # ------------------------------------------------------------------

    def _health_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self.check_interval)
            if self._stop_event.is_set():
                break
            with self._lock:
                dev = self.dev
                reconnecting = self._reconnecting
            if dev is None or reconnecting:   # 重连期间让出读权（worker 独占）
                continue
            if not self._probe(dev):
                self._notify_disconnect("health")

    def _probe(self, dev) -> bool:
        """探活：读一帧验证。未推流不算掉线；读帧失败/异常视为掉线。"""
        try:
            with self._read_lock:
                ok, _frames, msg = dev.GetCameraBuffer(self.probe_timeout)
            if ok:
                return True
            text = str(msg)
            # "not grabbing" 仅在用户 stop 后视为正常；运行中（streaming）即故障
            if "not grabbing" in text.lower() and not self._streaming:
                return True
            return False
        except Exception:
            return False

    def _notify_disconnect(self, source: str) -> None:
        """掉线通知：唯一入口（read/推流线程/探活线程共用），防抖——重连进行中
        或相机已关不重复触发；立即回调 on_disconnect 并后台重连。"""
        with self._lock:
            if self._reconnecting or self.dev is None or not self._streaming:
                return
            self._reconnecting = True
            self._was_streaming = True   # 掉线发生在推流中，重连后恢复推流
        reason = "Camera connection lost (source=%s)." % source
        if self.on_disconnect is not None:
            try:
                self.on_disconnect(reason)
            except Exception:
                pass
        else:
            print("[CameraHost] %s" % reason, flush=True)
        self._start_reconnect()

    def _start_reconnect(self) -> None:
        t = threading.Thread(target=self._reconnect_worker,
                             name="CameraHost-reconnect", daemon=True)
        self._reconnect_thread = t
        t.start()

    def _reconnect_worker(self) -> None:
        """后台重连：Stop → SetConfig → Open → Grab（保留配置，不用 Close——Local/
        Video 的 Close 会清空源列表）；失败按 reconnect_delay 间隔重试。"""
        attempt = 0
        while not self._stop_event.is_set():
            if self.max_reconnect and attempt >= self.max_reconnect:
                break
            attempt += 1
            with self._lock:
                dev = self.dev
            if dev is None:
                break
            try:
                dev.Stop()
            except Exception:
                pass
            try:
                dev.SetConfig(self.config)
                ret, msg = dev.Open()
                if ret:
                    # 验证一帧：Open 成功但读不到帧（如网络假恢复）算重连失败，
                    # 避免"假成功→瞬断→假成功"抖动循环
                    with self._read_lock:
                        ret2, _f, _m = dev.GetCameraBuffer(self.probe_timeout)
                    if ret2 or "not grabbing" in str(_m).lower():
                        dev.Grab()
                        self._reconnect_count = attempt
                        with self._lock:
                            # 重连期间用户若手动 stop（_streaming=False），不擅自恢复推流
                            self._streaming = self._was_streaming and self._streaming
                    else:
                        ret = False
                        msg = "reopened but frame read failed: %s" % _m
            except Exception as e:
                ret, msg = False, str(e)
            if ret:
                with self._lock:
                    self._reconnecting = False
                if self.on_reconnect is not None:
                    try:
                        self.on_reconnect(attempt)
                    except Exception:
                        pass
                return
            self._stop_event.wait(self.reconnect_delay)
        with self._lock:
            self._reconnecting = False

    def _stop_health_check(self) -> None:
        self._stop_event.set()
        for t in (self._stream_thread, self._health_thread, self._reconnect_thread):
            if t is not None:
                t.join(timeout=2.0)
        self._stream_thread = self._health_thread = self._reconnect_thread = None

    # ------------------------------------------------------------------

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
