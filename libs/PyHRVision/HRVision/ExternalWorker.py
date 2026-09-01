# -*- coding: utf-8 -*-
"""外部工具进程通信：拉起指定解释器/exe 的 worker 进程，TCP 帧协议请求/响应。

抽象了「调用外部工具进程」的通用模式（如 yolo demo 的 GPU worker 转发推理）：
    拉起进程（python 或打包 exe）→ READY 握手 → TCP 帧协议请求/响应
    → 崩溃自动重启 → 退出清理。

用法（客户端，算法进程内）：
    worker = ExternalWorker(
        launch=[python_exe, "-u", worker_script, "arg1"],
        log_path="worker.log",
    )
    worker.start()               # 拉起 + READY 握手（超时报错）
    result = worker.call(payload)  # 发送请求（bytes），阻塞收响应
    worker.close()               # 终止进程

worker 端（外部工具脚本，如 GPU 环境）：
    from HRVision.ExternalWorker import serve_forever, recv_msg, send_msg
    def handler(payload: bytes) -> bytes:
        # 处理一条请求，返回响应字节
        return b"ok"
    serve_forever(handler)       # 打印 "READY <port>" → 服务循环（连接断开自动退出）

协议（帧）：4 字节小端长度前缀 + 载荷（与 gpu_worker.py 一致，可跨 Python 版本）。

注意：
    - 本模块在 HRVision（3.12）与外部环境（3.9+）都会运行——注解用字符串形式
    - worker 脚本由外部解释器执行：不要使用比目标环境更新的 Python 语法
"""
import socket
import struct
import subprocess
import threading
import time


# =====================================================================
# 帧协议辅助（客户端与 worker 端共用）
# =====================================================================

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """读满 n 字节；连接断开抛 ConnectionError。"""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接断开")
        buf += chunk
    return buf


def send_msg(sock: socket.socket, payload: bytes) -> None:
    """发送一条消息（4 字节小端长度前缀 + 载荷）。"""
    sock.sendall(struct.pack("<I", len(payload)) + payload)


def recv_msg(sock: socket.socket) -> bytes:
    """接收一条消息；连接断开抛 ConnectionError。"""
    (n,) = struct.unpack("<I", recv_exact(sock, 4))
    return recv_exact(sock, n)


# =====================================================================
# worker 端：就绪握手 + 服务循环
# =====================================================================

def serve_forever(handler, host: str = "127.0.0.1",
                  ready_prefix: str = "READY") -> None:
    """worker 端服务循环：打印 "READY <port>" → accept → 逐条请求调 handler。

    handler(payload: bytes) -> bytes：处理一条请求，返回响应（可抛异常，连接断开）。
    连接断开（父进程退出/关闭）后进程自动退出——worker 随父进程生命周期收尾。
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, 0))
    port = server.getsockname()[1]
    server.listen(1)
    print("%s %d" % (ready_prefix, port), flush=True)
    while True:
        conn, _addr = server.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            while True:
                payload = recv_msg(conn)
                reply = handler(payload)
                send_msg(conn, reply)
        except (ConnectionError, OSError):
            pass
        finally:
            conn.close()


# =====================================================================
# 客户端：拉起外部工具进程 + 请求/响应
# =====================================================================

class ExternalWorker:
    """外部工具进程客户端：拉起 → 握手 → 请求/响应 → 崩溃自动重启。

    线程安全（call 串行）；call 时检测到连接断开或进程退出会自动重启并重试
    （restart_retries 次），适合长生命周期 worker（模型加载一次、之后每帧调用）。
    """

    def __init__(self, launch: list, ready_prefix: str = "READY",
                 ready_timeout: float = 40.0, log_path: "str | None" = None,
                 restart_retries: int = 1):
        self.launch = list(launch)          # 启动命令（[python/exe, ...参数]）
        self.ready_prefix = ready_prefix    # stdout 就绪标记（后跟 port）
        self.ready_timeout = ready_timeout  # 就绪等待上限（秒）
        self.log_path = log_path            # stderr 重定向文件（None = 继承）
        self.restart_retries = restart_retries  # call 失败自动重启重试次数
        self._lock = threading.Lock()
        self._proc: "subprocess.Popen | None" = None
        self._sock: "socket.socket | None" = None

    # ---------- 生命周期 ----------

    def start(self) -> None:
        """拉起进程 + READY 握手 + TCP 连接；超时/退出抛 RuntimeError。"""
        with self._lock:
            if self._sock is not None:
                return
            self._proc = subprocess.Popen(
                self.launch, stdout=subprocess.PIPE,
                stderr=(open(self.log_path, "a") if self.log_path else None),
                creationflags=0x08000000)   # CREATE_NO_WINDOW：不弹控制台窗口
            port = self._read_ready()
            if port is None:
                self.close()
                raise RuntimeError("外部工具启动失败（%s，日志: %s）"
                                   % (self.launch[0], self.log_path or "(继承)"))
            # READY 后 stdout 必须继续被读（排水线程）——否则 worker 此后 print
            # 写已停读的管道：实测 OSError [Errno 22] 直接把 worker 杀掉
            #（intermittent：管道缓冲恰未填满时正常，正是「时好时坏」的根源）
            self._start_stdout_drain()
            self._sock = socket.create_connection(("127.0.0.1", port), timeout=30)
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def close(self) -> None:
        """关闭连接并终止进程（幂等）。"""
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            if self._proc is not None:
                try:
                    self._proc.terminate()
                except OSError:
                    pass
                self._proc = None

    # ---------- 请求/响应 ----------

    def call(self, payload) -> bytes:
        """发送请求并阻塞收响应；连接断开/进程退出自动重启重试。

        payload 可为 bytes（单条）或 list[bytes]（多段请求——worker 端按段
        recv_msg 接收，如「帧头 + 帧数据」两段协议）。
        """
        parts = payload if isinstance(payload, (list, tuple)) else [payload]
        for attempt in range(self.restart_retries + 1):
            try:
                self.start()
                assert self._sock is not None
                for p in parts:
                    send_msg(self._sock, p)
                return recv_msg(self._sock)
            except (ConnectionError, OSError, RuntimeError) as e:
                self.close()
                if attempt >= self.restart_retries:
                    raise
                time.sleep(0.2)   # 重启间隔（等端口释放）
        raise RuntimeError("外部工具调用失败")   # unreachable

    # ---------- 内部 ----------

    def _read_ready(self) -> "int | None":
        """读进程 stdout 直到 "READY <port>"；退出/超时返回 None。"""
        deadline = time.time() + self.ready_timeout
        assert self._proc is not None and self._proc.stdout is not None
        while time.time() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                if self._proc.poll() is not None:
                    return None
                continue
            text = line.decode("utf-8", "replace").strip()
            if text.startswith(self.ready_prefix):
                parts = text.split()
                if len(parts) >= 2:
                    return int(parts[1])
        return None

    def _start_stdout_drain(self) -> None:
        """READY 握手后保持 stdout 排水：管道始终被读，worker 的 print 不再
        阻塞/触发 OSError 22（实证：握手后不读 stdout → worker 打印即被杀）。

        行内容：
            - 配置了 log_path → 追加写入同一日志文件（"|out| " 前缀，与 stderr
              分流，排障时仍能看到 worker 的输出）
            - 未配置 → 直接丢弃（只保证管道通畅）
        进程退出/close() 后 readline 返回 b"" → 线程自然结束（daemon，不阻塞退出）。
        """
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        logf = None
        if self.log_path:
            try:
                logf = open(self.log_path, "a", encoding="utf-8", errors="replace")
            except OSError:
                logf = None

        def _drain() -> None:
            try:
                for line in iter(lambda: proc.stdout.readline(), b""):
                    if logf is not None:
                        try:
                            logf.write("|out| " + line.decode("utf-8", "replace"))
                            logf.flush()
                        except OSError:
                            pass
            except Exception:
                pass
            finally:
                if logf is not None:
                    try:
                        logf.close()
                    except Exception:
                        pass

        threading.Thread(target=_drain, daemon=True,
                         name="ExternalWorker-stdout").start()
