# -*- coding: utf-8 -*-
"""检测功能块 VisionUnit（订阅式）：配置驱动、组件间以「主题订阅」无感连接。

拓扑（单元内自动接线；外部消费同样用订阅）：
    CameraActor --publish frames--> AlgoActor --publish results-->
    AggregatorActor --publish verdicts--> NotifyActor
    外部（UI/框架侧）：bus.subscribe("unit.verdicts", cb) 等即收结果

订阅框架 TopicBus：线程安全 pub/sub，dispatcher 单线程串行消费（慢消费者
背压安全），publish 非阻塞（队列 overflow=drop_oldest，帧类主题天然最新优先）。

配置（JSON 可序列化，全部声明式）：
    {
      "id": "unit1",
      "camera": {"type": "VideoCamera", "params": {"source": "videos/ccd1.avi"}},
      "stream": {"to_ui": true, "display_divisor": 3},
      "algo": {"name": "TemplateMatchAlgo", "config": {"load": 1}},
      "notify": [{"type": "log"}],
      "topics": {"frames": "unit1.frames", "results": "unit1.results",   # 默认主题名可改
                 "verdicts": "unit1.verdicts"}
    }

订阅接入示例（外部/集成方）：
    unit = VisionUnit.from_config(cfg, ui=window)
    unit.bus.subscribe("unit1.verdicts", on_verdict)   # 结果订阅
    unit.start(); ...; unit.close()
"""
import threading
import time
from typing import Callable, Dict, List, Optional

from HRVision.utils.camera_host import CameraHost
from HRVision.utils.topic_bus import TopicBus   # v2：每订阅者独立队列 + retained + 通配

__all__ = ["VisionUnit", "SceneHub", "SceneAggregator"]


class SceneAggregator:
    """结果汇总：多结果 → 判定（OK/NG/计数）。项目规则可继承覆写 aggregate。"""

    def __init__(self, tag: str = ""):
        self.tag = tag
        self.history: "List[dict]" = []
        self.count_ok = 0
        self.count_ng = 0

    def aggregate(self, info: dict) -> dict:
        err = info.get("error")
        ok = err is None
        if ok:
            self.count_ok += 1
        else:
            self.count_ng += 1
        verdict = {"tag": self.tag, "ok": ok, "count_ok": self.count_ok,
                   "count_ng": self.count_ng, "info": info}
        self.history.append(verdict)
        self.history = self.history[-64:]
        return verdict


class VisionUnit:
    """检测功能块（订阅式）：配置构建 → start（CameraActor 推帧）→ 订阅链自动流转。"""

    def __init__(self, config: dict, ui=None):
        # ---- 配置校验（配错早盘报错） ----
        if not config or not isinstance(config, dict):
            raise ValueError("VisionUnit 配置须为 dict")
        for required in ("id", "camera", "algo"):
            if not config.get(required):
                raise ValueError("配置缺少必填项: %r（配置示例见模块 docstring）" % required)
        self.config = config
        self.ui = ui
        self.unit_id = config.get("id", "unit1")
        self.pane = (config.get("ui") or {}).get("pane", self.unit_id)
        topics = config.get("topics") or {}
        self.T_FRAMES = topics.get("frames", self.unit_id + ".frames")
        self.T_RESULTS = topics.get("results", self.unit_id + ".results")
        self.T_VERDICTS = topics.get("verdicts", self.unit_id + ".verdicts")

        self.bus = TopicBus(name=self.unit_id)

        # ---- 相机（配置参数 → CameraHost 结构：复用 cam_control 解析） ----
        cam_cfg = config.get("camera", {}) or {}
        ctype = cam_cfg.get("type", "VideoCamera")
        params = dict(cam_cfg.get("params") or {}) or {}
        from HRVision.utils.cam_control import build_camera_config, all_camera_types
        cam_cfg_dict, cam_type = build_camera_config(ctype, params) if params else (
            {}, "Video")
        cls = all_camera_types().get(ctype, (None, {}))[0] or _camera_cls(ctype)
        self.camera = CameraHost(camera_cls=cls,
                                 camera_type=cam_type or _camera_type_name(ctype),
                                 config=cam_cfg_dict, check_interval=3.0,
                                 reconnect_delay=2.0, probe_timeout=1000)

        # ---- 算法 / 汇总 / 通知 ----
        algo_cfg = config.get("algo", {}) or {}
        self.algo = _build_algo(algo_cfg.get("name", "TemplateMatchAlgo"),
                                algo_cfg.get("config", {}) or {},
                                **dict(algo_cfg.get("params") or {}))
        self.aggregator = SceneAggregator(
            (config.get("aggregate") or {}).get("tag", self.unit_id))
        from HRVision.utils.notify import build_notifiers
        self.notifiers = build_notifiers(config.get("notify") or [{"type": "log"}])

        # 订阅接线（单元内自动）：
        #   frames(results图) 由 UI/外部订阅 → 这里挂 aggregator 与 notifier
        self.bus.subscribe(self.T_RESULTS, self._on_result)
        self._stream = config.get("stream") or {}
        self.to_ui = bool(self._stream.get("to_ui", True))
        self.display_divisor = int(self._stream.get("display_divisor", 3))

        self._loop = 0
        self.last_verdict = None
        self._stop_evt = threading.Event()
        self._cam_th = None
        # 运行时指标（可观测：框架隐藏实现中吐一点真相给用户/监控）
        self._stats = {"started_at": 0.0, "loops": 0, "verdicts": 0,
                       "ok": 0, "ng": 0, "algo_ms": 0.0, "errors": 0}

    # ---------------- 生命周期 ----------------

    @classmethod
    def from_config(cls, config: dict, ui=None) -> "VisionUnit":
        return cls(config, ui)

    def start(self) -> "tuple[bool, str]":
        if self._cam_th is not None and self._cam_th.is_alive():
            return True, "already running"
        ok, msg = self.camera.open()
        if not ok:
            return False, "相机打开失败: %s" % msg
        ok, msg = self.camera.start(push=False)
        if not ok:
            return False, "推流启动失败: %s" % msg
        self._stop_evt.clear()
        self._stats["started_at"] = time.time()
        self._cam_th = threading.Thread(target=self._camera_loop,
                                        name="VisionUnit-cam-%s" % self.unit_id,
                                        daemon=True)
        self._cam_th.start()
        return True, msg

    def stop(self) -> None:
        """停止检测循环/推流（订阅链与总线保持——可 start 重启）。"""
        self._stop_evt.set()
        if self._cam_th is not None:
            self._cam_th.join(timeout=3.0)
            self._cam_th = None
        self.camera.stop()

    def close(self) -> None:
        try:
            self.stop()
            self.camera.close()
            self.bus.close()
            for n in self.notifiers:
                try:
                    n.close()
                except Exception:
                    pass
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ---------------- CameraActor 循环 ----------------

    def _camera_loop(self) -> None:
        from HRVision import ndarray_to_qimage
        while not self._stop_evt.is_set():
            ok, frames, msg = self.camera.read()
            if not ok or not frames:
                self._stop_evt.wait(0.05)
                continue
            frame = frames[0]
            self._loop += 1
            t0 = time.time()
            try:
                res, info = self.algo.process(frame, meta={"unit": self.unit_id,
                                                           "loop": self._loop})
            except Exception as e:
                res, info = None, {"error": str(e)}
                self._stats["errors"] += 1
            self._stats["loops"] = self._loop
            self._stats["algo_ms"] = round((time.time() - t0) * 1000, 1)
            # 发布结果（订阅链：汇总 → 通知 → 外部 UI）
            self.bus.publish(self.T_RESULTS, {"frame": res, "info": info,
                                              "loop": self._loop})
            # 相机原图直推 UI（可选：预览不走算法）
            if self.to_ui and res is not None and \
                    self._loop % max(1, self.display_divisor) == 0:
                try:
                    if self.ui is not None:
                        title = "%s | 预览 | loop=%d" % (self.unit_id, self._loop)
                        self.ui.set_image(self.pane, ndarray_to_qimage(res), title)
                except Exception:
                    pass

    def _on_result(self, payload: dict) -> None:
        """汇总 + 外设通知（订阅回调在本订阅者队列线程，与相机循环解耦）。"""
        info = payload.get("info", {})
        verdict = self.aggregator.aggregate(info)
        self._stats["verdicts"] += 1
        if verdict.get("ok"):
            self._stats["ok"] += 1
        else:
            self._stats["ng"] += 1
        self.last_verdict = verdict
        frame = payload.get("frame")
        if frame is not None:
            try:
                if self.ui is not None:
                    from HRVision import ndarray_to_qimage
                    title = "%s | %s | loop=%d" % (
                        self.unit_id, "OK" if verdict.get("ok") else "NG",
                        payload.get("loop", 0))
                    self.ui.set_image(self.pane, ndarray_to_qimage(frame), title)
            except Exception:
                pass
        for n in self.notifiers:
            try:
                n.notify(verdict)
            except Exception as e:
                self._emit("通知失败: %s" % e)
        self.bus.publish(self.T_VERDICTS, verdict)

    def _emit(self, text: str) -> None:
        if self.ui is not None:
            try:
                self.ui.append_event("[%s] %s" % (self.unit_id, text))
            except Exception:
                pass

    # ---------------- 便捷对外订阅 ----------------

    def on_verdict(self, handler: Callable) -> tuple:
        """订阅汇总结果（便捷入口；retained——订阅即得最近一条）。"""
        return self.bus.subscribe(self.T_VERDICTS, handler)

    def on_result(self, handler: Callable) -> tuple:
        """订阅算法结果 {(frame, info)}（retained——订阅即得最近一条）。"""
        return self.bus.subscribe(self.T_RESULTS, handler)

    def stats(self) -> dict:
        """运行时指标快照（FPS/OK/NG/耗时/错误数）——框架侧可观测点。"""
        elapsed = time.time() - self._stats.get("started_at", time.time())
        fps = round(self._stats["loops"] / elapsed, 1) if elapsed > 0 else 0.0
        return dict(self._stats, fps=fps, unit=self.unit_id)


class SceneHub:
    """多单元编排：注册多个 VisionUnit 配置 → 一个订阅总线（通配消费）。

    hub = SceneHub.from_configs([UNIT1, UNIT2], ui=window)
    hub.subscribe("*.verdicts", on_verdict)     # 通配：所有单元结果一处收
    hub.start_all(); ...; hub.close()
    """

    def __init__(self, units: "list[VisionUnit] | None" = None):
        self.units: "list[VisionUnit]" = list(units or [])
        self.bus = None       # Unity 尚未聚合总线（v2 演进：单元共享可选 bus）

    @classmethod
    def from_configs(cls, configs: "list[dict] | None", ui=None,
                     shared_bus=None) -> "SceneHub":
        hub = cls()
        for cfg in configs or []:
            unit = VisionUnit.from_config(cfg, ui=ui)
            if shared_bus is not None:     # 聚合总线（单元间互联）
                unit.bus = shared_bus
            hub.units.append(unit)
        hub.bus = shared_bus
        return hub

    def subscribe(self, pattern: str, handler) -> tuple:
        """订阅（通配）：对每个单元总线自动 apply（或共享总线单条）。"""
        if self.bus is not None:
            return self.bus.subscribe(pattern, handler)
        tokens = []
        for u in self.units:
            tokens.append(u.bus.subscribe(pattern, handler))
        return tokens

    def start_all(self) -> "list[tuple]":
        return [u.start() for u in self.units]

    def stats(self) -> "dict[str, dict]":
        return {u.unit_id: u.stats() for u in self.units}

    def close(self) -> None:
        for u in self.units:
            try:
                u.close()
            except Exception:
                pass


# ------------------------------------------------------------------
# 构建支持
# ------------------------------------------------------------------

def _camera_cls(ctype: str):
    try:
        from HRVision.utils.cam_control import all_camera_types
        cls = all_camera_types().get(ctype, (None, {}))[0]
        if cls is not None:
            return cls
    except Exception:
        pass
    return _import_cls(ctype) or _DEFAULT_CAM()


def _camera_type_name(ctype: str) -> str:
    return {"VideoCamera": "Video", "LocalCamera": "File"}.get(ctype, ctype)


def _DEFAULT_CAM():
    from HRVision.utils.video_camera import VideoCamera
    return VideoCamera


def _import_cls(name: str):
    for mod in ("HRVision.utils.algo_base",):
        try:
            m = __import__(mod, fromlist=[name])
            obj = getattr(m, name, None)
            if obj is not None:
                return obj
        except Exception:
            pass
    return None


def _build_algo(name: str, config: dict, **params):
    """算法工厂：优先服务层类（TemplateMatchAlgo 等可 from_config）。"""
    for mod in ("services.algo_engine", "HRVision.utils.algo_base"):
        try:
            m = __import__(mod, fromlist=[name])
            cls = getattr(m, name, None)
            if cls is not None and hasattr(cls, "from_config"):
                return cls.from_config(name, dict(config), **params)
        except Exception:
            pass
    from HRVision.utils.algo_base import AlgoBase
    if hasattr(AlgoBase, "from_config"):
        try:
            return AlgoBase.__subclasses__()[0].from_config(name, dict(config), **params)
        except Exception:
            pass
    raise RuntimeError("算法类未找到: %s（实现 AlgoBase 子类）" % name)
