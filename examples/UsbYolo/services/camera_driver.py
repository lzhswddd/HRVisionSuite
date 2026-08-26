# -*- coding: utf-8 -*-
"""USB 相机驱动：cv2.VideoCapture 封装。

source 格式：
    "usb:N"        → 打开索引 N 的 USB 相机（VideoCapture(N)）
    "videos/xx.avi" → 按视频文件打开（无 USB 相机时调试用）
"""
import cv2
import numpy as np


class UsbCamera:
    """视频源驱动（USB 相机 / 视频文件），grab() 返回 BGR 帧。"""

    def __init__(self, source: str, width: int = 0, height: int = 0):
        self.source: str = source
        self.width: int = width
        self.height: int = height
        self._cap: cv2.VideoCapture | None = None
        self._open()

    def _open(self) -> None:
        """打开视频源；失败抛异常（节点代码回抓帧重试前会先初始化成功）。"""
        if self.source.startswith("usb:"):
            idx: int = int(self.source.split(":", 1)[1])
            self._cap = cv2.VideoCapture(idx)
            if self.width > 0:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            if self.height > 0:
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        else:
            self._cap = cv2.VideoCapture(self.source)   # 视频文件（调试）
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError("相机打开失败: %s" % self.source)

    def grab(self) -> np.ndarray | None:
        """取一帧；失败返回 None（调用方决定回抓帧重试）。"""
        assert self._cap is not None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None
        return np.ascontiguousarray(frame)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
