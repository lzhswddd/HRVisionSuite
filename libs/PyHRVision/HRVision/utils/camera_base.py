import abc
import collections.abc
import numpy
import typing

class CameraBase(abc.ABC):
    """
    相机抽象基类，接口对齐 HRCamera.pyi 中的 Camera。
    子类必须实现：Open、Close、Grab、Stop、GetCameraBuffer、GetConfig、
    SetConfig、IsGrabbing、IsOpened、SetReciveBufferCallback。
    """
    def __init__(self, cameraType: str = "opencv", **kwargs) -> None:
        """
        初始化相机
        """
        self.camera_type = cameraType
        self.exposure_time = kwargs.get("exposure_time", 0.0)
        self.gain = kwargs.get("gain", 0.0)
        self._param = {}

    def __del__(self) -> None:
        self.Close()

    def ChangeType(self, cameraType: str) -> bool:
        """
        更改相机类型
        """
        self.camera_type = cameraType
        return True

    def GetExposureTime(self) -> tuple[float, str]:
        """
        获取曝光时间
        """
        return self.exposure_time, "Exposure time is not applicable for camera."

    def GetGain(self) -> tuple[float, str]:
        """
        获取增益
        """
        return self.gain, "Gain is not applicable for camera."

    def GetValue(self, key: str) -> tuple[typing.Any, str]:
        """
        获取相机参数
        """
        if key == "exposure_time":
            return self.exposure_time, "Exposure time is not applicable for camera."
        elif key == "gain":
            return self.gain, "Gain is not applicable for camera."
        else:
            if key in self._param:
                return self._param[key], f"Parameter '{key}' retrieved successfully."
            else:
                return None, f"Unknown parameter: {key}"

    def LoadConfig(self, fileName: str) -> tuple[bool, str]:
        """
        加载相机配置
        注：HRCamera.pyi 中声明为 -> bool，实际实现返回 (True, 消息) 元组，此处按实际行为修正。
        """
        return True, "Loading configuration is not applicable for camera."

    def SaveConfig(self, fileName: str) -> tuple[bool, str]:
        """
        保存相机配置
        注：HRCamera.pyi 中声明为 -> bool，实际实现返回 (True, 消息) 元组，此处按实际行为修正。
        """
        return True, "Saving configuration is not applicable for camera."

    def SetExposureTime(self, timeMs: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置曝光时间
        """
        self.exposure_time = timeMs
        return True, f"Exposure time set to {timeMs} ms."

    def SetGain(self, gain: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置增益
        """
        self.gain = gain
        return True, f"Gain set to {gain}."

    def SetValue(self, key: str, value: typing.Any) -> tuple[bool, str]:
        """
        设置相机参数
        """
        if key == "exposure_time":
            return self.SetExposureTime(value)
        elif key == "gain":
            return self.SetGain(value)
        else:
            self._param[key] = value
            return True, f"Parameter '{key}' set successfully."

    @abc.abstractmethod
    def Open(self) -> tuple[bool, str]:
        """
        打开相机
        """

    @abc.abstractmethod
    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """

    @abc.abstractmethod
    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据
        """

    @abc.abstractmethod
    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """

    @abc.abstractmethod
    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据
        """

    @abc.abstractmethod
    def GetConfig(self) -> dict:
        """
        获取相机配置
        """

    @abc.abstractmethod
    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """

    @abc.abstractmethod
    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """

    @abc.abstractmethod
    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """

    @abc.abstractmethod
    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调
        """
