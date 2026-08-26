import collections.abc
import os
import numpy
import typing
import cv2
try:
    from .camera_base import CameraBase
except ImportError:  # 以脚本方式直接运行时（python HRVision/utils/video_camera.py）
    from camera_base import CameraBase

class VideoCamera(CameraBase):
    """
    基于 OpenCV VideoCapture 的视频流相机（视频文件 / RTSP·HTTP 网络流 / USB 设备索引）。
    拉取式逐帧读取；多源依次播放，全部播完后循环；网络流断流时自动重连一次。
    """
    def __init__(self, cameraType: str = "Video", **kwargs) -> None:
        """
        初始化相机
        """
        super().__init__(cameraType, **kwargs)
        self.file_paths = kwargs.get("file_paths", [])
        self._capture = None
        self.index = -1
        self.reord_index = -1

    def _is_network_stream(self, path) -> bool:
        return isinstance(path, str) and path.lower().startswith(("rtsp://", "http://", "https://"))

    def _is_valid_source(self, path) -> bool:
        """
        文件存在、网络流地址，或 USB 设备索引（int >= 0）
        """
        return (self._is_network_stream(path)
                or (isinstance(path, str) and os.path.isfile(path))
                or (isinstance(path, int) and not isinstance(path, bool) and path >= 0))

    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """
        self.Stop()
        self.file_paths = []
        return True, "Camera closed successfully."

    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据（每次调用读取下一帧，源结束自动切换，全部结束循环）
        """
        if self._capture is None or self.index < 0:
            return False, [], "Camera is not Grabbing."
        if self.index >= len(self.file_paths):
            return False, [], "No more video sources available."

        ret, frame = self._capture.read()
        if not ret:
            # 网络流断流时尝试重连一次
            if self._is_network_stream(self.file_paths[self.index]):
                ret, frame = self._try_reconnect_frame()
        if not ret:
            if not self._switch_to_next_source():
                return False, [], "No more video sources available."
            start_index = self.index
            while True:
                ret, frame = self._capture.read()
                if ret:
                    break
                if not self._switch_to_next_source():
                    return False, [], "No more video sources available."
                if self.index == start_index:
                    return False, [], "No more video sources available."

        if self.exposure_time > 0:
            frame = frame * (self.exposure_time / 1000.0)
        if self.gain > 0:
            frame = frame + self.gain

        user_callback = self._param.get("user_callback", None)
        if user_callback and callable(user_callback):
            frame = user_callback(frame, self._param.get("context", None))
        return True, [frame], "Frame read successfully."

    def GetConfig(self) -> dict:
        """
        获取相机配置
        """
        return {
            "camera_type": self.camera_type,
            "file_paths": self.file_paths,
            "exposure_time": self.exposure_time,
            "gain": self.gain
        }

    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据（打开第一个有效视频源）
        """
        if self.index >= 0:
            return True, "Camera is already grabbing."
        start = self.reord_index if self.reord_index >= 0 else 0
        for i in range(start, len(self.file_paths)):
            cap = cv2.VideoCapture(self.file_paths[i])
            if cap.isOpened():
                self._capture = cap
                self.index = i
                return True, f"Grabbing started from source {i}."
            cap.release()
        return False, "Failed to open any video source."

    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """
        return self.index >= 0, "Camera is not grabbing in video mode."

    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """
        valid = any(self._is_valid_source(p) for p in self.file_paths)
        return valid, "Camera is opened in video mode."

    def Open(self) -> tuple[bool, str]:
        """
        打开相机（校验视频源，不打开句柄）
        """
        valid_paths = [p for p in self.file_paths if self._is_valid_source(p)]
        if not valid_paths:
            return False, "No valid video sources provided."
        self.file_paths = valid_paths
        return True, "Camera opened successfully."

    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """
        if "camera_type" in config:
            self.camera_type = config["camera_type"]
        if "file_paths" in config:
            self.file_paths = config["file_paths"]
        if "exposure_time" in config:
            self.exposure_time = config["exposure_time"]
        if "gain" in config:
            self.gain = config["gain"]

    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调（拉取式语义，无需回调，保留接口）
        """
        pass

    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """
        self.reord_index = self.index
        self.index = -1
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        return True, "Camera stopped successfully."

    def _switch_to_next_source(self) -> bool:
        """
        切换到下一个可打开的视频源（循环）
        """
        n = len(self.file_paths)
        for step in range(1, n + 1):
            idx = (self.index + step) % n
            cap = cv2.VideoCapture(self.file_paths[idx])
            if cap.isOpened():
                if self._capture is not None:
                    self._capture.release()
                self._capture = cap
                self.index = idx
                return True
            cap.release()
        return False

    def _try_reconnect_frame(self) -> tuple[bool, numpy.ndarray]:
        """
        重新打开当前网络流并读取一帧
        """
        if self._capture is not None:
            self._capture.release()
        self._capture = cv2.VideoCapture(self.file_paths[self.index])
        if self._capture.isOpened():
            return self._capture.read()
        return False, None

if __name__ == "__main__":
    import sys
    import types
    # 绕过 TrainWatcherPrv.Ultralytics 私有模块缺失（预存在问题），使 -m 方式可运行
    sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics',
                           types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics'))
    import tempfile
    # 生成一个临时测试视频
    tmp_dir = tempfile.gettempdir()
    video_path = os.path.join(tmp_dir, "hrvision_demo_video.avi")
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (320, 240))
    for i in range(30):
        frame = numpy.zeros((240, 320, 3), numpy.uint8)
        cv2.putText(frame, f"frame {i}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()

    camera = VideoCamera(cameraType="Video")
    camera.SetConfig({"file_paths": [video_path]})
    camera.Open()
    camera.Grab()
    quit_demo = False
    while not quit_demo:
        success, frames, message = camera.GetCameraBuffer()
        if success:
            for frame in frames:
                cv2.imshow("Video", frame)
                if cv2.waitKey(33) & 0xFF == ord('q'):
                    quit_demo = True
                    break
        else:
            print(message)
            break
    camera.Close()
    cv2.destroyAllWindows()
    os.remove(video_path)
