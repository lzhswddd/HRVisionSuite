# -*- coding: utf-8 -*-
"""相机驱动封装：VideoCamera（视频流相机：视频文件 / RTSP·HTTP / USB 索引）。

职责：打开/抓帧，隐藏 HRVision 相机 API 细节；多源播完自动循环。
"""
from typing import List, Optional

import numpy as np

from HRVision.utils.video_camera import VideoCamera


class CameraDriver:
    """视频流相机：逐帧拉取，源耗尽自动切换/循环。"""

    _cam: VideoCamera

    def __init__(self, video_paths: List[str]):
        self._cam = VideoCamera(cameraType="Video")
        self._cam.SetConfig({"file_paths": video_paths})
        self._cam.Open()
        self._cam.Grab()

    def grab(self) -> Optional[np.ndarray]:
        """抓一帧。失败返回 None（调用方重试）。"""
        ret, frames, _msg = self._cam.GetCameraBuffer(1000)
        if not ret or not frames:
            return None
        return frames[0]
