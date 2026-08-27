"""
VisionMasterCore模块
"""
from __future__ import annotations
import typing
__all__ = ['GlobalCameraCore', 'VisionMasterCore']
class GlobalCameraCore:
    """
    全局相机控制类：不经流程直接从相机取图。名称 = 方案中配置的全局相机名；构造前须已 loadSolution，重新 loadSolution 前必须销毁（del/离开作用域）所有 GlobalCameraCore 实例，否则 SDK 工具指针悬空。构造时自动执行出图不触发流程(SetTriggerProcessEnable(false))，可用 setTriggerProcessEnable 改回
    """
    def __init__(self, name: str) -> None:
        """
        创建全局相机实例
        """
    def __repr__(self) -> str:
        ...
    def getCameraList(self) -> list:
        """
        枚举可用相机列表[{name,sn}]
        """
    def getChosenCameraSN(self) -> str:
        """
        获取当前绑定相机SN
        """
    def getExposureTime(self) -> float:
        """
        获取曝光时间(微秒)
        """
    def getGain(self) -> float:
        """
        获取增益(dB)
        """
    def getHeight(self) -> int:
        """
        获取图像高度
        """
    def getLatestImage(self) -> typing.Any:
        """
        立即返回最新帧，无帧返回None
        """
    def getPixelFormat(self) -> int:
        """
        获取像素格式(MVS编码)
        """
    def getTriggerDelay(self) -> float:
        """
        获取触发延迟(微秒)
        """
    def getTriggerProcessEnable(self) -> bool:
        """
        出图是否触发流程运行
        """
    def getTriggerSource(self) -> int:
        """
        获取触发源
        """
    def getWidth(self) -> int:
        """
        获取图像宽度
        """
    def grabImage(self, timeout_ms: typing.SupportsInt = 5000) -> typing.Any:
        """
        阻塞等待下一帧图像，超时返回None；timeout_ms<=0 立即返回
        """
    def isConnected(self) -> bool:
        """
        相机是否连接
        """
    def setChosenCameraSN(self, sn: str) -> None:
        """
        切换全局相机绑定的相机SN
        """
    def setExposureTime(self, us: typing.SupportsFloat) -> None:
        """
        设置曝光时间(微秒)
        """
    def setGain(self, db: typing.SupportsFloat) -> None:
        """
        设置增益(dB)
        """
    def setPixelFormat(self, fmt: typing.SupportsInt) -> None:
        """
        设置像素格式(MVS编码)
        """
    def setTriggerDelay(self, us: typing.SupportsFloat) -> None:
        """
        设置触发延迟(微秒)
        """
    def setTriggerProcessEnable(self, enable: bool) -> None:
        """
        出图是否触发流程运行
        """
    def setTriggerSource(self, source: typing.SupportsInt) -> None:
        """
        设置触发源(0=硬触发 1=软触发)
        """
    def softwareTrigger(self) -> None:
        """
        发一次软触发
        """
class VisionMasterCore:
    def DestroyObj(self) -> None:
        """
        销毁对象
        """
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __str__(self) -> str:
        ...
    def closeSolution(self) -> None:
        """
        关闭方案
        """
    def commIsConnected(self, deviceId: typing.SupportsInt) -> int:
        """
        通信设备是否连接(设备ID)
        """
    def commRecvData(self, deviceId: typing.SupportsInt, maxLen: typing.SupportsInt = 1024) -> bytes:
        """
        从通信设备接收数据(设备ID, 最大长度)
        """
    def commSendBytes(self, deviceId: typing.SupportsInt, data: bytes) -> int:
        """
        发送数据到通信设备(设备ID, bytes)
        """
    def commSetFloat(self, deviceId: typing.SupportsInt, values: list) -> int:
        """
        向通信设备写浮点数组(设备ID, 列表)
        """
    def commSetInt(self, deviceId: typing.SupportsInt, values: list) -> int:
        """
        向通信设备写整型数组(设备ID, 列表)
        """
    def commSetString(self, deviceId: typing.SupportsInt, strValue: str) -> int:
        """
        向通信设备写字符串(设备ID, 字符串)
        """
    def createSolution(self) -> int:
        """
        创建方案对象
        """
    def deleteAllProcedure(self) -> None:
        """
        删除所有流程
        """
    def deleteProcedure(self, name: str = '') -> None:
        """
        删除指定流程
        """
    def getProcedure(self, inProcedureName: str) -> int:
        """
        获取流程对象
        """
    def getProcedureList(self) -> None:
        """
        获取流程列表
        """
    def getSolution(self) -> int:
        """
        获取方案对象
        """
    def isLoadFinish(self) -> bool:
        """
        判断是否加载完成
        """
    def loadProcedure(self, inProcedurePath: str) -> int:
        """
        加载流程文件
        """
    def loadSolution(self, inSolutionPath: str) -> int:
        """
        加载方案文件
        """
    def saveAllProcedure(self, folderPath: str = '') -> int:
        """
        保存所有流程
        """
    def saveProcedure(self, inProcedureName: str, folderPath: str = '') -> int:
        """
        保存指定流程
        """
def _mvs_pixel_info(pixelFormat: typing.SupportsInt) -> tuple[str, int]:
    """
    MVS像素格式转(dtype,通道数)
    """
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'VisionMasterCore模块'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
