"""Camera parameter tree with caching, filtering, and search."""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any, Callable

VISIBILITY_TO_LEVEL = {
    "Beginner": 0,
    "Expert": 1,
    "Guru": 2,
    "Invisible": 3,
}


class CameraParameterTree:
    def __init__(
        self,
        tree_fetcher: Callable[[], dict],
        value_setter: Callable[[str, str], dict],
        serial_number: str = "",
    ):
        self._fetch_tree = tree_fetcher
        self._set_value = value_setter
        self._serial_number = serial_number
        self._raw_tree: dict | None = None
        self._flat_index: dict[str, dict] = {}
        self._level: str = "supplier"
        self._level_num: int = 1
        self._level_config: dict = {}
        self._is_stale: bool = False
        self._load_level_config()

    # -- public API --------------------------------------------------

    def load(self, force_refresh: bool = False) -> dict:
        if force_refresh:
            self.invalidate()

        online_tree = self._fetch_online()
        if online_tree is not None:
            self._raw_tree = online_tree
            self._is_stale = False
            self._build_flat_index()
            return self._raw_tree

        cached = self._load_cache()
        if cached is not None:
            self._raw_tree = cached
            self._is_stale = True
            self._build_flat_index()
            return self._raw_tree

        raise RuntimeError("Cannot load parameter tree: camera offline and no cache")

    def invalidate(self) -> None:
        self._raw_tree = None
        self._flat_index = {}

    def set_level(self, level: str) -> None:
        if level not in ("customer", "supplier", "vendor"):
            raise ValueError(f"Invalid level: {level}")
        self._level = level
        self._level_num = {"customer": 0, "supplier": 1, "vendor": 2}[level]

    def get_filtered_tree(self) -> dict:
        if self._raw_tree is None:
            raise RuntimeError("Tree not loaded. Call load() first.")
        tree = self._raw_tree.get("tree", {})
        return self._filter_node(tree, self._level_num)

    def search(self, keyword: str) -> list[dict]:
        keyword_lower = keyword.lower()
        results = []
        for _path, node in self._flat_index.items():
            display = (node.get("displayName") or "").lower()
            name = (node.get("path") or "").lower()
            if keyword_lower in display or keyword_lower in name:
                results.append({
                    "path": node.get("path", ""),
                    "displayName": node.get("displayName", ""),
                    "interfaceType": node.get("interfaceType", ""),
                    "currentValue": node.get("currentValue", ""),
                })
        return results

    def get_node(self, path: str) -> dict | None:
        return self._flat_index.get(path)

    def set_node_value(self, path: str, value: Any) -> dict:
        name = path.rsplit(".", 1)[-1]
        result = self._set_value(name, str(value))
        if result.get("success"):
            actual = result.get("actualValue", str(value))
            self._update_node_in_cache(path, actual)
        return result

    def set_node_values(self, changes: dict[str, Any]) -> list[dict]:
        failures = []
        for path, value in changes.items():
            r = self.set_node_value(path, value)
            if not r.get("success"):
                failures.append({
                    "path": path, "value": value,
                    "error": r.get("errorMessage", ""),
                })
        return failures

    def refresh_values(self) -> None:
        online_tree = self._fetch_online()
        if online_tree is None:
            return

        def merge_values(src: dict, dst: dict):
            if src.get("interfaceType") != "ICategory":
                dst["currentValue"] = src.get("currentValue", "")
            for name, child_src in src.get("children", {}).items():
                if name in dst.get("children", {}):
                    merge_values(child_src, dst["children"][name])

        if self._raw_tree and "tree" in self._raw_tree:
            merge_values(online_tree.get("tree", {}), self._raw_tree["tree"])
            self._is_stale = False
            self._build_flat_index()

    # -- private helpers ---------------------------------------------

    def _fetch_online(self) -> dict | None:
        try:
            result = self._fetch_tree()
            if isinstance(result, str):
                result = json.loads(result)
            if result and result.get("tree"):
                self._save_cache(result)
                return result
        except Exception:
            pass
        return None

    def _cache_path(self) -> str:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        cache_dir = os.path.join(appdata, "HRVision", "camera_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{self._serial_number}.json")

    def _load_cache(self) -> dict | None:
        path = self._cache_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "treeJson" in data:
                return data["treeJson"]
            return None
        except Exception:
            return None

    def _save_cache(self, raw_tree: dict) -> None:
        path = self._cache_path()
        cache_data = {
            "serialNumber": self._serial_number,
            "cameraModel": raw_tree.get("cameraModel", "Unknown"),
            "firmwareVersion": raw_tree.get("firmwareVersion", "Unknown"),
            "cachedAt": datetime.now().isoformat(),
            "completeness": raw_tree.get("completeness", "Full"),
            "treeJson": raw_tree,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_level_config(self) -> None:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_path = os.path.join(appdata, "HRVision", "camera_levels.json")
        try:
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self._level_config = json.load(f)
        except Exception:
            self._level_config = {}

    def _node_level_num(self, node: dict) -> int:
        if not node.get("isImplemented", True) or not node.get("isAvailable", True):
            return 999

        model = self._raw_tree.get("cameraModel", "") if self._raw_tree else ""
        model_config = self._level_config.get(model, self._level_config.get("*", {}))
        overrides = model_config.get("overrides", {})

        path = node.get("path", "")
        if path in overrides:
            level_name = overrides[path]
            return {"customer": 0, "supplier": 1, "vendor": 2}.get(level_name, 1)

        vis = node.get("visibility", "Expert")
        return VISIBILITY_TO_LEVEL.get(vis, 1)

    def _filter_node(self, node: dict, max_level: int) -> dict | None:
        node_level = self._node_level_num(node)
        is_category = node.get("interfaceType") == "ICategory"

        if not is_category:
            # 叶子：自身级别超过当前层级则剪掉
            if node_level > max_level:
                return None
            result = dict(node)
            result["stale"] = self._is_stale
            return result

        # 类目：先过滤子节点；自身级别超限时仅当过滤后为空才剪掉
        # （Root/类目节点的 visibility 不应阻止其可见子节点展示）
        filtered_children = {}
        for name, child in node.get("children", {}).items():
            filtered = self._filter_node(child, max_level)
            if filtered is not None:
                filtered_children[name] = filtered

        if node_level > max_level and not filtered_children:
            return None

        result = dict(node)
        result["children"] = filtered_children
        result["stale"] = self._is_stale
        return result

    def _build_flat_index(self) -> None:
        self._flat_index = {}

        def walk(node: dict):
            path = node.get("path", "")
            if path:
                self._flat_index[path] = node
            for child in node.get("children", {}).values():
                walk(child)

        if self._raw_tree and "tree" in self._raw_tree:
            walk(self._raw_tree["tree"])

    def _update_node_in_cache(self, path: str, value: str) -> None:
        node = self._flat_index.get(path)
        if node:
            node["currentValue"] = value
            node["stale"] = False

    @property
    def is_stale(self) -> bool:
        return self._is_stale
