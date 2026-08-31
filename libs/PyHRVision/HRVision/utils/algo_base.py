# -*- coding: utf-8 -*-
"""算法抽象基类 + 线程池调度（AlgoBase / AlgoManager）。

AlgoBase 统一算法生命周期与接口：
    导入导出（from_config / export）｜参数配置（configure）｜调用运行（process）
    获取结果（process 返回 + info()）｜多线程安全（instance 级 _lock 保护可用状态，
    帧不进不出引用）｜可注册进 AlgoManager 线程池（多实例并发分配）

约定（与「相机与算法模块接口规范」对齐）：
    - process(frame) -> (res_frame, info)；info 必须 JSON 可序列化（走信号/UI）
    - 帧只读，不得原地修改；res 为新帧（大图走通道/显示槽）
    - 实例内部共享状态（模板缓存/模型句柄）：默认 _lock 串行保护——
      多线程并发同一实例自动排队；多实例并行由 AlgoManager 线程池调度
    - 模型/资源加载放 setup（不阻塞节点首帧前的配置；加载失败 ready=False）

用法（节点/服务侧）：
    algo = TemplateMatchAlgo.from_config("blob", {"size": 64})
    algo.configure(threshold=0.8)
    res, info = algo.process(frame)          # 单线程
    # 池化：
    mgr = AlgoManager(workers=4)
    mgr.register("algo_1", algo)
    info = mgr.run("algo_1", frame)          # 同步提交（池内 worker 执行）
    future = mgr.submit("algo_2", frame)     # 异步
    mgr.shutdown()
"""
import abc
import threading
import time
import typing

import numpy as np

__all__ = ["AlgoBase", "AlgoManager"]


class AlgoBase(abc.ABC):
    """算法基类：任何算法（检测/分类/比对/透传）继承并实现两个钩子即可。"""

    def __init__(self, name: str = ""):
        self.name = name
        self.config = {}          # 导入的配置（setup 加载用，构造后只读）
        self.params = {}          # 运行参数（configure 写入；setup 之后只读，可序列化）
        self._ready = False
        self._lock = threading.RLock()   # 实例级锁：process 串行（内部状态无竞争）
        self._last_info = {}      # 最近一次结果摘要（info() 读取）

    # ---------------- 导入 / 导出 / 配置 ---------------- #

    @classmethod
    def from_config(cls, name: str, config: dict, **params) -> "AlgoBase":
        """导入：按 config 创建实例并加载模型/资源（ready 标志见 .ready）。"""
        algo = cls(name)
        ok = algo.setup(dict(config))
        algo.configure(**params)
        if not ok:
            algo._ready = False
        return algo

    def setup(self, config: dict) -> bool:
        """加载/初始化：子类覆写 _load_impl；成功置 ready。"""
        self.config = dict(config)
        ok = self._load_impl(self.config)
        self._ready = bool(ok)
        return self._ready

    def _load_impl(self, config: dict) -> bool:
        """子类钩子：加载模型/模板/初始化句柄；返回是否成功（默认成功）。"""
        return True

    def configure(self, **params) -> None:
        """参数配置（运行前/运行间隙调用；apply 为子类钩子）。"""
        self.params.update(params)
        self._apply_params(self.params)

    def _apply_params(self, params: dict) -> None:
        """子类钩子：参数生效（可选覆写；默认空实现）。"""
        pass

    def export(self) -> dict:
        """导出：{name, class, config, params, ready}（JSON 可序列化，供存档/UI）。"""
        return {"name": self.name, "class": type(self).__name__,
                "config": dict(self.config), "params": dict(self.params),
                "ready": self._ready}

    # ---------------- 运行 / 结果 ---------------- #

    def process(self, frame: np.ndarray, **extra) -> "tuple[np.ndarray, dict]":
        """运行一帧（多线程安全：实例级锁自动串行，子类无需分心）。

        Args:
            frame: 输入帧（只读，不得原地修改）
            **extra: 本次调用的临时参数（不进 params）
        Returns:
            (res_frame, info)；info JSON 可序列化（见规范）
        """
        if not self._ready:
            raise RuntimeError("algo %r not ready: setup() 未成功/failed" % self.name)
        t0 = time.time()
        with self._lock:
            res, info = self._process_impl(frame, **extra)
        info = dict(info or {})
        info.setdefault("algo", self.name)
        info.setdefault("time_ms", round((time.time() - t0) * 1000, 1))
        self._last_info = info
        return res, info

    @abc.abstractmethod
    def _process_impl(self, frame: np.ndarray, **extra) -> "tuple[np.ndarray, dict]":
        """子类实现：处理一帧，返回 (结果图, 摘要 dict)。"""

    def info(self) -> dict:
        """最近一次结果摘要（成功/失败都有字段）。"""
        return dict(self._last_info)

    @property
    def ready(self) -> bool:
        return self._ready

    def close(self) -> None:
        """释放资源（子类覆写 _close_impl）。"""
        try:
            self._close_impl()
        except Exception:
            pass
        self._ready = False

    def _close_impl(self) -> None:
        pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class AlgoManager:
    """算法实例注册表 + 线程池调度（多线程安全）。

    注册多个算法实例（可同型号不同参数/不同模型），submit/run 提交到内部
    ThreadPoolExecutor（Pool 惰性创建，workers=None = cpu 核心数）。
    run 为同步（submit + result），供节点/单线程调用；submit 为异步（Future）。
    """

    def __init__(self, workers: typing.Optional[int] = None):
        import os
        if workers is None:
            workers = max(1, (os.cpu_count() or 4) - 1)
        self.workers = workers
        self._instance_pool: typing.Dict[str, AlgoBase] = {}
        self._reg_lock = threading.RLock()
        self._pool = None          # ThreadPoolExecutor（惰性）
        self._last_results: typing.Dict[str, dict] = {}

    # ---------------- 注册 ----------------

    def register(self, key: str, algo: AlgoBase) -> None:
        with self._reg_lock:
            self._instance_pool[key] = algo

    def get(self, key: str) -> AlgoBase:
        with self._reg_lock:
            return self._instance_pool.get(key)

    def keys(self):
        with self._reg_lock:
            return list(self._instance_pool.keys())

    # ---------------- 池 ----------------

    def _get_pool(self):
        if self._pool is None:
            from concurrent.futures import ThreadPoolExecutor
            self._pool = ThreadPoolExecutor(max_workers=self.workers,
                                            thread_name_prefix="AlgoPool")
        return self._pool

    def submit(self, key: str, frame: np.ndarray, **extra):
        """异步提交（线程池分配执行），返回 Future（实例未注册抛 ValueError）。"""
        algo = self.get(key)
        if algo is None:
            raise ValueError("algo instance not registered: %s" % key)
        return self._get_pool().submit(algo.process, frame, **extra)

    def run(self, key: str, frame: np.ndarray, timeout: float = 60.0,
            **extra) -> typing.Any:
        """同步运行（池内 worker 执行）；返回 (res_frame, info)。"""
        fut = self.submit(key, frame, **extra)
        result = fut.result(timeout)
        self._last_results[key] = dict(result[1])
        return result

    def run_all(self, frame: np.ndarray, timeout: float = 60.0) -> dict:
        """并发运行全部实例：{key: (res_frame, info)}（fan-out 多算法并行）。"""
        futures = {k: self.submit(k, frame)
                   for k in self.keys()}
        out = {}
        for k, fut in futures.items():
            try:
                out[k] = fut.result(timeout)
                self._last_results[k] = dict(out[k][1])
            except Exception as e:
                out[k] = (None, {"algo": k, "error": str(e)})
        return out

    def last_info(self, key: str) -> dict:
        return dict(self._last_results.get(key, {}))

    def shutdown(self, wait: bool = True) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=wait)
            self._pool = None
