# -*- coding: utf-8 -*-
"""通用 GenICam 相机类 GenICamCamera（GenTL + GenApi，标准协议，不绑厂商 SDK）。

底层：harvesters / genicam（GenICam 官方 Python 绑定：GenTL Producer + GenApi），
任意提供 GenTL producer（.cti，GigE Vision / USB3 Vision / 虚拟）的相机都能接入；
与 VideoCamera/LocalCamera 同级，注册进 CAMERA_TYPES 下拉（"GenICam"）。

                ┌─ 扫描（类方法枚举）: producer 发现 → 设备列表 → UI 下拉
                ├─ Open:   h.update() + create(0) → 设备访问句柄
    GenTL ──    ├─ Grab:   ia.start()（内部异步回调 + 缓冲队列）
                ├─ 取帧:   ia.fetch() → payload 组件 → HxWxN numpy（非阻塞队列）
                ├─ 参数:   GenApi NodeMap（SetValue 类型化 / GetValue symbolic）
                └─ 设备树: NodeMap 节点递归（枚举项 symbolic 文本 + 上下限）

注意：
    - 同一相机同一进程只允许一个访问（GenTL 互斥），重复 Open 会失败——符合
      「相机实例只能在相机进程内声明」的框架规范
    - 虚拟相机（MVS 侧无图像源时）读不到帧属虚拟源限制，真实 GigE/USB3 相机正常
    - 像素序：GenICam RGB8Packed = R,G,B 与框架 3 通道约定一致（不做 swap）
"""
import json
import os
import threading
import typing

import numpy

try:
    from .camera_base import CameraBase
except ImportError:  # 以脚本方式直接运行时
    from camera_base import CameraBase

# GenTL producer 使用模型：**不自动扫描目录**。用户显式提供 .cti 路径
# （初始参数 / 文件选择 / 扫描选定设备带回）——所有 API 的 producer 参数必填。
# 自带模拟相机在 HRVision/bin/hrSimuCamera.cti（无需安装任何 SDK 即可用）。
_BUNDLED_CTI = os.path.join(os.path.dirname(__file__), "bin", "hrSimuCamera.cti")

# 虚拟相机/测试环境：无真实图像源时可用此节点补帧（真机勿开）
_TEST_PATTERN_NODE = "TestPattern"
_TEST_PATTERN_VALUE = "ColorBar"


def _import_backend():
    """惰性导入 harvesters/genicam（未安装时给出明确提示）。"""
    try:
        import harvesters.core as _hc
    except ImportError:
        raise RuntimeError(
            "缺少 GenICam 运行时：pip install genicam harvesters"
            "（GenTL producer 请安装相机厂商 SDK，如海康 MVS）")
    return _hc


# GenTL producer 进程内只允许加载一次（CTI 被绑定持有）——按 .cti 缓存 Harvester，
# 扫描/打开共用同一实例；进程退出时自然释放（跨进程使用互不影响）。
_HC_CACHE: "dict[str, typing.Any]" = {}
_HC_LOCK = threading.Lock()


def _get_harvester(cti: str) -> typing.Any:
    """按 cti 获取（或创建）进程内共享 Harvester。"""
    hc = _import_backend()
    with _HC_LOCK:
        h = _HC_CACHE.get(cti)
        if h is None:
            h = hc.Harvester()
            h.add_file(cti)
            h.update()
            _HC_CACHE[cti] = h
        return h


def _reset_harvester(cti: str) -> None:
    """移除缓存并复位（换 producer/关闭时用）。"""
    with _HC_LOCK:
        h = _HC_CACHE.pop(cti, None)
    if h is not None:
        try:
            h.reset()
        except Exception:
            pass


def _find_ctis(producer: str = "") -> "list[str]":
    """解析 producer 配置：显式 .cti 路径（不自动扫描任何目录）。

    producer 给出的路径不存在时回退内置模拟相机提示；空 = 无（调用方应提示先给 cti）。
    """
    if not producer:
        return []
    if os.path.isfile(producer) and producer.lower().endswith(".cti"):
        return [producer]
    # 允许省略 .cti 后缀时补全
    if os.path.isfile(producer + ".cti"):
        return [producer + ".cti"]
    return []


class GenICamCamera(CameraBase):
    """通用 GenICam 相机（GenTL + GenApi）。

    构造：GenICamCamera(cameraType="GenICam", producer=..., key=..., test_pattern=...)
    """

    def __init__(self, cameraType: str = "GenICam", **kwargs) -> None:
        super().__init__(cameraType, **kwargs)
        self._producer = str(kwargs.get("producer", "") or "")
        self._key = str(kwargs.get("key", "") or "")
        self._test_pattern = str(kwargs.get("test_pattern", "") or "")
        self._hc = None           # harvesters.Harvester
        self._ia = None           # harvesters ImageAcquirer
        self._nm = None           # GenApi NodeMap
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # 扫描（类方法：任意 producer 组合下的设备列表）
    # ------------------------------------------------------------------

    @classmethod
    def enumerate_devices(cls, producer: str = "") -> "list[dict]":
        """枚举可用 GenTL 设备：dict {key/serial/model/vendor/user_defined_name/ip/producer}。

        注意：跳过采集卡类 producer（MvFGProducer*，无采集卡时枚举会阻塞卡死），
        只扫描标准设备类（GigE/U3V/虚拟/模拟器）。
        """
        out = []
        seen = set()                            # 按 key 去重（同设备在多个 producer 目录有副本）
        for cti in _find_ctis(producer):
            if "fgproducer" in os.path.basename(cti).lower():
                continue                        # 采集卡 producer：跳过（扫描卡死源）
            try:
                h = _get_harvester(cti)         # 进程内共享（GenTL cti 只加载一次）
                for d in h.device_info_list:
                    key = str(d.serial_number or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "key": key,
                        "serial": key,
                        "model": str(d.model or ""),
                        "vendor": str(d.vendor or ""),
                        "user_defined_name": str(d.user_defined_name or ""),
                        "ip": "",
                        "interface": "",        # GenICam 无第二连接键（兼容字段）
                        "producer": cti,        # ← 本类特有：设备所属 GenTL producer
                    })
            except Exception:
                pass
        return out

    # ------------------------------------------------------------------
    # 开关相机
    # ------------------------------------------------------------------

    def Open(self) -> "tuple[bool, str]":
        """打开设备访问（GenTL 句柄 + GenApi NodeMap）。"""
        hc = _import_backend()
        with self._lock:
            if self._ia is not None:
                return True, "already opened"
            ctls = _find_ctis(self._producer)
            if not ctls:
                return False, ("未提供 GenTL producer（.cti）：请填写 .cti 路径"
                               "（如 HRVision/bin/hrSimuCamera.cti 或 MVS Runtime 的"
                               " MvProducerVIR.cti），或用「选择 .cti」按钮选择")
            errors = []
            self._hc = None
            for cti in ctls:
                try:
                    h = _get_harvester(cti)
                    if not h.device_info_list:
                        raise RuntimeError("no device")
                except Exception as e:
                    errors.append(str(e))
                    continue
                self._hc = h
                break
            if self._hc is None:
                return False, "GenTL 未发现相机（%s）" % ("; ".join(errors) or "无设备")
            if self._key:
                idx = None
                for i, d in enumerate(self._hc.device_info_list):
                    if str(d.serial_number or "") == self._key:
                        idx = i
                        break
                if idx is None:
                    return False, "未找到相机 %s" % self._key
            else:
                idx = 0
            try:
                self._ia = self._hc.create(idx)
            except Exception as e:
                note = ("（-1005 独占冲突：请关闭 MVS 客户端等占用者后重试）"
                        if "(-1005)" in str(e) or "-1005" in str(e) else "")
                return False, "打开相机失败%s: %s" % (note, e)
            self._nm = self._ia.remote_device.node_map
            if self._test_pattern and self._nm.has_node(_TEST_PATTERN_NODE):
                try:
                    self._nm.get_node(_TEST_PATTERN_NODE).value = self._test_pattern
                except Exception:
                    pass
            hint = ("；虚拟相机出图需 MVS 客户端重置相机" if self._is_virtual() else "")
            return True, "GenICam 相机已打开%s" % hint

    def Close(self) -> "tuple[bool, str]":
        with self._lock:
            if self._ia is not None:
                try:
                    self._ia.destroy()
                except Exception:
                    pass
                self._ia = None
            # 共享 producer 不 reset（进程内缓存复用；不做 _HC_CACHE 清理）
            self._nm = None
            return True, "Camera closed successfully."

    def IsOpened(self) -> "tuple[bool, str]":
        return self._ia is not None, "camera is opened"

    # ------------------------------------------------------------------
    # 虚拟相机（MVS 虚拟源）识别与提示
    # ------------------------------------------------------------------

    def _is_virtual(self) -> bool:
        """海康 MVS 虚拟相机：producer 为 MvProducerVIR 时是私有图像源——
        连过/被连后需在海康 MVS 客户端「重置相机」或「运行图像源」才有帧。"""
        p = self._producer.lower()
        return "mvproducervir" in p or "virtual" in p or "vir_" in p

    @staticmethod
    def _virtual_hint() -> str:
        return ("（海康虚拟相机：帧由 MVS 客户端私有图像源提供——请在 MVS 客户端"
                "「运行图像源」，被连过后先「重置相机」；真实 GigE/USB3 相机无此限制）")

    # ------------------------------------------------------------------
    # 推流/取帧
    # ------------------------------------------------------------------

    def Grab(self) -> "tuple[bool, str]":
        with self._lock:
            if self._ia is None:
                return False, "camera is not opened"
            try:
                self._ia.start()
            except Exception as e:
                return False, str(e)
            return True, "grabbing started"

    def Stop(self) -> "tuple[bool, str]":
        with self._lock:
            if self._ia is None:
                return False, "camera is not opened"
            try:
                self._ia.stop()
            except Exception:
                pass
            return True, "grabbing stopped"

    def IsGrabbing(self) -> "tuple[bool, str]":
        with self._lock:
            if self._ia is None:
                return False, "camera is not opened"
            try:
                return (bool(self._ia.is_started), "grabbing")
            except Exception:
                return False, "not grabbing"

    def GetCameraBuffer(self, timeOut: int = 1000) -> "tuple[bool, list[numpy.ndarray], str]":
        """读取下一帧（HxWxN numpy，RGB8/BGR8 等按 GenICam PixelFormat 原序）。

        数据源 = 事件缓冲 raw_buffer + node map 宽高/通道（组件层 width 推导
        依赖部分厂商信息项，部分 GenTL 生产者给不全——raw_buffer 是保真通道）。
        """
        with self._lock:
            if self._ia is None:
                return False, [], "Camera is not Grabbing."
        try:
            w, h, nc = 0, 0, 1
            nm = self._nm
            if nm is not None:
                try:
                    w = int(nm.get_node("Width").value)
                    h = int(nm.get_node("Height").value)
                except Exception:
                    pass
                try:
                    pf = str(nm.get_node("PixelFormat").value)
                    nc = 3 if pf.lower().startswith(("rgb", "bgr")) else 1
                except Exception:
                    nc = 1
            with self._ia.fetch(timeout=int(timeOut)) as buffer:
                raw = buffer.raw_buffer          # 事件缓冲原始字节（bytes）
                size = getattr(buffer, "data_size", None) or len(raw)
                flat = numpy.frombuffer(raw, dtype=numpy.uint8, count=int(size)).copy()
                if w and h:
                    img = flat.reshape((h, w, nc))
                else:
                    img = flat
        except Exception as e:
            err = str(e)
            if self._is_virtual():
                err += self._virtual_hint()
            return False, [], err
        return True, [img], "Frame read successfully."

    def SetReciveBufferCallback(self, callback, context: typing.Any = None) -> None:
        """拉取式语义，无需回调（保留接口）。"""
        pass

    # ------------------------------------------------------------------
    # 参数（GenApi NodeMap，任意 GenICam 特征）
    # ------------------------------------------------------------------

    def _node(self, key: str):
        if self._nm is None or not self._nm.has_node(key):
            return None
        return self._nm.get_node(key)

    def SetValue(self, key: str, value: typing.Any) -> "tuple[bool, str]":
        """写参数（布尔/数值/字符串 symbolic 均可；布尔兼容 "true"/"1" 字符串）。"""
        node = self._node(key)
        if node is None:
            return False, "unknown parameter: %s" % key
        try:
            # 真值字符串 → bool（UI 下拉同款）；数值字符串交 GenApi 类型化转换
            if isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
                node.value = value.lower() in ("true", "1", "yes")
            else:
                node.value = value
            return True, "ok"
        except Exception as e:
            return False, str(e)

    def GetValue(self, key: str) -> "tuple[typing.Any, str]":
        """读参数：枚举返回 symbolic 文本，其余按 GenApi 原始类型。"""
        node = self._node(key)
        if node is None:
            return None, "unknown parameter: %s" % key
        try:
            return node.value, "ok"
        except Exception as e:
            return None, str(e)

    def SetExposureTime(self, timeMs) -> "tuple[bool, str]":
        return self.SetValue("ExposureTime", float(timeMs))

    def GetExposureTime(self) -> "tuple[typing.Any, str]":
        return self.GetValue("ExposureTime")

    def SetGain(self, gain) -> "tuple[bool, str]":
        return self.SetValue("Gain", float(gain))

    def GetGain(self) -> "tuple[typing.Any, str]":
        return self.GetValue("Gain")

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------

    def GetConfig(self) -> dict:
        return {
            "camera_type": self.camera_type,
            "producer": self._producer,
            "key": self._key,
            "test_pattern": self._test_pattern,
        }

    def SetConfig(self, config: dict) -> None:
        if "camera_type" in config:
            self.camera_type = config["camera_type"]
        if "producer" in config:
            self._producer = str(config["producer"] or "")
        if "key" in config:
            self._key = str(config["key"] or "")
        if "test_pattern" in config:
            self._test_pattern = str(config["test_pattern"] or "")

    # ------------------------------------------------------------------
    # 参数树（与 HRCamera.GetParameterTree 同构 JSON）
    # ------------------------------------------------------------------

    def GetParameterTree(self) -> "tuple[str, str]":
        node_map = self._nm
        if node_map is None:
            return "{}", "camera is not opened"
        model = ""
        try:
            model = str(getattr(self._ia.remote_device, "model", "") or "")
        except Exception:
            pass

        def iface_type(e) -> str:
            # 真接口类型 = SWIG proxy 类名（ICategory/IInteger/IFloat/IBoolean/
            # IString/IEnumeration/ICommand/IRegister）；node 上无 interface_type 属性
            t = type(e).__name__
            if t in ("ICategory", "IInteger", "IFloat", "IBoolean", "IString",
                     "IEnumeration", "ICommand", "IRegister"):
                return t
            try:
                inner = getattr(e.node, "principal_interface_type", "") or ""
                if isinstance(inner, str) and inner:
                    return inner
                return str(getattr(inner, "value", "") or "")
            except Exception:
                return "INode"

        def access_mode(node) -> str:
            try:
                am = node.get_access_mode()
                return str(getattr(am, "value", am) or am)
            except Exception:
                return "RW"

        # 全量路径法：CNodeMap.nodes 为全部节点的扁平列表（海康 XML 2995 个）；
        # 路径经 node.parents 链上溯（category.features 引用链对子层不全）——
        # 每个节点挂到其父类别下，构成完整参数树。
        def _path_of(e) -> "str | None":
            names = []
            cur = e
            for _ in range(60):
                try:
                    p = cur.node.parents
                except Exception:
                    return None
                if not isinstance(p, (tuple, list)) or not p:
                    return None
                cur = p[0]
                try:
                    nm_ = str(cur.node.name)
                except Exception:
                    return None
                if nm_ == "Root":
                    break
                names.append(nm_)
            return "Root." + ".".join(reversed(names)) if names else None

        try:
            nodes = list(node_map.nodes)
            entry = {}
            for e in nodes:
                try:
                    full = _path_of(e)
                except Exception:
                    continue
                if not full:
                    continue
                # 内部瑞士军刀节点（寄存器地址/转换器/查询位）不展示：
                # 丢弃后层级清晰且不会覆盖真参数（真 Width=640 vs Width_RegAddr=0x30360）
                nm2 = str(e.node.name)
                if any(t in nm2 for t in ("_RegAddr", "_Reg", "_Int", "_Inq",
                                          "_Bit", "_Addr", "_Inq_Bit")):
                    continue
                # first-wins：同路径同名（命名空间副本）保留首位真体
                entry.setdefault(full + "." + nm2, e)
            # 判定叶子：没有任何 full 名以该名+"." 为前缀 → 叶子；否则为类别
            def is_category(full: str) -> bool:
                prefix = full + "."
                return any(f.startswith(prefix) for f in entry)

            tree_children = {}
            for key, e in sorted(entry.items()):
                parent_full = key.rsplit(".", 1)[0]                 # 父路径（键含叶名）
                parts = (parent_full.split(".")[1:] + [str(e.node.name)])
                name = parts[-1]
                # 挂入路径链
                cur = tree_children
                for i, part in enumerate(parts):
                    is_leaf = i == len(parts) - 1
                    if part not in cur:
                        cur[part] = {
                            "path": "Root." + ".".join(parts[: i + 1]),
                            "displayName": part,
                            "toolTip": "",
                            "visibility": "Expert",
                            "isImplemented": True,
                            "isAvailable": True,
                            "interfaceType": "ICategory" if not is_leaf else "INode",
                            "accessMode": "NA",
                            "currentValue": "",
                        }
                    node_dict = cur[part]
                    if True:                       # 无条件填值：同名作用域节点信息合并
                        try:
                            n = e.node
                            node_dict["displayName"] = str(getattr(n, "display_name", "") or name)
                            node_dict["toolTip"] = str(getattr(n, "description", "") or "")
                            ctype = iface_type(e)
                            node_dict["interfaceType"] = ctype or "INode"
                            node_dict["accessMode"] = access_mode(n)
                            # 填值：同名节点既挂子作用域又有自身值（如 Width）；
                            # 已有值不覆盖（命名空间副本防污染），枚举转 symbolic
                            if ctype != "ICategory":
                                try:
                                    cv = e.value
                                    if isinstance(cv, bool):
                                        cv = "true" if cv else "false"
                                    if hasattr(e, "entries") and not isinstance(cv, str):
                                        try:
                                            items = list(e.entries)
                                            sym = next((se.symbolic for se in items
                                                        if int(se.value) == int(cv)
                                                        or str(se.value) == str(cv)), None)
                                            if sym:
                                                cv = sym
                                        except Exception:
                                            pass
                                    if node_dict.get("currentValue") in (None, ""):
                                        node_dict["currentValue"] = str(cv)
                                except Exception:
                                    pass
                                node_dict["defaultValue"] = node_dict.get("currentValue", "")
                                for attr in ("min", "max", "inc"):
                                    try:
                                        v = getattr(e, attr, None)
                                        if v is not None:
                                            node_dict[attr] = float(v)
                                    except Exception:
                                        pass
                                if hasattr(e, "entries"):
                                    try:
                                        node_dict["enumEntries"] = [
                                            {"symbolic": str(se.symbolic),
                                             "value": int(se.value)} for se in e.entries
                                        ]
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    else:
                        node_dict.setdefault("children", {})
                    cur = node_dict.setdefault("children", {})
            tree_children = tree_children
        except Exception as e:
            return "{}", "tree walk failed: %s" % e
        result = {"cameraModel": model, "firmwareVersion": "",
                  "completeness": "Full",
                  "tree": {"path": "Root", "displayName": "Root",
                           "visibility": "Expert", "interfaceType": "ICategory",
                           "accessMode": "NA", "children": tree_children}}
        return json.dumps(result, ensure_ascii=False), ""


def _manual_test():
    """直接运行（python genicam_camera.py 或 -m）：扫描 + 打开 + 树 + 写读参数。"""
    devs = GenICamCamera.enumerate_devices()
    print("扫描到 %d 台设备" % len(devs))
    for d in devs:
        print("  ", d)
    if not devs:
        return
    cam = GenICamCamera(producer=devs[0].get("producer", ""), key=devs[0]["key"])
    ok, msg = cam.Open()
    print("Open:", ok, msg)
    if not ok:
        return
    tree, err = cam.GetParameterTree()
    print("tree bytes:", len(tree))
    for k in ("Width", "ExposureTime", "Gain", "PixelFormat", "TriggerMode"):
        v, m = cam.GetValue(k)
        print("  GetValue %-16s = %r (%s)" % (k, v, m))
    print("SetValue TriggerMode=Off ->", cam.SetValue("TriggerMode", "Off"))
    v, _ = cam.GetValue("TriggerMode")
    print("  TriggerMode now:", v)
    cam.Grab()
    ok0, frames, msg0 = cam.GetCameraBuffer(2000)
    print("grab:", ok0, msg0, [f.shape for f in frames])
    cam.Stop()
    cam.Close()


if __name__ == "__main__":
    _manual_test()
