# -*- coding: utf-8 -*-
"""PLC 通信：cModule/PLCInterface 库（PLCDevice.dll + HslCommunication.dll 封装）。

支持协议（plc_type，见 PLCDevice.h）：Modbus / ModbusRtu / ModbusAscii /
Profinet_Siemens_S200Smart / Profinet_Melsec_Mc / Profinet_Omron_Fins 等。

DLL 依赖目录（pyd 所在，可用环境变量 PLC_LIB_DIR 覆盖）：
    d:/Python/cModule/PLCInterface/build/bin/Release/
    PLCInterface.pyd / PLCDevice.dll / HslCommunication.dll / lua.dll / toluapp.dll

地址语义（HslCommunication）：
    "0".."n"    Modbus 线圈/寄存器（十进制地址）
    "M100"      M 区（西门子）  "D100"  D 区（三菱）等按 plc_type 而定
type 参数：bool / short / int / float（writeString 走单独接口）

两种运行模式（pipeline.json 节点参数 plc_mode）：
    mock : 本机起 pymodbus TCP 从站模拟 PLC（无真实 PLC 环境演示；外部工具可连）
    tcp  : 通过 PLCInterface 连真实 PLC（plc_host/plc_port）

约定地址（可配置）：trigger_addr 触发拍照（消费后清零）/ ok_addr OK / ng_addr NG。
"""
import os
import sys
import threading

_PLC_DIR: str = os.environ.get(
    "PLC_LIB_DIR", r"D:/Python/cModule/PLCInterface/build/bin/Release")


def _ensure_lib() -> None:
    """把 PLCInterface.pyd 目录加入搜索路径（pyd 与依赖 DLL 同目录）。"""
    if _PLC_DIR not in sys.path:
        sys.path.insert(0, _PLC_DIR)
    if os.path.isdir(_PLC_DIR):
        os.add_dll_directory(_PLC_DIR)


_ensure_lib()
from PLCInterface import PLC as _PLC   # noqa: E402

from pymodbus.datastore import (ModbusDeviceContext, ModbusSequentialDataBlock,
                                ModbusServerContext)
from pymodbus.server import StartTcpServer


class MockPlcServer:
    """内置 Modbus TCP 从站（mock 模式：模拟 PLC 设备端，演示/联调用）。"""

    def __init__(self, port: int = 8000, coils: int = 8):
        self.port: int = port
        self.coils: int = coils
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        block = ModbusSequentialDataBlock(0, [0] * self.coils)
        ctx = ModbusServerContext(
            devices=ModbusDeviceContext(di=block, co=block, ir=block, hr=block),
            single=True)
        StartTcpServer(context=ctx, address=("127.0.0.1", self.port))

    def start(self) -> None:
        """启动从站（后台线程，daemon 随进程退出）。"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()


class Plc:
    """PLC 客户端封装（PLCInterface.PLC）：触发读 / OK-NG 写。"""

    def __init__(self, plc_type: str = "Modbus", host: str = "127.0.0.1",
                 port: int = 8000, trigger_addr: str = "0",
                 ok_addr: str = "1", ng_addr: str = "2",
                 addr_type: str = "bool"):
        self.plc_type: str = plc_type
        self.host: str = host
        self.port: int = port
        self.trigger_addr: str = trigger_addr
        self.ok_addr: str = ok_addr
        self.ng_addr: str = ng_addr
        self.addr_type: str = addr_type
        self._plc: _PLC = _PLC()
        self._plc.createTcp("demo", plc_type, host, port)

    def connect(self) -> bool:
        """打开连接；成功返回 True。"""
        try:
            return bool(self._plc.openConnection())
        except Exception:
            return False

    def is_connected(self) -> bool:
        try:
            return bool(self._plc.isConnected())
        except Exception:
            return False

    def read_trigger(self) -> bool:
        """读触发地址；返回 True 表示有触发（1/True）。"""
        try:
            v = self._plc.readNumber(self.trigger_addr, self.addr_type)
            return str(v).strip().lower() in ("1", "true")
        except Exception:
            return False

    def reset_trigger(self) -> None:
        """触发消费后清零（下次上升沿再触发）。"""
        try:
            self._plc.writeNumber(self.trigger_addr, "0", self.addr_type)
        except Exception:
            pass

    def write_result(self, ok: bool) -> bool:
        """写判定结果：OK → ok_addr=1/ng_addr=0；NG 反之。成功返回 True。"""
        try:
            self._plc.writeNumber(self.ok_addr, "1" if ok else "0", self.addr_type)
            self._plc.writeNumber(self.ng_addr, "1" if not ok else "0", self.addr_type)
            return True
        except Exception:
            return False

    def close(self) -> None:
        try:
            self._plc.close()
        except Exception:
            pass
