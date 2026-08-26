"""
VisionMasterProcess
"""
from __future__ import annotations
import numpy
import numpy.typing
import typing
__all__ = ['VisionMasterProcess']
class VisionMasterProcess:
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __str__(self) -> str:
        ...
    def getModuleList(self) -> dict:
        """
        获取流程模块列表({显示名: 类型名})
        """
    def getModuleParam(self, moduleName: str, paramName: str) -> str:
        """
        读取模块参数(模块名, 参数名)
        """
    def getOutput(self, outputName: str) -> typing.Any:
        """
        获取单个输出(输出名), 不存在返回None
        """
    def getOutputNamesList(self) -> list:
        """
        获取输出名称列表
        """
    def getOutputReult(self) -> dict:
        """
        获取输出结果
        """
    def getParamType(self) -> dict:
        """
        获取参数类型
        """
    def isProcedureLoaded(self) -> bool:
        """
        判断流程是否加载
        """
    def loadProcedure(self, inProcedurePath: typing.SupportsInt) -> int:
        """
        加载流程文件
        """
    def processProcedure(self, img_array: typing.Annotated[numpy.typing.ArrayLike, numpy.uint8], resourceModuleName: str, restoreImageSource: bool = True) -> bool:
        """
        处理流程
        """
    def processProcedureTimer(self, img_array: typing.Annotated[numpy.typing.ArrayLike, numpy.uint8], resourceModuleName: str, restoreImageSource: bool = True) -> list:
        """
        处理流程，返回各阶段耗时列表(ms)
        """
    def runProcedure(self) -> bool:
        """
        单独运行流程(不推图，图像源按方案配置采图，适合相机流程)
        """
    def setModuleParam(self, moduleName: str, paramName: str, strValue: str) -> int:
        """
        设置模块参数(模块名, 参数名, 字符串值, 0=成功)
        """
    def setProcedureParam(self, paramName: str, strValue: str) -> int:
        """
        设置流程参数(参数名, 字符串值, 0=成功)
        """
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'VisionMasterProcess'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
