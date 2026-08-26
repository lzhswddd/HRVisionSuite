"""
HRVision的相机接口模块
"""
from __future__ import annotations
import collections.abc
import numpy
import typing
__all__ = ['Camera']
class Camera:
    def ChangeType(self, cameraType: str) -> bool:
        """
        更改相机类型
        """
    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """
    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据
        """
    def GetConfig(self) -> dict:
        """
        获取相机配置
        """
    def GetExposureTime(self) -> tuple[float, str]:
        """
        获取曝光时间
        """
    def GetGain(self) -> tuple[float, str]:
        """
        获取增益
        """
    def GetValue(self, key: str) -> tuple[typing.Any, str]:
        """
        获取相机参数
        """
    def GetParameterTree(self) -> tuple[typing.Any, str]:
        """
        获取相机参数树(GenICam JSON)
        """
    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据
        """
    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """
    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """
    def LoadConfig(self, fileName: str) -> bool:
        """
        加载相机配置
        """
    def Open(self) -> tuple[bool, str]:
        """
        打开相机
        """
    def SaveConfig(self, fileName: str) -> bool:
        """
        保存相机配置
        """
    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """
    def SetExposureTime(self, timeMs: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置曝光时间
        """
    def SetGain(self, gain: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置增益
        """
    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调
        """
    def SetValue(self, key: str, value: typing.Any) -> tuple[bool, str]:
        """
        设置相机参数
        """
    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, cameraType: str) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __str__(self) -> str:
        ...
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'HRVision的相机接口模块'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
