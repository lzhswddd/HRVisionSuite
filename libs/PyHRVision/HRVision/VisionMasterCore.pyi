"""
VisionMasterCore模块
"""
from __future__ import annotations
import typing
__all__ = ['VisionMasterCore']
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
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'VisionMasterCore模块'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
