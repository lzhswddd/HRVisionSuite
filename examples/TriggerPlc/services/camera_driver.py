# -*- coding: utf-8 -*-
"""相机驱动：cv2.VideoCapture 封装（视频文件 / USB 相机）。

source 格式：
    "videos/xx.avi" → 视频文件（单相机演示，播完循环）
    "usb:N"         → USB 相机索引 N
"""
import cv2
import numpy as np


class CameraDriver:
    """视频源驱动，grab() 返回 BGR 帧。"""

    def __init__(self, source: str):
        self.source: str = source
        self._cap: cv2.VideoCapture | None = None
        self._open()

    def _open(self) -> None:
        if self.source.startswith("usb:"):
            idx: int = int(self.source.split(":", 1)[1])
            self._cap = cv2.VideoCapture(idx)
        else:
            self._cap = cv2.VideoCapture(self.source)
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError("相机打开失败: %s" % self.source)

    def grab(self) -> np.ndarray | None:
        """取一帧（视频文件播完自动循环回卷）；失败返回 None。"""
        assert self._cap is not None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)   # 播完回卷
            ok, frame = self._cap.read()
            if not ok or frame is None:
                return None
        return np.ascontiguousarray(frame)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
