import collections.abc
from pathlib import Path
import numpy
import typing
import cv2
import os
try:
    from .camera_base import CameraBase
except ImportError:  # 以脚本方式直接运行时（python HRVision/utils/local_camera.py）
    from camera_base import CameraBase

class LocalCamera(CameraBase):
    def __init__(self, cameraType: str = "opencv", **kwargs) -> None:
        """
        初始化相机
        """
        super().__init__(cameraType, **kwargs)
        self.file_paths = kwargs.get("file_paths", [])
        self.image_paths = kwargs.get("image_paths", [])
        self.index = -1
        self.reord_index = -1

    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """
        self.Stop()
        self.image_paths = []
        return True, "Camera closed successfully."

    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据
        """
        if self.camera_type != "File" or not self.image_paths:
            return False, [], "Camera type is not 'File' or no image paths provided."

        if self.index < 0:
            return False, [], "Camera is not Grabbing."

        if self.index >= len(self.image_paths):
            return False, [], "No more images to read."

        try:
            with open(self.image_paths[self.index], 'rb') as f:
                data = numpy.frombuffer(f.read(), numpy.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
            if image is None:
                return False, [], f"Failed to decode image. {self.image_paths[self.index]}"

            if self.exposure_time > 0:
                image = image * (self.exposure_time / 1000.0)
            if self.gain > 0:
                image = image + self.gain

            user_callback = self._param.get("user_callback", None)
            if user_callback and callable(user_callback):
                image = user_callback(image, self._param.get("context", None))

            self.index += 1
            if self.index >= len(self.image_paths):
                self.index = 0
            return True, [image], "Image read successfully."
        except Exception as e:
            return False, [], f"Failed to read image: {self.image_paths[self.index]} - {str(e)}"

    def GetConfig(self) -> dict:
        """
        获取相机配置
        """
        return {
            "camera_type": self.camera_type,
            "image_paths": self.image_paths,
            "exposure_time": self.exposure_time,
            "gain": self.gain
        }

    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据
        """
        if self.index < 0:
            if self.reord_index >= 0:
                self.index = self.reord_index
            else:
                self.index = 0
        return True, "Grabbing is not applicable for local camera."

    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """
        return self.index >= 0, "Grabbing is not applicable for local camera."

    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """
        return len(self.image_paths) > 0, "Camera is always open in local mode."

    def Open(self) -> tuple[bool, str]:
        """
        打开相机
        """
        self.image_paths = []
        for path in self.file_paths:
            image_suffix_list = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.raw']
            if os.path.isfile(path):
                if Path(path).suffix.lower() in image_suffix_list:
                    self.image_paths.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(tuple(image_suffix_list)):
                            self.image_paths.append(os.path.join(root, file))
        return self.IsOpened()

    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """
        if "camera_type" in config:
            self.camera_type = config["camera_type"]
        if "file_paths" in config:
            self.file_paths = config["file_paths"]
        if "image_paths" in config:
            self.image_paths = config["image_paths"]
        if "exposure_time" in config:
            self.exposure_time = config["exposure_time"]
        if "gain" in config:
            self.gain = config["gain"]

    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调
        """
        pass

    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """
        self.reord_index = self.index
        self.index = -1
        return True, "Camera stopped successfully."

if __name__ == "__main__":
    import sys
    import types
    # 绕过 TrainWatcherPrv.Ultralytics 私有模块缺失（预存在问题），使 -m 方式可运行
    sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics',
                           types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics'))
    camera = LocalCamera(cameraType="File")
    camera.SetConfig({
        "file_paths": [r"C:\Users\public\Documents\MVTec\HALCON-20.11-Steady\examples\images"],
    })
    camera.Open()
    camera.Grab()
    while True:
        success, images, message = camera.GetCameraBuffer()
        if success:
            for img in images:
                cv2.imshow("Image", img)
                cv2.waitKey(33)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        else:
            print(message)
            break
