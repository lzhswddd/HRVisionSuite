import os
import time
import socket
import json
import sys
import traceback
import threading
import typing
import signal
import psutil

from PySide6.QtGui import QImage
from PySide6.QtCore import QDataStream, QByteArray, QUuid, QIODevice, QBuffer
from PySide6.QtCore import QSharedMemory, QProcess
from PySide6.QtCore import QObject, Signal
import numpy as np
from typing import Callable, Optional

def ndarray_to_qimage(array: np.ndarray) -> QImage:
    if array is None:
        return QImage()

    # 检查数组的维度
    if len(array.shape) == 2:
        # 灰度图像
        height, width = array.shape
        bytes_per_line = width
        qimage = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    elif len(array.shape) == 3:
        # 彩色图像 (RGB 或 RGBA)
        height, width, channels = array.shape
        if channels == 3:
            # 框架约定 3 通道帧 = RGB（OpenCV 系相机已在源侧 BGR2RGB；
            # 海康 RGB8_Packed 等 SDK 输出亦为 RGB）——直接 RGB888 包装
            qimage = QImage(array.data, width, height, 3 * width,
                            QImage.Format_RGB888)
        elif channels == 4:
            # RGBA 图像
            bytes_per_line = 4 * width
            qimage = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        elif channels == 1:
            # 单通道图像（可能是灰度图）
            height, width = array.shape[:2]
            bytes_per_line = width
            qimage = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        else:
            raise ValueError("Unsupported channel number: {}".format(channels))
    else:
        raise ValueError("Unsupported ndarray shape: {}".format(array.shape))

    return qimage.copy()  # 复制数据以确保安全

def qimage_to_ndarray(qimage: QImage) -> np.ndarray:
    """将 QImage 转换为 NumPy ndarray"""
    if qimage is None:
        return np.array([])
    if qimage.format() == QImage.Format_RGB888:
        width = qimage.width()
        height = qimage.height()
        step = qimage.bytesPerLine()
        ptr = qimage.bits()  # 获取图像的底层数据指针
        if step != width * 3:
            array = np.array(ptr, dtype=np.uint8).reshape((height, step // 3, 3))
            array = array[:, :width, :]  # 修剪到正确的宽度
        else:
            array = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))  # 转换为 NumPy 数组
        return array
    elif qimage.format() == QImage.Format_RGBA8888 or qimage.format() == QImage.Format_ARGB32 or qimage.format() == QImage.Format_RGB32:
        width = qimage.width()
        height = qimage.height()
        step = qimage.bytesPerLine()
        ptr = qimage.bits()  # 获取图像的底层数据指针
        if step != width * 4:
            array = np.array(ptr, dtype=np.uint8).reshape((height, step // 4, 4))
            array = array[:, :width, :]
        else:
            array = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))  # 转换为 NumPy 数组
        return array
    elif qimage.format() == QImage.Format_Grayscale8 or qimage.format() == QImage.Format_Indexed8:
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        step = qimage.bytesPerLine()
        if step != width:
            array = np.array(ptr, dtype=np.uint8).reshape((height, step))
        else:
            array = np.array(ptr, dtype=np.uint8).reshape((height, width))  # 转换为 NumPy 数组
        return array
    else:
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        step = qimage.bytesPerLine()
        channels = step // width
        if width * channels != step:
            array = np.array(ptr, dtype=np.uint8).reshape((height, step // channels, channels))
            array = array[:, :width, :]
        else:
            array = np.array(ptr, dtype=np.uint8).reshape((height, width, -1))  # 转换为 NumPy 数组
        return array

class SharedMemory(QSharedMemory):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)

    def __init__(self, key: str):
        super().__init__()
        self.setKey(key)
        self.setNativeKey(key)

    def setObjectBuffer(self, obj: dict) -> bool:
        if obj is None:
            return False
        if self.isAttached():
            if not self.detach():
                return False

        # Serialize the object into a QByteArray using QBuffer
        buffer = QBuffer()
        buffer.open(QIODevice.ReadWrite)
        stream = QDataStream(buffer)
        stream.writeQVariant(obj)  # Assuming obj is serializable as QVariant

        # Create shared memory segment
        if not self.create(buffer.size()):
            return False

        # Lock the shared memory and write data
        self.lock()
        try:
            to = self.data()
            from_data = buffer.data().data()
            memory_size = min(self.size(), buffer.size())
            to[:memory_size] = from_data[:memory_size]  # Copy data into shared memory
        finally:
            self.unlock()

        return True

    def getObjectBuffer(self) -> dict:
        obj = {}
        if not self.isAttached():
            return obj

        # Create a QBuffer to read data from shared memory
        buffer = QBuffer()
        self.lock()  # Lock the shared memory to prevent access by other processes
        try:
            buffer.setData(self.constData(), self.size())  # Set data from shared memory
            buffer.open(QBuffer.ReadOnly)
            stream = QDataStream(buffer)
            stream.readQVariant(obj)  # Assuming obj is serializable as QVariant
        finally:
            self.unlock()  # Unlock the shared memory after reading
            self.detach()  # Detach the process from the shared memory

        return obj

    def setImageBuffer(self, image: typing.Union[QImage, np.ndarray]) -> bool:
        if image is None:
            return False
        if self.isAttached():
            if not self.detach():
                return False

        if isinstance(image, np.ndarray):
            image = self.ndarray_to_qimage(image)

        # Calculate the size of the shared memory
        size = image.sizeInBytes() + 4 * 4 + 8  # sizeof(int)*4 + sizeof(qint64)
        data = bytearray(size)

        # Prepare the data to write into shared memory
        qint64_ptr = memoryview(data)[:8]  # First 8 bytes for qint64
        qint64_ptr[:] = int(image.sizeInBytes()).to_bytes(8, byteorder='little')

        image_data = memoryview(data)[8:8 + image.sizeInBytes()]
        image_data[:] = np.array(image.constBits(), copy=False).tobytes()

        int_ptr = memoryview(data)[8 + image.sizeInBytes():]
        int_ptr[:4] = int(image.width()).to_bytes(4, byteorder='little')
        int_ptr[4:8] = int(image.height()).to_bytes(4, byteorder='little')
        int_ptr[8:12] = int(image.bytesPerLine()).to_bytes(4, byteorder='little')
        int_ptr[12:16] = int(image.format().value).to_bytes(4, byteorder='little')

        # Create shared memory segment
        if not self.create(size):
            return False

        # Lock the shared memory and write data
        self.lock()
        try:
            to = self.data()
            from_data = data
            memory_size = min(self.size(), size)
            to[:memory_size] = from_data[:memory_size]  # Copy data into shared memory
        finally:
            self.unlock()

        return True

    def getImageBuffer(self) -> QImage:
        image = QImage()
        if self.attach():
            # 读取共享内存中的数据
            self.lock()  # 读取数据时锁定共享内存段，其他进程将不能访问该共享内存
            try:
                data = self.constData()
                qint64_ptr = memoryview(data)[:8]  # 前 8 字节为 qint64
                mem_size = int.from_bytes(qint64_ptr, byteorder='little')

                raw = memoryview(data)[8:8 + mem_size]  # 图像的原始数据
                int_ptr = memoryview(data)[8 + mem_size:]  # 后续部分为图像元数据

                width = int.from_bytes(int_ptr[:4], byteorder='little')
                height = int.from_bytes(int_ptr[4:8], byteorder='little')
                stride = int.from_bytes(int_ptr[8:12], byteorder='little')
                format = QImage.Format(int.from_bytes(int_ptr[12:16], byteorder='little'))

                # 创建 QImage
                image = QImage(raw, width, height, stride, format)
                image = image.copy()  # 调用 copy() 确保数据安全
            finally:
                # 解锁共享内存并分离
                self.unlock()
                self.detach()

        return image
     
class ProcessSocket:
    def __init__(self, uid:str):
        self.uid = uid
        
        self.inputJson = {}
        self.inputImage:dict[str, QImage] = {}
        self.inputObject = {}

        self.outputJson = {}
        self.outputImage:dict[str, QImage] = {}
        self.outputObject = {}

        self.message = ''
        self.channel = ''
        
        self.parent = None
        self.sharedMemorys = {}
        
        self.inputlock = threading.Lock()
        self.outputlock = threading.Lock()
        
    def reply(self):
        if self.parent is not None:
            self.parent.replyTask(self)
        
    def lockInput(self):
        self.inputlock.acquire()
        
    def unlockInput(self):
        self.inputlock.release()
        
    def lockOutput(self):
        self.outputlock.acquire()
        
    def unlockOutput(self):
        self.outputlock.release()
        
    def InputParamToSharedMemory(self):
        self.inputlock.acquire()
        if len(self.inputObject) > 0:
            _key = self.uid + "_parameters"
            if _key not in self.sharedMemorys:
                self.sharedMemorys[_key] = SharedMemory(_key)
            obj = self.inputObject
            if self.sharedMemorys[_key].setObjectBuffer(obj):
                self.inputJson["process_parameters_address"] = _key
        if len(self.inputImage) > 0:
            imageNode = {}
            for key in self.inputImage.keys():
                _key = self.uid + "_" + key
                if _key not in self.sharedMemorys:
                    self.sharedMemorys[_key] = SharedMemory(_key)
                if self.sharedMemorys[_key].setImageBuffer(self.inputImage[key]):
                    imageNode[key] = _key
            self.inputJson["process_images"] = imageNode
        self.inputlock.release()
        
    def InputParamFromSharedMemory(self):
        self.inputlock.acquire()
        if "process_parameters_address" in self.inputJson:
            sharedMemory = SharedMemory(self.inputJson["process_parameters_address"])
            self.inputObject = sharedMemory.getObjectBuffer()
            
        if "process_images" in self.inputJson:
            outputNode = self.inputJson["process_images"]
            for key in outputNode.keys():
                sharedMemory = SharedMemory(outputNode[key])
                self.inputImage[key] = sharedMemory.getImageBuffer()
        self.inputlock.release()
        
    def OutputParamToSharedMemory(self):
        self.outputlock.acquire()
        if len(self.outputObject) > 0:
            _key = self.uid + "_parameters"
            if _key not in self.sharedMemorys:
                self.sharedMemorys[_key] = SharedMemory(_key)
            obj = self.outputObject
            if self.sharedMemorys[_key].setObjectBuffer(obj):
                self.outputJson["process_parameters_address"] = _key
        if len(self.outputImage) > 0:
            imageNode = {}
            for key in self.outputImage.keys():
                _key = self.uid + "_" + key
                if _key not in self.sharedMemorys:
                    self.sharedMemorys[_key] = SharedMemory(_key)
                if self.sharedMemorys[_key].setImageBuffer(self.outputImage[key]):
                    imageNode[key] = _key
            self.outputJson["process_images"] = imageNode
        self.outputlock.release()
        
    def OutputParamFromSharedMemory(self):
        self.outputlock.acquire()
        if "process_parameters_address" in self.outputJson:
            sharedMemory = SharedMemory(self.outputJson["process_parameters_address"])
            self.outputObject = sharedMemory.getObjectBuffer()
            
        if "process_images" in self.outputJson:
            outputNode = self.outputJson["process_images"]
            for key in outputNode.keys():
                sharedMemory = SharedMemory(outputNode[key])
                self.outputImage[key] = sharedMemory.getImageBuffer()
        self.outputlock.release()
    
class Client():
    def __init__(self, client_socket:socket.socket = None, process:Optional[Callable[[ProcessSocket], None]] = None, request:Optional[Callable[[dict, str], None]] = None):
        super().__init__(None)
        self.tempMsg:bytes = b''
        self.startReceive = False
        self.bufferSize = 0
        self.recordbufferSize = 0
        self.largeBuffer:bytes = b''
        self.online = False
        self.client_socket:socket.socket = client_socket
        self.sharedMemorys:dict[str, SharedMemory] = {}
        self.replyJson = ""
        
        self.threadLock = threading.Lock()
        self.sockets:dict[str, ProcessSocket] = {}
        self.events:dict[str, threading.Condition] = {}
        self.iswait:dict[str, bool] = {}
        
        self.exitLoop = False
        self.receiveThread:threading.Thread = None
        
        if self.client_socket is not None:
            try:
                client_socket.getpeername()
                self.start()
            except socket.error:
                pass
            
        self.process = process
        self.request = request

    def __del__(self):
        self.stop()
    
    def clear(self):
        self.threadLock.acquire()
        for key in self.events.keys():
            with self.events[key]:
                self.events[key].notify()
        self.threadLock.release()
    
    def start(self):
        if self.receiveThread is None or not self.receiveThread.is_alive():
            self.clear()
            self.receiveThread = threading.Thread(target=self.__LoopFun)
            self.receiveThread.start()
            
    def stop(self):
        if self.receiveThread is not None and self.receiveThread.is_alive():
            self.clear()
            self.exitLoop = True
            self.receiveThread.join()
            self.receiveThread = None
        
    def __LoopFun(self):
        self.exitLoop = False
        while self.exitLoop is False:
            try:
                recvmsg = self.client_socket.recv(8192)
                if len(recvmsg) == 0:
                    break
                self.receiveClientMsg(recvmsg)
            except Exception as e:
                traceback.print_exc()
                break
            
    def receiveClientMsg(self, message:bytes) -> None:
        if message != '':
            if self.startReceive is True:
                buffer = message
                self.largeBuffer += buffer
                self.bufferSize -= len(buffer)
                # print(self.bufferSize)
                if self.bufferSize <= 0:
                    message = self.largeBuffer[self.recordbufferSize:-1]
                    self.largeBuffer = self.largeBuffer[0:self.recordbufferSize]
                    
                    self.startReceive = False
                    self.onlineProcessSocket()
                    
                    if self.tempMsg != "":
                        message = self.tempMsg + message
                    ret, strJsons, remain, middle = self.splitJson(message)
                    if ret == 0:
                        for _str in strJsons:
                            try:
                                _json = json.loads(_str.replace("\\", "\\\\"))
                                self.processSocketJson(_json)
                            except Exception as e:
                                
                                traceback.print_exc()
                    elif ret == 1:
                        self.tempMsg = message
                        print("may be have err", message)
            else:
                if self.tempMsg != "":
                    message = self.tempMsg + message
                ret, strJsons, remain, middle = self.splitJson(message)
                if len(remain) < 500:
                    pass
                    #print("type 2")
                    #print(ret)
                    #print(remain)
                    #print(message)
                if ret == 0:
                    index = 0
                    for _str in strJsons:
                        try:
                            _json = json.loads(_str)
                            self.processSocketJson(_json)
                        except Exception as e:
                            traceback.print_exc()
                        self.tempMsg = remain
                        if self.bufferSize != 0 and self.startReceive is True:
                            self.recordbufferSize = self.bufferSize
                            if len(middle) != 0:
                                buffer = middle[index].encode("utf-8")
                                index += 1
                                self.largeBuffer += buffer
                                self.bufferSize -= len(buffer)
                                if self.bufferSize <= 0:
                                    self.largeBuffer = self.largeBuffer[0:self.recordbufferSize]
                                    self.startReceive = False
                                    self.onlineProcessSocket()
                    if self.bufferSize != 0 and self.startReceive is True:
                        self.recordbufferSize = self.bufferSize
                        if len(remain) != 0:
                            buffer = remain.encode("utf-8")
                            self.largeBuffer += buffer
                            self.bufferSize -= len(buffer)
                            if self.bufferSize <= 0:
                                self.largeBuffer = self.largeBuffer[0:self.recordbufferSize]
                                self.startReceive = False
                                self.onlineProcessSocket()
                elif ret == 1:
                    self.tempMsg = message
                    
    def splitJson(self, str:bytes):
        _list = []
        remain = ''
        middle = []
        _ret = -1
        try:
            message = str.decode()
        except Exception as ex:
            print(str)
        if message != "":
            _start = _end = -1
            count = 0
            remain = message
            for i in range(len(message)):
                ch = message[i]
                if ch == '{':
                    if count == 0:
                        if _end != -1:
                            middle.append(message[_end:i+1])
                        _start = i
                    count += 1
                elif ch == '}':
                    count -= 1
                    if count == 0:
                        _end = i
                        _list.append(message[_start:_end+1])
                        remain = message[_end+1:-1]
                        if len(remain) > 0:
                            remain = remain.strip('\n')
                            remain = remain.strip(' ')
            if len(_list) > 0:
                _ret = 0
            elif _start != -1:
                _ret = 1
            else:
                _ret = -1
        return _ret, _list, remain, middle
          
    def onlineProcessSocket(self):
        if self.tasker.empty() is False:
            uid = self.tasker.get()
            self.threadLock.acquire()
            processSocket = self.sockets[uid]
            self.threadLock.release()
            if len(self.largeBuffer) > 0:
                if "process_parameters_address" in processSocket.inputJson:
                    size = int(processSocket.inputJson["process_parameters_address"])
                    buffer = self.largeBuffer[0:size]
                    self.largeBuffer = self.largeBuffer[size:-1]
                    inStream = QDataStream(QByteArray.fromBase64(buffer))
                    inStream >> processSocket.inputObject
                if "process_images" in processSocket.inputJson:
                    inputNode = processSocket.inputJson["process_images"]
                    for key in inputNode.keys():
                        size = int(inputNode[key])
                        buffer = self.largeBuffer[0:size]
                        self.largeBuffer = self.largeBuffer[size:-1]
                        image = QImage()
                        if image.loadFromData(QByteArray.fromBase64(buffer)):
                            processSocket.inputImage[key] = image
                        else:
                            processSocket.inputImage[key] = None
                if "process_parameters_address" in processSocket.inputJson:
                    del processSocket.inputJson["process_parameters_address"]   
                if "process_images" in processSocket.inputJson:
                    del processSocket.inputJson["process_images"] 
                if "process_command" in processSocket.inputJson:     
                    processSocket.message = processSocket.inputJson["process_command"]
                else:
                    processSocket.message = "unknow"
                processSocket.channel = '1'
                processSocket.parent = self
                if self.process is not None:
                    self.process(processSocket)
          
    def processSocketJson(self, _socket:json):
        #print(_socket)
        if "process_socket_uid" in _socket:
            uid = _socket["process_socket_uid"]
            if 'process_mode' in _socket:
                mode = _socket["process_mode"]
                if mode == "execute":
                    inputJson = None
                    inputImage = {}
                    inputObject = {}
                    self.bufferSize = 0
                    if 'process_parameters_address' in _socket:
                        if self.online is False:
                            sharedMemory = SharedMemory(_socket["process_parameters_address"])
                            inputObject = sharedMemory.getObjectBuffer()
                        else:
                            self.bufferSize += int(_socket["process_parameters_address"])
                    if 'process_images' in _socket:
                        if self.online is False:
                            outputNode = _socket["process_images"]
                            for key in outputNode.keys():
                                sharedMemory = SharedMemory(outputNode[key])
                                inputImage[key] = sharedMemory.getImageBuffer()
                        else:
                            outputNode = _socket["process_images"]
                            for key in outputNode.keys():
                                self.bufferSize += int(outputNode[key])
                        
                    inputJson = _socket
                    
                    if self.online is False:
                        if 'process_parameters_address' in _socket:
                            del _socket["process_parameters_address"]
                        if 'process_images' in _socket:
                            del _socket["process_images"]
                    if self.online is True and self.bufferSize > 0:
                        self.startReceive = True
                        processSocket = ProcessSocket(uid)
                        processSocket.inputJson = inputJson
                        self.threadLock.acquire()
                        self.sockets[uid] = processSocket
                        self.threadLock.release()
                        self.tasker.put(uid)
                        #print(self.sockets.keys())
                    else:
                        processSocket = ProcessSocket(uid)
                        processSocket.inputJson = inputJson
                        processSocket.inputImage = inputImage
                        processSocket.inputObject = inputObject
                        processSocket.message = _socket["process_command"]
                        processSocket.channel = "1"
                        if self.process is not None:
                            self.process(processSocket)
                elif mode == "reply":
                    if uid in self.sockets.keys():
                        self.threadLock.acquire()
                        processSocket = self.sockets[uid]
                        self.threadLock.release()
                        processSocket.outputJson = _socket
                        if self.online is True:
                            self.bufferSize = 0
                            if "process_parameters_address" in _socket:
                                self.bufferSize += int(_socket["process_parameters_address"])
                            if "process_images" in _socket:
                                outputNode = _socket["process_images"]
                                for key in outputNode.keys():
                                    self.bufferSize += int(outputNode[key])
                            if "process_mode" in processSocket.outputJson:
                                del processSocket.outputJson["process_mode"]
                            if "process_command" in processSocket.outputJson:
                                del processSocket.outputJson["process_command"]
                            if self.bufferSize > 0:
                                self.startReceive = True
                                return
                        else:
                            processSocket.OutputParamFromSharedMemory()
                            if "process_socket_uid" in processSocket.outputJson:
                                del processSocket.outputJson["process_socket_uid"]
                            if "process_mode" in processSocket.outputJson:
                                del processSocket.outputJson["process_mode"]
                            if "process_command" in processSocket.outputJson:
                                del processSocket.outputJson["process_command"]
                            if "process_parameters_address" in processSocket.outputJson:
                                del processSocket.outputJson["process_parameters_address"]
                            if "process_images" in processSocket.outputJson:
                                del processSocket.outputJson["process_images"]
                        reply = {}
                        reply["process_socket_uid"] = uid
                        reply["process_mode"] = "replyFinish"
                        self.client_socket.send(json.dumps(reply).encode("utf-8"))
                    pass
                elif mode == "request":
                    self.replyJson = _socket
                    if self.request is not None:
                        self.request(_socket, mode)
                elif mode == "replyFinish":
                    pass
            elif 'process_command' in _socket:
                if _socket["process_command"] == "ConnectedState" and _socket["status"] == "online":
                    self.online = True
                elif _socket["process_command"] == "heartBeat" and _socket["status"] == "checkProcessIsValid":
                    self.client_socket.send(json.dumps(_socket).encode("utf-8"))
                elif self.online is True and _socket["process_command"] == "sendFinished" and _socket["status"] == "end":
                    uid = _socket["uid"]
                    if "head" in _socket:
                        if _socket["head"] == "execute":
                            self.threadLock.acquire()
                            processSocket = self.sockets[uid]
                            del self.sockets[uid]
                            self.threadLock.release()
                            if len(self.largeBuffer) > 0:
                                if "process_parameters_address" in processSocket.inputJson:
                                    size = int(processSocket.inputJson["process_parameters_address"])
                                    buffer = self.largeBuffer[0:size]
                                    self.largeBuffer = self.largeBuffer[size:-1]
                                    inStream = QDataStream(QByteArray.fromBase64(buffer))
                                    inStream >> processSocket.inputObject
                                if "process_images" in processSocket.inputJson:
                                    inputNode = processSocket.inputJson["process_images"]
                                    for key in inputNode.keys():
                                        size = int(inputNode[key])
                                        buffer = self.largeBuffer[0:size]
                                        self.largeBuffer = self.largeBuffer[size:-1]
                                        image = QImage()
                                        if image.loadFromData(QByteArray.fromBase64(buffer)):
                                            processSocket.inputImage[key] = image
                                        else:
                                            processSocket.inputImage[key] = None
                                if "process_parameters_address" in processSocket.inputJson:
                                    del processSocket.inputJson["process_parameters_address"]   
                                if "process_images" in processSocket.inputJson:
                                    del processSocket.inputJson["process_images"] 
                                if "process_command" in processSocket.inputJson:     
                                    processSocket.message = processSocket.inputJson["process_command"]
                                else:
                                    processSocket.message = "unknow"
                                processSocket.channel = '1'
                                processSocket.parent = self
                                if self.process is not None:
                                    self.process(processSocket)
                        elif _socket["head"] == "reply":
                            self.threadLock.acquire()
                            processSocket = self.sockets[uid]
                            self.threadLock.release()
                            if len(self.largeBuffer) > 0:
                                if "process_parameters_address" in processSocket.outputJson:
                                    size = int(processSocket.outputJson["process_parameters_address"])
                                    buffer = self.largeBuffer[0:size]
                                    self.largeBuffer = self.largeBuffer[size:-1]
                                    inStream = QDataStream(QByteArray.fromBase64(buffer))
                                    inStream >> processSocket.outputObject
                                if "process_images" in processSocket.outputJson:
                                    outputNode = processSocket.outputJson["process_images"]
                                    for key in outputNode.keys():
                                        size = int(outputNode[key])
                                    buffer = self.largeBuffer[0:size]
                                    self.largeBuffer = self.largeBuffer[size:-1]
                                    image = QImage()
                                    if image.loadFromData(QByteArray.fromBase64(buffer)):
                                        processSocket.outputImage[key] = image
                                    else:
                                        processSocket.outputImage[key] = None
                                reply = {}
                                reply["process_socket_uid"] = _socket["process_socket_uid"]
                                reply["process_mode"] = "replyFinish"
                                self.client_socket.send(json.dumps(reply).encode("utf-8"))
                            if "process_socket_uid" in processSocket.outputJson:     
                                del processSocket.outputJson["process_socket_uid"]
                            if "process_mode" in processSocket.outputJson:     
                                del processSocket.outputJson["process_mode"]
                            if "process_command" in processSocket.outputJson:     
                                del processSocket.outputJson["process_command"]
                            if "process_parameters_address" in processSocket.outputJson:     
                                del processSocket.outputJson["process_parameters_address"]
                            if "process_images" in processSocket.outputJson:     
                                del processSocket.outputJson["process_images"]
                            self.largeBuffer = ''
                            self.startReceive = False
                            self.bufferSize = 0
                            self.recordbufferSize = 0
            self.threadLock.acquire()
            if uid in self.iswait:
                self.iswait[uid] = False
            if uid in self.events:
                with self.events[uid]:
                    self.events[uid].notify()
            self.threadLock.release()
                            
    def replyTask(self, _socket:ProcessSocket):
        if _socket.inputJson is not None:
            _socket.lockOutput()
            bufferList = []
            for _key in _socket.inputJson.keys():
                _socket.outputJson[_key] = _socket.inputJson[_key]
            if len(_socket.outputObject) > 0:
                if self.online is False:
                    _key = str(id(self)) + '_' + _socket.uid + "_parameters"
                    sharedMemory = SharedMemory(_key)
                    if sharedMemory.setObjectBuffer(_socket.outputObject) is True:
                        self.sharedMemorys[_key] = sharedMemory
                        _socket.outputJson["process_parameters_address"] = _key
                else:
                    buffer = QByteArray()
                    stream = QDataStream(buffer, QIODevice.OpenModeFlag.Truncate | QIODevice.OpenModeFlag.WriteOnly)
                    stream << _socket.outputObject
                    bufferList.append(buffer.toBase64().data())
                    _socket.outputJson["process_parameters_address"] = str(len(bufferList[-1]))
            if len(_socket.outputImage) > 0:
                imageNode = {}
                for key in _socket.outputImage.keys():
                    _key = str(id(self)) + '_' + _socket.uid + "_" + key
                    if self.online is False:
                        if _key not in self.sharedMemorys:
                            self.sharedMemorys[_key] = SharedMemory(_key)
                        if self.sharedMemorys[_key].setImageBuffer(_socket.outputImage[key]):
                            imageNode[key] = _key
                    else:
                        image = _socket.outputImage[key]
                        imageData = QByteArray()
                        buffer = QBuffer(imageData)
                        image.save(buffer, "bmp")
                        bufferList.append(imageData.toBase64().data())
                        imageNode[key] = str(len(bufferList[-1]))
                _socket.outputJson["process_images"] = imageNode
            if self.client_socket is not None:
                _socket.outputJson["process_mode"] = "reply"
                if self.online and len(bufferList) > 0:
                    _socket.outputJson["process_largeSocket"] = True
                else:
                    _socket.outputJson["process_largeSocket"] = False
                self.client_socket.send(json.dumps(_socket.outputJson).encode("utf-8"))
                if self.online:
                    for buffer in bufferList:
                        self.client_socket.send(buffer)
                    msg = {}
                    msg["status"] = "end"
                    msg["head"] = "reply"
                    msg["uid"] = _socket.uid
                    msg["process_command"] = "sendFinished"
                    msg["process_socket_uid"] = QUuid.createUuid().toString()
                    self.client_socket.send(json.dumps(msg).encode("utf-8"))
            _socket.unlockOutput()
      
    def execute(self, _socket:ProcessSocket, timeOut:int = 0) -> bool:
        try:
            bufferList = []
            _socket.inputJson["process_command"] = _socket.message
            _socket.inputJson["process_socket_uid"] = _socket.uid
            _json = _socket.inputJson
            if self.online:
                if len(_socket.inputObject) > 0:
                    buffer = QByteArray()
                    stream = QDataStream(buffer, QIODevice.OpenModeFlag.Truncate | QIODevice.OpenModeFlag.WriteOnly)
                    stream << _socket.inputObject
                    bufferList.append(buffer.toBase64().data())
                    _json["process_parameters_address"] = str(len(bufferList[-1]))
                if len(_socket.inputImage) > 0:
                    imageNode = {}
                    for key in _socket.inputImage.keys():
                        image = _socket.inputImage[key]
                        imageData = QByteArray()
                        buffer = QBuffer(imageData)
                        image.save(buffer, "bmp")
                        bufferList.append(imageData.toBase64().data())
                        imageNode[key] = str(len(bufferList[-1]))
                    _json["process_images"] = imageNode
            else:
                _socket.InputParamToSharedMemory()
                _json["process_mode"] = "execute"
                if self.online and len(bufferList) > 0:
                    _json["process_largeSocket"] = True
                else:
                    _json["process_largeSocket"] = False
                self.client_socket.send(json.dumps(_json).encode('utf-8'))
                if self.online:
                    for _buffer in bufferList:
                        self.client_socket.send(_buffer)
                    msg = {}
                    msg["status"] = "end"
                    msg["head"] = "execute"
                    msg["uid"] = _socket.uid
                    msg["process_command"] = "sendFinished"
                    msg["process_socket_uid"] = QUuid.createUuid().toString()
                    self.client_socket.send(json.dumps(msg).encode("utf-8"))
                _event = threading.Condition()
                self.threadLock.acquire()
                self.iswait[_socket.uid] = True
                self.events[_socket.uid] = _event
                self.sockets[_socket.uid] = _socket
                self.threadLock.release()
                with _event:
                    ret = _event.wait(timeout=timeOut/1000.0)
                self.threadLock.acquire()
                del self.iswait[_socket.uid]
                del self.events[_socket.uid]
                del self.sockets[_socket.uid]
                del _event
                self.threadLock.release()
                return ret
        except Exception as e:
            traceback.print_exc()
        return False
        
    def _request(self, cmd:str, timeOut:int = 0) -> dict:
        retJson = {}
        msg = {}
        msg["process_command"] = cmd
        uid = QUuid.createUuid().toString()
        msg["process_socket_uid"] = uid
        msg["process_mode"] = "request"
        try:
            self.client_socket.send(json.dumps(msg).encode("utf-8"))
            
            _event = threading.Condition()
            self.threadLock.acquire()
            self.events[uid] = _event
            self.threadLock.release()
            with _event:
                ret = _event.wait(timeout=timeOut)
            self.threadLock.acquire()
            del self.sockets[uid]
            del _event
            if ret:
                retJson = json.loads(self.replyJson)
            self.threadLock.release()
        except Exception as e:
            traceback.print_exc()
        return retJson
        
    def releaseSharedMem(self):
        self.sharedMemorys = {}

    def is_connected(self) -> bool:
        if self.client_socket is not None:
            try:
                self.client_socket.send(b'')
                return True
            except socket.error:
                pass
        return False
    
class Executor:
    def __init__(self, url, args, env, host, port):
        self.url_ = url
        self.args_ = args
        self.env_ = env
        self.host_ = host
        self.port_ = port
        
        self.pid_ = 0
        self.client_socket_ = None
        self.exitLoop_ = False
        self.watcher_thread_ = None
        self.client = None
        
    def __del__(self):
        self.stop()
        
    def start(self):
        if self.pid_ == 0:
            # Start the process in a detached mode
            ret, self.pid_= QProcess.startDetached(self.url_, self.args_, self.env_)
            if ret:
                print(f"Process started successfully with PID: {self.pid_}")
            else:
                print("Failed to start the process.")
                return None
            
            if ret:
                count = 0
                while count < 10:
                    try:
                        self.client_socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client_socket_.connect((self.host_, self.port_))
                        self.watcher_thread_ = threading.Thread(target=self.__watcher)
                        self.watcher_thread_.start()
                        self.client = Client(self.client_socket_)
                        return self.client
                    except socket.error as e:
                        print(f"Connection error: {e}")
                        time.sleep(1)
                    finally:
                        count += 1
                if count == 10:
                    print("Failed to connect to the process.")
                    return None      
        
    def stop(self):
        if self.watcher_thread_ is not None:
            self.exitLoop_ = True
            self.watcher_thread_.join()
            self.watcher_thread_ = None
        if self.client_socket_ is not None:
            self.client_socket_.close()
        if self.pid_ != 0:
            os.kill(self.pid_, signal.SIGTERM)
            self.pid_ = 0
        if self.client is not None:
            self.client.stop()
            
    def is_connected(self) -> bool:
        if self.client is not None and self.pid_ != 0:
            return self.client.is_connected()
        return False
            
    def __watcher(self):
        self.exitLoop_ = False
        while self.exitLoop_ is False:
            try:
                if self.pid_ != 0:
                    if not psutil.pid_exists(self.pid_):
                        if self.client_socket_ is not None:
                            self.client_socket_.close()
                        print("Process is no longer running.")
                        ret, self.pid_ = QProcess.startDetached(url, args, env)
                        if ret:
                            print(f"Process started successfully with PID: {self.pid_}")
                        else:
                            print("Failed to start the process.")
                            break
                        
                        if ret:
                            count = 0
                            while count < 10:
                                try:
                                    self.client_socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    self.client_socket_.connect((self.host_, self.port_))
                                    if self.client is not None:
                                        self.client.client_socket = self.client_socket_
                                        self.client.start()
                                        break
                                except socket.error as e:
                                    print(f"Connection error: {e}")
                                    time.sleep(1)
                                finally:
                                    count += 1
                            if count == 10:
                                print("Failed to connect to the process.")
                                break   
            except Exception as e:
                break
            time.sleep(1)

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QWidget
    import threading
    
    app = QApplication(sys.argv)
    widget = QWidget()
    widget.show()    

    ip = '127.0.0.1'
    port = 1234
    url = r"D:\AIProgram\dist\AITest\AITest.exe"
    args = ["/ip", ip, '/port', str(port), '/display','True','/weights','D:/AIProgram/AIModels/yolov8s-seg.pt'] 
    env = r'D:\AIProgram\dist\AITest'

    # # Initialize the Client
    execuor = Executor(url, args, env, ip, port)
    
    exitLoop = False
    def loop():
        client = execuor.start()
        # Create a ProcessSocket with a unique ID
        process_socket = ProcessSocket(uid="unique_process_id")

        image = QImage(r'D:\AIProgram\bus.jpg')
        # Set input parameters
        # process_socket.inputJson = {"param1": "value1", "param2": "value2"}
        process_socket.inputImage["image"] = image
        
        while exitLoop is False:
            try:
                if not client.is_connected():
                    time.sleep(1)
                    continue
                # Execute the process with a timeout of 10 seconds
                success = client.execute(process_socket, timeOut=1000)

                if success:
                    print("Process executed successfully.")
                    # print("Output ", process_socket.outputJson)
                    # with open('outputJson.json', 'w', encoding='utf-8') as json_file:
                        # json.dump(process_socket.outputJson, json_file, ensure_ascii=False, indent=4)
                else:
                    print("Process execution failed or timed out.")
            except Exception as e:
                print(f"An error occurred: {e}")
                break
            
    th = threading.Thread(target=loop)
    th.start()
    
    app.exec()
    exitLoop = True
    th.join()
    execuor.stop()