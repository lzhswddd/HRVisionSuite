# -*- coding: utf-8 -*-
"""进程隔离环境：用指定解释器（python_exe）拉起流程子进程。

背景：multiprocessing spawn 强制使用当前解释器（sys.executable）——
需要把某流程（如算法进程）跑在别的 Python 环境（如 D:/AIProgram/python.exe，
CUDA 环境）时，spawn 做不到。本模块提供「外部 spawn」路径：

    参数 pickle 到临时文件 → 目标 python 执行 bootstrap → 跑 _process_main
    （与 spawn 完全同构：控制通道用 multiprocessing.connection，
     锁用具名内核对象按名字重建）

核心机制：
    - 控制通道：Windows 命名管道（AF_PIPE）/ POSIX 回环 TCP
    - mp 同步原语：DataBus 锁为「具名」内核对象（Windows 具名 mutex /
      POSIX 具名信号量），标准 pickle 走 name 分支，子进程按名字打开同一
      内核对象 —— 无需句柄继承/传递
    - sys.path：bootstrap 注入 HRVision 包父目录（目标环境可能不在
      site-packages 安装）

使用（框架内部）：ProcessStartor.python_exe（节点级参数或 spec 顶层
python_exe），见 start_external_process()。

注意：目标环境必须能 import HRVision.HRFlowController（cp 版本匹配 +
PyHRVision 已安装或 .pyd/.so 可导入）；POSIX 具名信号量由主进程创建时
先 unlink 清残留（防崩溃后值被消耗 → 死锁）+ atexit 退出清理。
"""
import atexit as _atexit
import os
import pickle
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import multiprocessing as _mp
import multiprocessing.synchronize

def bootstrap_main(argv=None) -> int:
    """子进程入口（python -c 与打包 exe 共用）：读参数 → 连控制通道 → 跑 _process_main。

    argv 约定：`[入口, "--hrflow-bootstrap", <pkl路径>]` 或 `[入口, <pkl路径>]`。
    打包子进程（PyInstaller/Nuitka 等）入口一行调用：
        # flow_worker.py
        import sys
        from HRVision.ProcessIsolate import bootstrap_main
        sys.exit(bootstrap_main())
    注意：hrf_dir 用 append 兜底（目标环境优先，避免主环境 site-packages 污染——
    如主环境 torch 2.x 被 py39 子进程误用）；打包产物内框架已在 bundle 中。
    """
    argv = list(sys.argv if argv is None else argv)
    if "--hrflow-bootstrap" in argv:
        pkl_path = argv[argv.index("--hrflow-bootstrap") + 1]
    else:
        pkl_path = argv[1]
    with open(pkl_path, "rb") as f:
        p = pickle.load(f)
    d = p.get("hrf_dir")
    if d and d not in sys.path:
        sys.path.append(d)
    from multiprocessing.connection import Client
    conn = Client(p["conn_addr"])
    from HRVision.HRFlowController import _process_main
    _process_main(p["flow_id"], p["dir_path"], p["main_process_name"],
                  conn, p["proc_config"], codeDict=p.get("codeDict"), **p["kwargs"])
    return 0


# python -c 路径：一行委托 bootstrap_main（与打包 exe 同一实现）
_EXT_BOOTSTRAP = (
    "import sys\n"
    "from HRVision.ProcessIsolate import bootstrap_main\n"
    "sys.exit(bootstrap_main())\n"
)


class _PopenProcess:
    """subprocess.Popen 薄封装：API 对齐 multiprocessing.Process（is_alive/terminate/join/pid）。

    外部环境不是 multiprocessing spawn，进程对象是 Popen —— 补上 Process 的
    接口供 ProcessExecutor / _kill_pending_processes / Monitor 透明使用。
    """

    def __init__(self, popen):
        self._popen = popen
        self.pid = popen.pid

    def is_alive(self) -> bool:
        return self._popen.poll() is None

    def terminate(self) -> None:
        self._popen.terminate()

    def join(self, timeout=None) -> None:
        try:
            self._popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass

    def poll(self):
        return self._popen.poll()


def _is_python_interpreter(path: str) -> bool:
    """探测目标是否为 python 解释器（python.exe 也是 .exe，不能只看后缀）。

    运行 `path -V`：返回 0 且输出含 "Python" → 解释器；打包 exe 无 -V 语义 → False。
    每次外部启动探测一次（~50ms），避免 python.exe 被误判为打包产物。
    """
    try:
        r = subprocess.run([path, "-V"], capture_output=True, timeout=10)
        return r.returncode == 0 and b"Python" in (r.stdout + r.stderr)
    except Exception:
        return False


def _lock_kind() -> int:
    """当前平台 Lock 的 kind 值（C 层 SemLock 构造用）。"""
    probe = _mp.Lock()
    k = probe._semlock.kind
    del probe   # 匿名锁 GC 即释放句柄
    return k


def _unlink_named_sem(name: str) -> None:
    """POSIX：unlink 具名信号量（/dev/shm/sem.* 文件）；不存在时静默。"""
    try:
        os.unlink(os.path.join("/dev/shm", "sem." + name.lstrip("/")))
    except OSError:
        pass


def make_named_lock(name: str):
    """具名锁（外部解释器路径需要：pickle 按名字重建，无需句柄传递）。

    Windows：具名 mutex（kind=1）；POSIX：具名信号量（sem_open，先 unlink 防残留
    死锁，atexit 退出清理——子进程端 rebuild 不注册 unlink，主进程退出时
    sem_unlink 只标记删除，引用者不受影响）。
    """
    import _multiprocessing as _mpc
    full = "HRVisionLock_" + name
    if sys.platform != "win32":
        _unlink_named_sem(full)   # 清残留（崩溃后值可能被消耗为 0 → 死锁）
        _atexit.register(_unlink_named_sem, full)
    sem = _mpc.SemLock(_lock_kind(), 1, 1, full, False)
    w = _mp.synchronize.SemLock.__new__(_mp.synchronize.SemLock)
    w._semlock = sem
    w._make_methods()
    return w


def _reduce_semlock(sem):
    """mp 同步原语 → (kind, maxvalue, name)（具名锁 name 分支，子进程按名字打开）。"""
    return (_rebuild_semlock, (
        sem._semlock.kind, sem._semlock.maxvalue, sem._semlock.name))


def _rebuild_semlock(kind, maxvalue, name):
    """子进程端：按名字打开具名内核对象还原同步原语（Windows mutex / POSIX sem）。

    平台差异（实测）：
        Windows：C 层 _rebuild(0, ...) 不支持 name 分支（返回句柄 0 → 无效句柄）；
                构造 SemLock(kind, 1, maxvalue, name, unlink=False) —— CreateMutex
                同名返回已有对象句柄（unlink=False 容忍 ERROR_ALREADY_EXISTS）
        POSIX ：构造是排他创建（sem_open O_EXCL，同名抛 FileExistsError）；
                _rebuild(0, ...) 走 name 分支非排他打开（sem_open 不带 O_EXCL）
    """
    import _multiprocessing as _mpc
    if not name:
        raise RuntimeError("外部解释器路径需要具名同步原语（DataBus 已具名）")
    if sys.platform == "win32":
        sem = _mpc.SemLock(kind, 1, maxvalue, name, False)
    else:
        sem = _mpc.SemLock._rebuild(0, kind, maxvalue, name)
    w = _mp.synchronize.SemLock.__new__(_mp.synchronize.SemLock)
    w._semlock = sem
    w._make_methods()
    return w


def _ensure_external_pickle_support() -> None:
    """外部解释器路径的 pickle 支持：mp 同步原语按「名字」序列化（跨平台）。

    标准 pickle 对 SemLock 走 wrapper.__getstate__（assert_spawning 拒绝），
    注册 copyreg 让 SemLock/Lock/Event 等序列化为 (kind, maxvalue, name)——
    子进程端 _rebuild_semlock 按名字打开同一内核对象：
        Windows：具名 mutex（CreateMutex 同名复用）
        POSIX ：具名信号量（sem_open 同名复用）
    """
    try:
        import copyreg
        from multiprocessing import synchronize as _sync

        for _cls in (_sync.SemLock, _sync.Lock, _sync.RLock,
                     _sync.Semaphore, _sync.Event, _sync.BoundedSemaphore):
            try:
                copyreg.pickle(_cls, _reduce_semlock)
            except (TypeError, AttributeError):
                pass
    except Exception as e:   # 注册失败不致命：启动时再报
        print("外部解释器 pickle 支持注册失败: %s" % e, flush=True)


def start_external_process(python_exe, getProcess, dir_path, main_process_name,
                           signals=None, kwargs=None, priority=None,
                           cpu_affinity=None, codeDict=None):
    """用指定解释器拉起流程子进程；返回 ProcessExecutor（与 spawn 路径 API 一致）。

    参数（由 ProcessStartor._start_external 传入）：
        python_exe          目标环境 python 可执行文件（须能 import HRVision）
        getProcess          流程获取函数（ProcessStartor.getProcess）
        dir_path            Flow 目录；main_process_name  主流程名
        signals             信号转发白名单（proc_config["signals"]）
        kwargs              注入子进程 thData 的参数（含通道对象）
        priority / cpu_affinity   进程优先级 / 锁核（与 spawn 路径一致）

    内部：pickle 参数到临时文件 → Popen([python_exe, -c, bootstrap, tmp])
    → Listener 控制通道（Win 命名管道 / POSIX 回环）→ _process_main。
    """
    from multiprocessing.connection import Listener
    from HRVision.HRFlowController import (ProcessExecutor, _apply_cpu_affinity,
                                           _apply_process_priority,
                                           _pending_processes)

    _ensure_external_pickle_support()   # 具名同步原语按名字序列化（跨平台）
    if sys.platform == "win32":
        addr = r"\\.\pipe\hrflow_ext_%s" % uuid.uuid4().hex
        listener = Listener(addr, family="AF_PIPE")
    else:
        listener = Listener(("localhost", 0))
    flow_id = getProcess().localCodePath
    params = {"flow_id": flow_id or "", "dir_path": dir_path,
              "main_process_name": main_process_name,
              "proc_config": {"signals": signals or []},
              "codeDict": codeDict,
              "conn_addr": listener.address, "kwargs": kwargs or {},
              # HRVision 包所在目录的父目录（sys.path 需含父目录才能 import HRVision）；
              # 外部解释器可能不在 site-packages 安装，显式注入
              "hrf_dir": os.path.dirname(os.path.dirname(
                  os.path.abspath(sys.modules["HRVision.HRFlowController"].__file__)))}
    fd, tmp = tempfile.mkstemp(suffix=".pkl", prefix="hrflow_ext_")
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            pickle.dump(params, f)
        # 打包子进程（exe）：走 --hrflow-bootstrap 协议（入口调 bootstrap_main）；
        # 解释器：python -c 委托 bootstrap_main（同一实现）。
        # 注意：python.exe 也以 .exe 结尾 —— 探测确认是解释器才走 -c 协议
        if (not python_exe.lower().endswith(".exe")
                or _is_python_interpreter(python_exe)):
            cmd = [python_exe, "-c", _EXT_BOOTSTRAP, tmp]
        else:
            cmd = [python_exe, "--hrflow-bootstrap", tmp]
        proc = subprocess.Popen(cmd)
    except Exception as e:
        listener.close()
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise RuntimeError("外部环境启动失败（python_exe=%s）: %s" % (python_exe, e))

    # accept 与子进程失败并发等待：子进程提前退出（如 import 失败）不能永久阻塞
    result: dict = {}
    def _accept():
        try:
            result["conn"] = listener.accept()
        except Exception as e:
            result["err"] = e
    t = threading.Thread(target=_accept, daemon=True)
    t.start()
    for _ in range(600):   # 上限 30s
        if "conn" in result:
            break
        if "err" in result:
            listener.close()
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise RuntimeError("外部环境控制通道失败: %s" % result["err"])
        if proc.poll() is not None:
            listener.close()
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise RuntimeError("外部环境子进程退出（exit=%s，python_exe=%s）"
                               % (proc.returncode, python_exe))
        time.sleep(0.05)
    else:
        listener.close()
        proc.terminate()
        raise RuntimeError("外部环境控制通道连接超时（python_exe=%s）" % python_exe)
    listener.close()
    try:
        os.unlink(tmp)
    except OSError:
        pass

    wrapped = _PopenProcess(proc)
    _pending_processes.append(wrapped)   # 主进程退出时终止（避免残留持有段）
    if priority:
        _apply_process_priority(wrapped.pid, priority)
    if cpu_affinity:
        _apply_cpu_affinity(wrapped.pid, cpu_affinity)
    return ProcessExecutor(wrapped, result["conn"])
