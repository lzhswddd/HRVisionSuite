# -*- coding: utf-8 -*-
"""PLCInterface：PLC 通信库（PLCDevice.dll + HslCommunication.dll 封装）。

支持协议（plc_type）：Modbus / ModbusRtu / ModbusAscii /
Profinet_Siemens_S200Smart / Profinet_Melsec_Mc / Profinet_Omron_Fins 等。
地址语义（HslCommunication）："0".."n" Modbus 线圈/寄存器、"M100" M 区等。

DLL 依赖（本包目录）：PLCDevice.dll（原生，依赖下面的 C# 程序集）+
HslCommunication.dll（C# 程序集，经 CLR 解析——不走标准 DLL 搜索路径）。
本模块在 import 时把包目录注入 DLL 搜索路径 + PATH：
    - os.add_dll_directory：原生 DLL（PLCDevice/lua/toluapp）加载
    - PATH 注入：.NET 程序集探测（部分 CLR 宿主查 PATH）/ 兜底
避免「包安装在 site-packages、从其他目录运行时引用不到 DLL」。
"""
import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
if sys.platform == "win32":
    try:
        os.add_dll_directory(_PKG)
    except (AttributeError, OSError):
        pass
    os.environ["PATH"] = _PKG + os.pathsep + os.environ.get("PATH", "")

from .PLCInterface import PLC   # noqa: F401,E402  re-export（pyd 与包同名，作为子模块暴露）
