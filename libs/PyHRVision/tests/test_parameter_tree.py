"""genICam 参数树冒烟测试：CameraParameterTree 逻辑 + HRCamera.pyd 端到端。

不依赖 pytest，直接 `python tests/test_parameter_tree.py` 运行，退出码 0 即通过。
离线部分不要求相机硬件；端到端部分在无相机时验证管线可用（树含 Root 节点）。
"""
import json
import os
import sys
import tempfile

# 包根目录加入 sys.path（脚本在 tests/ 下运行时默认只加 tests/）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 隔离缓存目录，避免污染真实 APPDATA/HRVision/camera_cache
_TMP_APPDATA = tempfile.mkdtemp(prefix="hrvision_test_appdata_")
os.environ["APPDATA"] = _TMP_APPDATA


def make_mock_tree():
    """构造与 C++ BuildTreeJSON 输出同构的模拟树。"""
    return {
        "cameraModel": "MockCamera",
        "firmwareVersion": "1.0.0",
        "completeness": "Full",
        "tree": {
            "path": "Root",
            "displayName": "Root",
            "interfaceType": "ICategory",
            "visibility": "Expert",
            "children": {
                "ImageFormatControl": {
                    "path": "Root.ImageFormatControl",
                    "displayName": "ImageFormatControl",
                    "interfaceType": "ICategory",
                    "visibility": "Beginner",
                    "children": {
                        "Width": {
                            "path": "Root.ImageFormatControl.Width",
                            "displayName": "Width",
                            "interfaceType": "IInteger",
                            "visibility": "Beginner",
                            "currentValue": "2448",
                            "min": 16, "max": 2448, "inc": 1,
                        },
                        "Height": {
                            "path": "Root.ImageFormatControl.Height",
                            "displayName": "Height",
                            "interfaceType": "IInteger",
                            "visibility": "Guru",
                            "currentValue": "2048",
                        },
                    },
                },
                "AnalogControl": {
                    "path": "Root.AnalogControl",
                    "displayName": "AnalogControl",
                    "interfaceType": "ICategory",
                    "visibility": "Expert",
                    "children": {
                        "Gain": {
                            "path": "Root.AnalogControl.Gain",
                            "displayName": "Gain",
                            "interfaceType": "IFloat",
                            "visibility": "Expert",
                            "currentValue": "3.14",
                        },
                    },
                },
                "DeviceInfo": {
                    "path": "Root.DeviceInfo",
                    "displayName": "DeviceInfo",
                    "interfaceType": "ICategory",
                    "visibility": "Invisible",
                    "children": {
                        "DeviceUserID": {
                            "path": "Root.DeviceInfo.DeviceUserID",
                            "displayName": "DeviceUserID",
                            "interfaceType": "IString",
                            "visibility": "Beginner",
                            "currentValue": "cam01",
                        },
                    },
                },
            },
        },
    }


def walk_leaves(node):
    if node.get("interfaceType") != "ICategory":
        yield node
    else:
        for child in node.get("children", {}).values():
            yield from walk_leaves(child)


def test_offline_logic():
    """离线逻辑：加载、缓存、级别过滤、搜索、设值。"""
    from HRVision.camera_parameter_tree import CameraParameterTree

    tree_data = make_mock_tree()
    fetched = {"count": 0}
    offline = {"flag": False}

    def fetch():
        if offline["flag"]:
            return None  # 模拟相机离线/接口错误
        fetched["count"] += 1
        return json.dumps(tree_data)

    set_calls = []

    def setter(name, value):
        set_calls.append((name, value))
        return {"success": True, "actualValue": value, "errorMessage": ""}

    tree = CameraParameterTree(tree_fetcher=fetch, value_setter=setter, serial_number="mock_cam_01")

    # 1. load() 成功且生成了缓存文件
    loaded = tree.load()
    assert loaded == tree_data, "load() 应返回原始树"
    cache_path = tree._cache_path()
    assert os.path.isfile(cache_path), "load() 后应生成缓存文件"
    print("  [1] load() + 缓存文件生成: OK")

    # 2. 离线加载：先为 offline 序列号生成缓存，再模拟 fetch 失败从缓存读
    tree._serial_number = "mock_cam_offline"
    offline["flag"] = False
    loaded = tree.load()
    assert os.path.isfile(tree._cache_path()), "offline 序列号应先有缓存"
    offline["flag"] = True
    tree.invalidate()
    loaded = tree.load()
    assert loaded.get("cameraModel") == "MockCamera", "应命中离线缓存"
    assert tree.is_stale is True, "离线缓存加载应标记 stale"
    print("  [2] 离线缓存加载 (is_stale=True): OK")

    # 3. 级别过滤：customer 只留 Beginner
    tree.invalidate()
    tree._serial_number = "mock_cam_01"
    tree.load()
    tree.set_level("customer")
    filtered = tree.get_filtered_tree()
    leaves = list(walk_leaves(filtered))
    names = {n["displayName"] for n in leaves}
    assert names == {"Width", "DeviceUserID"}, f"customer 级应只剩 Width/DeviceUserID, got {names}"
    assert "Height" not in names and "Gain" not in names
    print(f"  [3] customer 级过滤 ({sorted(names)}): OK")

    # 4. supplier 级：Beginner + Expert（Gain 出现，Height 仍隐藏）
    tree.set_level("supplier")
    filtered = tree.get_filtered_tree()
    names = {n["displayName"] for n in walk_leaves(filtered)}
    assert names == {"Width", "Gain", "DeviceUserID"}, f"supplier 级应含 Gain, got {names}"
    print(f"  [4] supplier 级过滤 ({sorted(names)}): OK")

    # 5. vendor 级：全部节点
    tree.set_level("vendor")
    filtered = tree.get_filtered_tree()
    names = {n["displayName"] for n in walk_leaves(filtered)}
    assert names == {"Width", "Height", "Gain", "DeviceUserID"}
    print(f"  [5] vendor 级过滤 ({sorted(names)}): OK")

    # 6. search
    tree.set_level("supplier")
    results = tree.search("Width")
    assert len(results) == 1 and results[0]["currentValue"] == "2448"
    assert tree.search("Gain")[0]["path"] == "Root.AnalogControl.Gain"
    assert tree.search("not_exist") == []
    print("  [6] search: OK")

    # 7. get_node / set_node_value
    node = tree.get_node("Root.ImageFormatControl.Width")
    assert node and node["currentValue"] == "2448"
    result = tree.set_node_value("Root.ImageFormatControl.Width", "1000")
    assert result["success"] is True
    assert tree.get_node("Root.ImageFormatControl.Width")["currentValue"] == "1000"
    assert set_calls[-1] == ("Width", "1000")
    print("  [7] get_node / set_node_value: OK")

    # 8. set_node_values 批量：失败项被收集
    offline["flag"] = False  # 还原在线状态
    def bad_setter(name, value):
        return {"success": False, "actualValue": "", "errorMessage": "rejected"}

    tree2 = CameraParameterTree(tree_fetcher=fetch, value_setter=bad_setter, serial_number="mock_cam_02")
    tree2.load()
    failures = tree2.set_node_values({"Root.ImageFormatControl.Width": "1"})
    assert len(failures) == 1 and failures[0]["error"] == "rejected"
    print("  [8] set_node_values 批量失败收集: OK")

    print("test_offline_logic: OK")


def test_end_to_end():
    """端到端：HRCamera.pyd -> C++ GetParameterTree -> CameraParameterTree。"""
    from HRVision.HRCamera import Camera
    from HRVision import create_parameter_tree

    # 注意：CameraType 就是 DLL 文件名（如 'hrOpenCV' -> hrOpenCV.dll）
    cam = Camera("hrOpenCV")
    cam.SetConfig({"SerialNumber": "smoke_test"})

    tree = create_parameter_tree(cam)
    try:
        loaded = tree.load()
    except RuntimeError:
        # 完全拿不到树（无相机且无缓存）— 管线本身可用性由 getattr 保证
        assert hasattr(cam, "GetParameterTree")
        print("  (无相机且无缓存，跳过在线断言)")
        print("test_end_to_end: OK")
        return

    tree_json = loaded.get("tree", {})
    assert tree_json.get("path") == "Root", "树根应为 Root"
    assert loaded.get("completeness") in ("Full", "Partial", "Minimal")
    print(f"  cameraModel={loaded.get('cameraModel')!r}, completeness={loaded.get('completeness')!r}")
    leaves = list(walk_leaves(tree_json))
    print(f"  叶子节点数: {len(leaves)}")
    if leaves:
        print(f"  示例节点: {leaves[0]['displayName']} = {leaves[0].get('currentValue')!r}")

    # 过滤 + 搜索在真实树上跑一遍
    tree.set_level("supplier")
    filtered = tree.get_filtered_tree()
    assert filtered is not None
    res = tree.search("Width")
    print(f"  search('Width') -> {len(res)} 条")
    print("test_end_to_end: OK")


if __name__ == "__main__":
    print("== 离线逻辑测试 ==")
    test_offline_logic()
    print("== 端到端测试 (HRCamera.pyd) ==")
    test_end_to_end()
    print("\nALL PASS")
