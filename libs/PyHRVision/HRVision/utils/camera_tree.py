# -*- coding: utf-8 -*-
"""设备参数树统一规范化：所有相机（hr* 厂商库 / GenICam）导出的树 JSON
经过本模块整理成**一种格式**给 UI 显示。

输入可为两种语义（兼容历史）：
    A. 字段平铺节点：{"path":..., "interfaceType":..., "currentValue":...,
       "children": {...}}                       （HRCamera C++ / GenICam）
    B. 字段包在 "info" 键的节点：{"info": {...}, "children": {...}}

输出统一格式（UI `_walk_tree`/`_update_values` 已消费）：
    {
      "cameraModel": ..., "firmwareVersion": ..., "completeness": ...,
      "tree": {
        "name": "Root", "path": "Root", "displayName": "Root",
        "interfaceType": "ICategory", "visibility": "Expert",
        "accessMode": "NA",
        "children": {<name>: 规范节点}
      }
    }
规范节点字段：
    name/path/displayName/toolTip/description/visibility/isImplemented/isAvailable/
    interfaceType/accessMode/currentValue/defaultValue/min/max/inc/enumEntries

内部节点（寄存器地址/转换器/查询位 SwissKnife，非用户参数）默认过滤。
"""
import json

_VALID_TYPES = ("ICategory", "IInteger", "IFloat", "IBoolean", "IString",
                "IEnumeration", "ICommand", "IRegister", "INode")

# 内部节点名（寄存器/转换器/查询位/SwissKnife 域）——不展示
_INTERNAL_TOKENS = ("_RegAddr", "_Reg", "_Int", "_Inq", "_Bit", "_Addr",
                    "_Inq_Bit", "_InqCheck", "enumentry_", "_float",
                    "ctrlval", "converter", "convertfrom", "convertto",
                    "swissknife", "maxinq", "mininq", "checkinq")

# 命令节点名（GenICam 标准恒定名）：确保显示为命令按钮
_COMMAND_NAMES = {
    "AcquisitionStart", "AcquisitionStop", "AcquisitionAbort", "TriggerSoftware",
    "FrameTriggerSoftware", "UserSetLoad", "UserSetSave", "GevSCPSFireTestPacket",
    "GevSCPSFireTest", "ActionDevice", "FeatureReset", "LUTReset", "GevDeviceReset",
}


def _is_internal(name: str) -> bool:
    n = name.lower()
    return any(t in n for t in _INTERNAL_TOKENS)


def _norm_value(node: dict, key: str, default=None):
    v = node.get(key, default)
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return dict(v)
    return v


def _norm_node(node, default_name: str) -> dict:
    """单个节点规范化（含 children 递归）。"""
    info = node.get("info") if isinstance(node, dict) else None
    info = info if isinstance(info, dict) else node
    name = str(info.get("name") or default_name)

    out = {
        "name": name,
        "path": str(info.get("path") or ("" if name == "Root" else name)),
        "displayName": str(info.get("displayName") or name),
        "toolTip": str(info.get("toolTip") or ""),
        "description": str(info.get("description") or ""),
        "visibility": str(info.get("visibility") or "Expert"),
        "isImplemented": bool(info.get("isImplemented", True)),
        "isAvailable": bool(info.get("isAvailable", True)),
        "interfaceType": str(info.get("interfaceType") or "INode"),
        "accessMode": str(info.get("accessMode") or "NA"),
    }
    if out["interfaceType"] not in _VALID_TYPES:
        out["interfaceType"] = "INode"
    # 类型权威修正（源树类型可能被同名作用域节点污染）：
    # 带枚举项 → IEnumeration；有子层 → ICategory
    if out["interfaceType"] in ("INode", "ICategory"):
        if info.get("enumEntries"):
            out["interfaceType"] = "IEnumeration"
        elif str(info.get("accessMode") or "").upper() == "WO" \
                and not info.get("currentValue") \
                and not info.get("children"):
            out["interfaceType"] = "ICommand"
    if name in _COMMAND_NAMES:
        out["interfaceType"] = "ICommand"

    children = {}
    for cname, child in (info.get("children") or {}).items():
        if _is_internal(cname):
            continue                      # 内部节点不进 UI 树
        if cname == name:
            continue                      # 同名自挂残枝（parents 链错位）收缩
        ch = _norm_node(child, cname)
        children[cname] = ch
    if children:
        out["children"] = children
        # 有子层者必为类别：权威标记 + 剥掉污染的值/类型/访问字段
        # （类别行 UI 只显示名称与展开，不显示值/类型/int 等）
        out["interfaceType"] = "ICategory"
        out["accessMode"] = ""
        for k in ("currentValue", "defaultValue", "min", "max", "inc", "enumEntries"):
            out.pop(k, None)
    # 值域填充独立于 children（枚举可同时含 EnumEntry 展开子域）
    if out["interfaceType"] != "ICategory":
        out["currentValue"] = str(info.get("currentValue") or "")
        out["defaultValue"] = str(info.get("defaultValue") or out["currentValue"])
        for attr in ("min", "max", "inc"):
            v = info.get(attr)
            if v is not None:
                try:
                    out[attr] = float(v)
                except (TypeError, ValueError):
                    pass
        entries = info.get("enumEntries")
        if entries:
            out["enumEntries"] = [
                {"symbolic": str(e.get("symbolic", "")), "value": int(e.get("value", 0))}
                if isinstance(e, dict) else {"symbolic": str(e), "value": int(e)}
                for e in entries if isinstance(e, (dict, int, float, str))
            ]
    return out


def normalize_tree(tree_json) -> str:
    """任意厂商树 JSON → 统一规范格式（字符串，给 UI 直接消费）。"""
    try:
        if isinstance(tree_json, (list, dict)):
            data = dict(tree_json)
        else:
            data = json.loads(tree_json or "{}")
    except Exception:
        return json.dumps({"tree": {"name": "Root", "children": {}}})

    root = data.get("tree") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        root = data
    try:
        tree = _norm_node(root, "Root")
    except Exception:
        tree = {"name": "Root", "path": "Root", "interfaceType": "ICategory",
                "children": {}}
    return json.dumps({
        "cameraModel": str(data.get("cameraModel", "") or ""),
        "firmwareVersion": str(data.get("firmwareVersion", "") or ""),
        "completeness": str(data.get("completeness", "") or ""),
        "tree": tree,
    }, ensure_ascii=False)
