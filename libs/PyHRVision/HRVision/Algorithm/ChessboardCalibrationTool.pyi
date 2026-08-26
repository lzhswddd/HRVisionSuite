"""
HR的棋盘格标定工具
"""
from __future__ import annotations
import collections.abc
import numpy
import numpy.typing
import typing
__all__ = ['AutoCalibratorEx', 'CalibratorEx', 'TransformerEx']
class AutoCalibratorEx:
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, squareSize: tuple[typing.SupportsFloat, typing.SupportsFloat]) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @typing.overload
    def appendImage(self, imagePath: str) -> None:
        """
        appendImage (string)
        """
    @typing.overload
    def appendImage(self, image: typing.Annotated[numpy.typing.ArrayLike, numpy.uint8]) -> None:
        """
        appendImage (array)
        """
    def calibrate(self) -> bool:
        """
        执行标定
        """
    def clear(self) -> None:
        """
        清除标定数据
        """
    def clearImage(self) -> None:
        """
        清除图像数据
        """
    def getChessBoardRank(self, index: typing.SupportsInt = 0) -> list[tuple[int, int]]:
        """
        获取棋盘格行列 (int)
        """
    def getCornerImage(self, index: typing.SupportsInt = 0) -> numpy.typing.NDArray[numpy.uint8]:
        """
        获取角点图像 (int)
        """
    def getImagePoint(self, index: typing.SupportsInt = 0) -> numpy.ndarray:
        """
        获取标定的图像点 (int)
        """
    def getImagePoints(self) -> list[numpy.ndarray]:
        """
        获取标定的图像点组
        """
    def getTransformer(self, index: typing.SupportsInt = 0) -> TransformerEx:
        """
        获取变换器 (int)
        """
    def getWorldPoint(self, index: typing.SupportsInt = 0) -> numpy.ndarray:
        """
        获取标定的世界点 (int)
        """
    def getWorldPoints(self) -> list[numpy.ndarray]:
        """
        获取标定的世界点组
        """
    def load(self, filePath: str) -> None:
        """
        加载标定数据 (string)
        """
    def registerCallback(self, callback: typing.Callable[[str], None]) -> None:
        """
        注册回调函数 (function)
        """
    def save(self, filePath: str) -> None:
        """
        保存标定数据 (string)
        """
    @typing.overload
    def setImages(self, imagePaths: collections.abc.Sequence[str]) -> None:
        """
        setImages (list)
        """
    @typing.overload
    def setImages(self, images: collections.abc.Sequence[typing.Annotated[numpy.typing.ArrayLike, numpy.uint8]]) -> None:
        """
        setImages (list)
        """
    def setSquareSize(self, squareSize: tuple[typing.SupportsFloat, typing.SupportsFloat]) -> None:
        """
        设置方格大小 (tuple)
        """
class CalibratorEx:
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, boardSize: tuple[typing.SupportsInt, typing.SupportsInt], squareSize: tuple[typing.SupportsFloat, typing.SupportsFloat]) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @typing.overload
    def appendImage(self, imagePath: str) -> None:
        """
        appendImage (string)
        """
    @typing.overload
    def appendImage(self, image: typing.Annotated[numpy.typing.ArrayLike, numpy.uint8]) -> None:
        """
        appendImage (array)
        """
    def calibrate(self) -> bool:
        """
        执行标定
        """
    def clear(self) -> None:
        """
        清除标定数据
        """
    def clearImage(self) -> None:
        """
        清除图像数据
        """
    def getChessBoardRank(self, index: typing.SupportsInt = 0) -> list[tuple[int, int]]:
        """
        获取棋盘格行列 (int)
        """
    def getCornerImage(self, index: typing.SupportsInt = 0) -> numpy.typing.NDArray[numpy.uint8]:
        """
        获取角点图像 (int)
        """
    def getImagePoint(self, index: typing.SupportsInt = 0) -> numpy.ndarray:
        """
        获取标定的图像点 (int)
        """
    def getImagePoints(self) -> list[numpy.ndarray]:
        """
        获取标定的图像点组
        """
    def getTransformer(self, index: typing.SupportsInt = 0) -> TransformerEx:
        """
        获取变换器 (int)
        """
    def getWorldPoint(self, index: typing.SupportsInt = 0) -> numpy.ndarray:
        """
        获取标定的世界点 (int)
        """
    def getWorldPoints(self) -> list[numpy.ndarray]:
        """
        获取标定的世界点组
        """
    def load(self, filePath: str) -> None:
        """
        加载标定数据 (string)
        """
    def save(self, filePath: str) -> None:
        """
        保存标定数据 (string)
        """
    def setBoardSize(self, boardSize: tuple[typing.SupportsInt, typing.SupportsInt]) -> None:
        """
        设置棋盘格大小 (tuple)
        """
    @typing.overload
    def setImages(self, imagePaths: collections.abc.Sequence[str]) -> None:
        """
        setImages (list)
        """
    @typing.overload
    def setImages(self, images: collections.abc.Sequence[typing.Annotated[numpy.typing.ArrayLike, numpy.uint8]]) -> None:
        """
        setImages (list)
        """
    def setSquareSize(self, squareSize: tuple[typing.SupportsFloat, typing.SupportsFloat]) -> None:
        """
        设置方格大小 (tuple)
        """
class TransformerEx:
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, cameraMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], distCoeffs: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], affineMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> None:
        ...
    @typing.overload
    def __init__(self, cameraMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], cameraMatrix_inv: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], distCoeffs: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], affineMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], affineMatrix_inv: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def getAffineMatrix(self) -> numpy.typing.NDArray[numpy.float64]:
        """
        获取外参 (array)
        """
    def getCameraMatrix(self) -> numpy.typing.NDArray[numpy.float64]:
        """
        获取相机内参 (array)
        """
    def getDistCoeffs(self) -> numpy.typing.NDArray[numpy.float64]:
        """
        获取畸变矩阵 (array)
        """
    @typing.overload
    def getPixelCoordinate(self, world: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> numpy.typing.NDArray[numpy.float64]:
        """
        获取像素坐标 (array)
        """
    @typing.overload
    def getPixelCoordinate(self, x: typing.SupportsFloat, y: typing.SupportsFloat, z: typing.SupportsFloat) -> tuple[float, float]:
        """
        获取像素坐标 (double, double, double)
        """
    @typing.overload
    def getWorldCoordinate(self, px: typing.SupportsFloat, py: typing.SupportsFloat, Zw: typing.SupportsFloat = 0) -> tuple[float, float, float]:
        """
        获取世界坐标 (double, double, double)
        """
    @typing.overload
    def getWorldCoordinate(self, pixels: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], Zw: typing.SupportsFloat | typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> numpy.typing.NDArray[numpy.float64]:
        """
        获取世界坐标 (array, (double, array))
        """
    def load(self, filePath: str) -> None:
        """
        加载变换器 (string)
        """
    def save(self, filePath: str) -> None:
        """
        保存变换器 (string)
        """
    def setAffineMatrix(self, affineMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> None:
        """
        设置外参 (array)
        """
    def setCameraMatrix(self, cameraMatrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> None:
        """
        设置相机内参 (array)
        """
    def setDistCoeffs(self, distCoeffs: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]) -> None:
        """
        设置畸变矩阵 (array)
        """
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'HR的棋盘格标定工具'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
