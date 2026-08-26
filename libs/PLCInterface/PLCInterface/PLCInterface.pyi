"""
PLC模块
"""
from __future__ import annotations
import typing
__all__ = ['PLC']
class PLC:
    @staticmethod
    def canUse() -> bool:
        """
        Check if PLC can be used
        """
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __str__(self) -> str:
        ...
    def close(self) -> None:
        """
        Close the PLC connection
        """
    def createSerial(self, inSerialStr: str, plcType: str, portName: str, baudRate: typing.SupportsInt, dataBits: typing.SupportsInt, stopBits: str = 'One', parity: str = 'None') -> None:
        """
        Create a PLC connection using Serial
        """
    def createTcp(self, inSerialStr: str, plcType: str, ip: str, port: typing.SupportsInt) -> None:
        """
        Create a PLC connection using IP
        """
    def getErrorInfo(self) -> str:
        """
        Get the last error information from the PLC
        """
    def isConnected(self) -> bool:
        """
        Check if the PLC is connected
        """
    def openConnection(self, timeOut: typing.SupportsInt = 2000) -> bool:
        """
        Open the PLC connection
        """
    def readNumber(self, addr: str, type: str, timeOut: typing.SupportsInt = 2000) -> str:
        """
        Read a number from the PLC
        """
    def readNumbers(self, addr: str, type: str, length: typing.SupportsInt, timeOut: typing.SupportsInt = 2000) -> str:
        """
        Read multiple numbers from the PLC
        """
    def readString(self, addr: str, num: typing.SupportsInt, timeOut: typing.SupportsInt = 2000) -> str:
        """
        Read a string from the PLC
        """
    def writeNumber(self, addr: str, val: str, type: str, timeOut: typing.SupportsInt = 2000) -> bool:
        """
        Write a number to the PLC
        """
    def writeNumbers(self, addr: str, val: str, type: str, timeOut: typing.SupportsInt = 2000) -> bool:
        """
        Write multiple numbers to the PLC
        """
    def writeString(self, addr: str, num: typing.SupportsInt, data: str, isFill: bool = True, timeOut: typing.SupportsInt = 2000) -> bool:
        """
        Write a string to the PLC
        """
__author__: str = 'HRVision'
__copyright__: str = 'Copyright (c) 2023 HRVision'
__description__: str = 'PLC模块'
__license__: str = 'MIT License'
__version__: str = '0.1.0'
