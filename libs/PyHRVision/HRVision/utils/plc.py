# -*- coding: utf-8 -*-
"""PLC 统一接口（框架通用组件）：HslCommunication(C# 托管) 直连 + 回退双后端。

对统一接口（地址型，业务位名映射在调用侧/项目层）：
    Plc("Modbus", host, port) → 后端探测：pythonnet+CLR(HslCommunication) 优先，
    无 pythonnet → 回退 C++/CLI pyd(PLCInterface,惰性加载)；两者皆无 → 构造抛错。

常用操作:
    connect()/is_connected()/close()
    read_coil(addr)/write_coil(addr, on)      # FC01/FC05, 字符串或整型地址("0")
    read_register(addr)/write_register(addr, val)
    兼容别名 read_bit/write_bit = coil 语义

托管库落位（关键坑,已实测）:HslCommunication.dll 由 pythonnet 托管解析,
解析基准 = 进程基目录(sys.prefix)——ensure_managed_dll() 自动从
HRVision/bin(与相机 DLL 同库惯例)补放到基准,无环境根依赖(直连路线)。

中链事实(pythonnet):纯 C# 库 add_reference 后无 pyd/C++/CLI、无环境根 DLL 依赖;
本项目专案的 IO 位名映射/镜像路由/mock 语义留在项目 services/plc.py。

注意:Python 3.9 兼容(字符串注解);cp39 环境无 pythonnet 时回退接口仍可用。
"""
import os
import shutil
import sys

_LEGACY_DIRS = (r"D:/Python/cModule/PLCInterface/build/bin/Release",)

try:
    import HRVision as _pkg
    _PKG_DIR = os.path.dirname(os.path.abspath(_pkg.__file__))
except Exception:
    _PKG_DIR = os.path.dirname(os.path.abspath(__file__))


def hrvision_bin_dir() -> str:
    """框架内置 PLC 环境目录(HRVision/bin,与相机 DLL 同库惯例)。"""
    d = os.path.join(_PKG_DIR, "bin")
    return d if os.path.isdir(d) else ""


def hrvision_has_plc_lib() -> bool:
    """框架 bin 内是否含 PLCInterface.pyd(回退库)。"""
    return bool(hrvision_bin_dir()) and os.path.isfile(
        os.path.join(hrvision_bin_dir(), "PLCInterface.pyd"))


def ensure_managed_dll() -> str:
    """HslCommunication.dll(C# 托管库)自动补放到 CLR 解析基准(python.exe 所在目录)。

    实测:托管库解析基准 = 进程基目录(环境根), bin/sys.path 注册都不覆盖——
    旧经验「放 HRVision 环境目录才可用」由此而来。本函数在基准缺失时从源
    (HRVision/bin → PLC_LIB_DIR 环境变量 → 旧编译目录)复制一份。
    """
    src = ""
    for d in (hrvision_bin_dir(), os.environ.get("PLC_LIB_DIR", "")) + _LEGACY_DIRS:
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
            print("[plc] HslCommunication.dll 已补放到环境根(CLR 解析基准)", flush=True)
        except Exception:
            pass
    return dst


def _search_plc_dirs() -> list:
    out = []
    for d in (hrvision_bin_dir(), os.environ.get("PLC_LIB_DIR", "")) + _LEGACY_DIRS:
        if d and d not in out and os.path.isdir(d):
            out.append(d)
    return out


class ClrPlc:
    """直连 C# 后端(pythonnet + HslCommunication.dll——绕过 pyd/C++/CLI 中间件)。

    实测全链路:clr.AddReference → ModbusTcpNet(host,port) → ConnectServer →
    ReadBool/Write(string,bool) 回环一致;托管解析由 pythonnet 钩子承载,
    无环境根 DLL 约束(ensure_managed_dll 仅为双保险)。
    """

    _loaded = False

    @classmethod
    def _ensure(cls) -> None:
        if cls._loaded:
            return
        import clr
        for _d in _search_plc_dirs():
            ensure_managed_dll()
            try:
                for part in ("HslCommunication.dll", "PLCDevice.dll"):
                    p = os.path.join(_d, part)
                    if os.path.isfile(p):
                        clr.AddReference(p)
                cls._loaded = True
                return
            except Exception:
                continue
        # 基准目录直加(纯托管库,无附带依赖)
        for _d in (_search_plc_dirs() or ["."]):
            try:
                clr.AddReference(_d)
                cls._loaded = True
                return
            except Exception:
                continue
        raise ImportError("HslCommunication.dll 未找到(请置于 HRVision/bin 或 PLC_LIB_DIR)")

    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self._ensure()
        import HslCommunication.ModBus as _mb
        self._net = _mb.ModbusTcpNet(host, port)
        self._conn = False

    def connect(self) -> bool:
        try:
            self._conn = bool(self._net.ConnectServer().IsSuccess)
        except Exception:
            self._conn = False
        return self._conn

    def is_connected(self) -> bool:
        return self._conn

    def read_coil(self, addr) -> bool:
        try:
            r = self._net.ReadBool(str(addr))
            return bool(r.IsSuccess and r.Content)
        except Exception:
            return False

    def write_coil(self, addr, on: bool) -> bool:
        try:
            return bool(self._net.Write(str(addr), bool(on)).IsSuccess)
        except Exception:
            return False

    def read_register(self, addr, count: int = 1):
        """保持寄存器读(3 区;按 HslCommunication 地址语义,可读/写区)。"""
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

    # 兼容别名(coil 语义)
    read_bit = read_coil
    write_bit = write_coil

    def close(self):
        try:
            self._net.ConnectClose()
        except Exception:
            pass


class PydPlc:
    """回退后端:C++/CLI pyd(PLCInterface)——历史环境/无 pythonnet 时使用(惰性加载)。"""

    def __init__(self, plc_type: str = "Modbus", host: str = "127.0.0.1",
                 port: int = 9000, name: str = "hrvision"):
        import PLCInterface
        self._plc = PLCInterface.PLC()
        ensure_managed_dll()
        self._plc.createTcp(name, plc_type, host, port)

    def connect(self) -> bool:
        try:
            return bool(self._plc.openConnection())
        except Exception:
            return False

    def is_connected(self) -> bool:
        try:
            return bool(self._plc.isConnected())
        except Exception:
            return False

    def read_coil(self, addr) -> bool:
        try:
            v = self._plc.readNumber(str(addr), "bool")
            return str(v).strip().lower() in ("1", "true")
        except Exception:
            return False

    def write_coil(self, addr, on: bool) -> bool:
        try:
            self._plc.writeNumber(str(addr), "1" if on else "0", "bool")
            return True
        except Exception:
            return False

    read_bit = read_coil
    write_bit = write_coil

    def read_register(self, addr, count: int = 1):
        try:
            return [self._plc.readNumber(str(int(addr) + i), "int16")
                    for i in range(count)]
        except Exception:
            return None

    def write_register(self, addr, value) -> bool:
        try:
            self._plc.writeNumber(str(addr), str(int(value)), "int16")
            return True
        except Exception:
            return False

    def close(self):
        try:
            self._plc.close()
        except Exception:
            pass


def backend_status() -> str:
    """当前环境后端探测(无副作用):'clr'(直连 C#)/'pyd'(回退)/'none'。"""
    try:
        ClrPlc._ensure()
        return "clr"
    except Exception:
        pass
    try:
        import PLCInterface
        return "pyd"
    except Exception:
        return "none"


class Plc:
    """PLC 客户端统一门:构造时探测后端——CLR(直连 C#,推荐)优先,pyd 回退。

    统一接口(地址型):
        conn = Plc("Modbus", "127.0.0.1", 9000)
        conn.connect() / conn.read_coil("0") / conn.write_coil("0", True) /
        conn.read_register("0") / conn.write_register("0", 1) / conn.close()
    业务位名映射(I/O 表)在项目层(services/plc.py)包一层,此处不感知。
    """

    def __init__(self, plc_type: str = "Modbus", host: str = "127.0.0.1",
                 port: int = 9000, name: str = "hrvision"):
        ensure_managed_dll()
        try:
            self._impl = ClrPlc(host, port)
            self._backend = "clr"
        except Exception as e:
            try:
                self._impl = PydPlc(plc_type, host, port, name)
                self._backend = "pyd"
            except Exception as e2:
                raise RuntimeError(
                    "PLC 后端不可用: CLR(%s) / pyd(%s) —— 请安装 pythonnet+"
                    "HslCommunication 或 PLCInterface.pyd" % (e, e2)) from e2

    @property
    def backend(self) -> str:
        """实际后端: 'clr' / 'pyd'。"""
        return self._backend

    def connect(self) -> bool:
        return self._impl.connect()

    def is_connected(self) -> bool:
        return self._impl.is_connected()

    def read_coil(self, addr) -> bool:
        return self._impl.read_coil(addr)

    def write_coil(self, addr, on: bool) -> bool:
        return self._impl.write_coil(addr, on)

    read_bit = read_coil     # 兼容别名
    write_bit = write_coil

    def read_register(self, addr, count: int = 1):
        return self._impl.read_register(addr, count)

    def write_register(self, addr, value) -> bool:
        return self._impl.write_register(addr, value)

    def close(self):
        self._impl.close()
