# -*- coding: utf-8 -*-
"""PLC 统一接口（框架通用组件）：pythonnet + HslCommunication **直连 C#**（仅此一条路）。

已实测的库形态（本 DLL，机型可见）：
    - 厂商类平铺 HslCommunication 根命名空间：SiemensS7Net / SiemensFetchWriteNet /
      MelsecMcNet / MelsecMcAsciiNet / MelsecA1ENet / OmronFinsNet / AllenBradleyNet /
      ModbusTcpNet / ModbusRtuOverTcp（及 KUKA/EFORT 等通讯类）
    - 全部继承 NetworkDeviceBase → **统一 API**：ConnectServer/ConnectClose +
      ReadBool/ReadInt16/ReadUInt16/ReadString + WriteBool/WriteInt16/WriteString
      （地址串透传，各厂自己的地址语法：S7 "DB1.DBX0.0"/"DB1.DBW2"、
      Melsec "M100"/"D100"、Fins "M10"/"D100"、AB "B3[0].0"/"FLOAT[0]"、Modbus "0"）

统一接口（同一调用形态，不抽象各厂地址语义——那是各厂协议精髓，直接透传）：
    conn = Plc("siemens_s7",  "192.168.0.10", 102)     # 或 modbus/melsec/omron_fins/…
    conn.connect() / is_connected() / close()
    conn.read_bool("DB1.DBX0.0") / write_bool(..., on)
    conn.read_int16("DB1.DBW2")  / write_int16(..., v)
    conn.read_string(addr)       / write_string(addr, s)
    # Modbus 协议额外: read_coil/write_coil/read_register/write_register

授权（set_authorization）：当前随包 DLL 无 Authorization 成员（免注册版，实测）；
    若替换为正版需要授权的 dll，组件自动探测 HslCommunication.Authorization 并调
    SetAuthorization(code, devcode)；也可在构造前用环境变量 HRVISION_HSL_AUTH=
    "公司码:设备码" 自动注册（敏感信息只走环境/配置，**不进源码与 git**）。

托管库落位（关键坑）：HslCommunication.dll 由 pythonnet 托管解析，解析基准 =
进程基目录（sys.prefix）——ensure_managed_dll() 自动从 HRVision/bin 补放。

注意：Python 3.9 兼容（字符串注解）。module 级不 import clr（延迟——无 pythonnet
环境构造时给明确报错）。
"""
import os
import shutil
import sys


def set_authorization_code(code: str) -> bool:
    """HslCommunication 授权注册（static SetAuthorizationCode，反射式调用）。

    实测：pythonnet 常规属性/import 路径无法解析该类型（Assembly 类型装载碎），
    反射 Invoke 100% 可用（与 PLCDevice.cpp 的 C++/CLI 调用同语义）。
    **授权码敏感**：仅经环境变量 HRVISION_HSL_AUTH 或运行时显式传入，
    禁止写入源码/日志/仓库。
    """
    try:
        ClrPlc._ensure()     # dll 先装载（否则 AppDomain 里找不到装配 → False）
        import clr           # pythonnet 先装载（System 由 pythonnet 提供）
        import System
        _arg = System.String(str(code))    # 显式 System.String（实测自动转换判 False！
        for _a in list(System.AppDomain.CurrentDomain.GetAssemblies()):   # 差异点）
            if str(_a.GetName().Name) == "HslCommunication":
                _t = _a.GetType("HslCommunication.Authorization")
                if _t is not None:
                    _r = _t.GetMethod("SetAuthorizationCode").Invoke(None, [_arg])
                    return True if _r is None else bool(_r)
        return False
    except Exception as e:
        print("[plc] 授权注册失败:", e, flush=True)
        return False


def set_authorization(code: str = "", dev_code: str = "") -> bool:
    """兼容入口：注册码为主要参数（dev_code 在 SetAuthorizationCode API 中无需）。"""
    return set_authorization_code(code or dev_code)


_AUTH_TIP_SHOWN = [False]


def _autoload_auth() -> None:
    """构造前自动注册：环境变量 HRVISION_HSL_AUTH（=注册码；兼容 "code:devcode"）。

    授权码敏感：只认环境/显式传入——不读文件、不进 git。未配置时提示一次
    （部分 dll 功能在未授权态可能受限——参照 PLCDevice.cpp 的 RegisterDevice 语义）。
    """
    v = os.environ.get("HRVISION_HSL_AUTH", "").strip()
    if not v:
        if not _AUTH_TIP_SHOWN[0]:
            _AUTH_TIP_SHOWN[0] = True
            print("[plc] 提示: 未配置 Hsl 授权码（环境变量 HRVISION_HSL_AUTH），"
                  "部分功能可能受限", flush=True)
        return
    code, _, _dev = v.partition(":")
    set_authorization_code(code)


def hrvision_bin_dir() -> str:
    """框架内置 DLL 环境（HRVision/bin，与相机 DLL 同库惯例）。"""
    try:
        import HRVision as _pkg
        d = os.path.join(os.path.dirname(os.path.abspath(_pkg.__file__)), "bin")
        return d if os.path.isdir(d) else ""
    except Exception:
        return ""


def ensure_managed_dll() -> str:
    """HslCommunication.dll 补放到 CLR 解析基准（python.exe 所在目录）。

    实测：托管库解析基准 = 进程基目录（环境根）——bin/sys.path 注册都不覆盖。
    基准缺失时从源（HRVision/bin → PLC_LIB_DIR → 旧编译目录）复制一份。
    """
    src = ""
    for d in (hrvision_bin_dir(), os.environ.get("PLC_LIB_DIR", ""),
              r"D:/Python/cModule/PLCInterface/build/bin/Release"):
        c = os.path.join(d, "HslCommunication.dll") if d else ""
        if c and os.path.isfile(c):
            src = c
            break
    if not src:
        return ""
    dst = os.path.join(sys.prefix, "HslCommunication.dll")
    if not os.path.isfile(dst):
        try:
            shutil.copy2(src, dst)
            print("[plc] HslCommunication.dll 已补放到环境根（CLR 解析基准）", flush=True)
        except Exception:
            pass
    return dst


class _Vendor:
    """厂商定义：类名 + 构造形态（实测 pythonnet 重载序列）。"""

    def __init__(self, cls, ctor="ip_port", default_port=5000):
        self.cls = cls
        self.ctor = ctor            # ip_port / plctype_ip_port / ip_only
        self.default_port = default_port


def _vendor_table(clr_H) -> "dict[str, _Vendor]":
    """protocol 名 → _Vendor。类名平铺 HslCommunication 根（本 DLL 实测形态）。"""
    return {
        "modbus": _Vendor(clr_H.ModbusTcpNet, "ip_port", 502),
        "modbus_rtu": _Vendor(clr_H.ModbusRtuOverTcp, "ip_port", 502),
        "siemens_s7": _Vendor(clr_H.SiemensS7Net, "plctype_ip", 102),
        "siemens_fetch_write": _Vendor(clr_H.SiemensFetchWriteNet, "ip_port", 102),
        "melsec_mc": _Vendor(clr_H.MelsecMcNet, "ip_port", 6000),
        "melsec_mc_ascii": _Vendor(clr_H.MelsecMcAsciiNet, "ip_port", 6000),
        "melsec_a1e": _Vendor(clr_H.MelsecA1ENet, "ip_port", 6000),
        "omron_fins": _Vendor(clr_H.OmronFinsNet, "ip_port", 8500),
        "allen_bradley": _Vendor(clr_H.AllenBradleyNet, "ip_port", 44818),
    }


def _resolve_s7_type(_H, plc_type) -> object:
    """西门子 plcType 解析（'S1200'/'S300'/'s200smart'… → SiemensPLCS 枚举）。"""
    name = str(plc_type or "S1200").upper().replace("-", "").replace("_", "")
    for cand in ("S1200", "S1500", "S400", "S300", "S200SMART", "S200"):
        if name == cand.replace("_", ""):
            return getattr(_H.SiemensPLCS, cand)
    return _H.SiemensPLCS.S1200


class ClrPlc:
    """直连 C# 后端（pythonnet + HslCommunication.dll，唯一后端——无 pyd 中间件）。"""

    _loaded = False

    @classmethod
    def _ensure(cls) -> None:
        if cls._loaded:
            return
        try:
            import clr
        except ImportError:
            raise RuntimeError("pythonnet 未安装（pip install pythonnet）")
        _d = hrvision_bin_dir() or os.environ.get("PLC_LIB_DIR", "")
        for part in ("HslCommunication.dll",):
            p = os.path.join(_d, part) if _d else ""
            if p and os.path.isfile(p):
                clr.AddReference(p)
        else:
            clr.AddReference("HslCommunication")   # 已装环境（pip/全局）时兜底
        cls._loaded = True

    def __init__(self, protocol: str = "modbus", host: str = "127.0.0.1",
                 port: int = 0, plc_type=None):
        self._ensure()
        _autoload_auth()
        import HslCommunication as _H
        v = _vendor_table(_H).get((protocol or "modbus").lower())
        if v is None:
            raise ValueError("未知厂商协议: %r（可用: %s）"
                             % (protocol, ", ".join(sorted(_vendor_table(_H)))))
        self._protocol = (protocol or "modbus").lower()
        self._port = int(port or v.default_port)
        # 构造形态（pythonnet 重载序列实测）
        if v.ctor == "plctype_ip":                       # 西门子 (pltype, ip)
            self._net = v.cls(_resolve_s7_type(_H, plc_type), host)
        elif v.ctor == "ip_port":
            self._net = v.cls(host, self._port)
        else:                                            # ip_only
            self._net = v.cls(host)
        self._conn = False

    @property
    def protocol(self) -> str:
        return self._protocol

    def connect(self) -> bool:
        try:
            self._conn = bool(self._net.ConnectServer().IsSuccess)
        except Exception:
            self._conn = False
        return self._conn

    def is_connected(self) -> bool:
        return self._conn

    # ---- 统一读/写（各厂地址语法透传；值类型按 API 分） ----

    def read_bool(self, addr) -> bool:
        try:
            r = self._net.ReadBool(str(addr))
            return bool(r.IsSuccess and r.Content)
        except Exception:
            return False

    def write_bool(self, addr, on: bool) -> bool:
        try:
            return bool(self._net.WriteBool(str(addr), bool(on)).IsSuccess)
        except Exception:
            return False

    def read_int16(self, addr):
        try:
            r = self._net.ReadInt16(str(addr))
            return int(r.Content) if r.IsSuccess else None
        except Exception:
            return None

    def write_int16(self, addr, value) -> bool:
        try:
            return bool(self._net.WriteInt16(str(addr), int(value)).IsSuccess)
        except Exception:
            return False

    def read_string(self, addr) -> "str | None":
        try:
            r = self._net.ReadString(str(addr))
            return str(r.Content) if r.IsSuccess else None
        except Exception:
            return None

    def write_string(self, addr, s: str) -> bool:
        try:
            return bool(self._net.WriteString(str(addr), str(s)).IsSuccess)
        except Exception:
            return False

    # ---- Modbus 语义（地址 "0"/寄存区 ReadHoldingRegisters） ----

    def read_coil(self, addr) -> bool:
        return self.read_bool(addr)

    def write_coil(self, addr, on: bool) -> bool:
        return self.write_bool(addr, on)

    def read_register(self, addr, count: int = 1):
        try:
            r = self._net.ReadHoldingRegisters(str(addr), int(count))
            return list(r.Content) if r.IsSuccess else None
        except Exception:
            return None

    def write_register(self, addr, value) -> bool:
        try:
            return bool(self._net.Write(str(addr), int(value)).IsSuccess)
        except Exception:
            return False

    read_bit = read_coil
    write_bit = write_coil

    def close(self):
        try:
            self._net.ConnectClose()
        except Exception:
            pass


class Plc:
    """PLC 客户端统一门：**CLR 直连（pythonnet + HslCommunication）**，无 pyd 回退。

    用法：
        conn = Plc("siemens_s7", "192.168.0.10")     # 默认端口随厂商
        conn = Plc("modbus", "127.0.0.1", 502)
        conn.connect() / read_bool / write_bool / read_int16 / write_int16 / ...
        业务位名映射（I/O 表）在项目层，地址语法按厂商（见模块 docstring）。
    """

    def __init__(self, protocol: str = "modbus", host: str = "127.0.0.1",
                 port: int = 0, plc_type=None):
        ensure_managed_dll()
        self._impl = ClrPlc(protocol, host, port, plc_type)

    @property
    def backend(self) -> str:
        return "clr"

    @property
    def protocol(self) -> str:
        return self._impl.protocol

    def connect(self) -> bool:
        return self._impl.connect()

    def is_connected(self) -> bool:
        return self._impl.is_connected()

    def read_bool(self, addr) -> bool:
        return self._impl.read_bool(addr)

    def write_bool(self, addr, on: bool) -> bool:
        return self._impl.write_bool(addr, on)

    def read_int16(self, addr):
        return self._impl.read_int16(addr)

    def write_int16(self, addr, value) -> bool:
        return self._impl.write_int16(addr, value)

    def read_string(self, addr):
        return self._impl.read_string(addr)

    def write_string(self, addr, s: str) -> bool:
        return self._impl.write_string(addr, s)

    read_coil = ClrPlc.read_coil     # 仅 Modbus 语义下有效（地址透传）
    write_coil = ClrPlc.write_coil
    read_register = ClrPlc.read_register
    write_register = ClrPlc.write_register
    read_bit = read_coil
    write_bit = write_coil

    def close(self):
        self._impl.close()


def backend_status() -> str:
    """当前环境后端探测（无副作用）：'clr'（可用）/ 'none'（缺 pythonnet/dll）。"""
    try:
        ClrPlc._ensure()
        return "clr"
    except Exception:
        return "none"
