import os
import time
import queue
import socket
import json
import sys
import traceback
import threading
import signal
import psutil
from multiprocessing import Lock, shared_memory
import pickle
import numpy as np
from typing import Callable, Optional
import subprocess
import uuid

class SharedMemory:
    def __init__(self, key: str):
        self.key = key
        self.shm = None
        self.lock = Lock()

    def __del__(self):
        if self.shm:
            self.shm.close()
            self.shm.unlink()
            self.shm = None

    def __set_buffer(self, val) -> bool:
        if val is None:
            return False
        
        if self.shm:
            self.shm.close()
            self.shm.unlink()
            self.shm = None

        data = pickle.dumps(val)
        try:
            self.shm = shared_memory.SharedMemory(name=self.key, create=True, size=len(data))
        except FileNotFoundError:
            print(f"Shared memory {self.key} already exists.")
            return False

        with self.lock:
            self.shm.buf[:len(data)] = data

        return True
    
    def __get_buffer(self):
        obj = None
        try:
            shm = shared_memory.SharedMemory(name=self.key)
            with self.lock:  # 使用锁保护共享资源
                data = bytes(shm.buf[:]).rstrip(b'\x00')
                obj = pickle.loads(data)
        except FileNotFoundError:
            print(f"Shared memory {self.key} not found.")
        return obj
    
    def setObjectBuffer(self, obj: dict) -> bool:
        if obj is None:
            return False
        return self.__set_buffer(obj)

    def getObjectBuffer(self):
        return self.__get_buffer()

    def setImageBuffer(self, image: np.ndarray) -> bool:
        if image is None:
            return False
        
        try:
            header = {'shape': image.shape, 'dtype': image.dtype}
            header_data = pickle.dumps(header)
            len_header = len(header_data)
            if self.shm is None:
                self.shm = shared_memory.SharedMemory(name=self.key, create=True, size=image.nbytes + len_header + 4)
            else:
                if self.shm.size < image.nbytes + len_header + 4:
                    self.shm.close()
                    self.shm.unlink()
                    self.shm = shared_memory.SharedMemory(name=self.key, create=True, size=image.nbytes + len_header + 4)
        except Exception as e:
            print(f"Error creating shared memory {self.key}: {e}")
            return False

        with self.lock:
            self.shm.buf[:4] = len_header.to_bytes(4, 'little')
            self.shm.buf[4:4 + len_header] = header_data
            shared_array = np.ndarray(image.shape, dtype=image.dtype, buffer=self.shm.buf[4 + len(header_data):])
            np.copyto(shared_array, image)  # 将数据复制到共享内存
            
        return True
        
    def getImageBuffer(self) -> np.ndarray:
        image = None
        try:
            shm = shared_memory.SharedMemory(name=self.key)
            with self.lock:  # 使用锁保护共享资源
                len_header = int.from_bytes(shm.buf[:4], byteorder='little')
                header = pickle.loads(bytes(shm.buf[4:4 + len_header]).rstrip(b'\x00'))
                image = np.ndarray(header.get('shape'), dtype=header.get('dtype'), buffer=shm.buf[4 + len_header:]).copy()
            shm.unlink()
        except Exception as e:
            print(f"Error reading shared memory {self.key}: {e}")
        return image
     
class ProcessSocket:
    def __init__(self, uid:str):
        self.uid = uid
        
        self.inputJson = {}
        self.inputImage:dict[str, np.ndarray] = {}
        self.inputObject = {}

        self.outputJson = {}
        self.outputImage:dict[str, np.ndarray] = {}
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
    
class Client:
    def __init__(self, client_socket:socket.socket = None, process:Optional[Callable[[ProcessSocket], None]] = None, request:Optional[Callable[[dict, str], None]] = None):
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
        
        self.tasker = queue.Queue()
        
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
                    try:
                        processSocket.inputObject = pickle.loads(buffer.rstrip(b'\x00'))
                    except KeyError:
                        pass
                if "process_images" in processSocket.inputJson:
                    inputNode = processSocket.inputJson["process_images"]
                    for key in inputNode.keys():
                        size = int(inputNode[key])
                        buffer = self.largeBuffer[0:size]
                        self.largeBuffer = self.largeBuffer[size:-1]
                        try:
                            processSocket.inputImage[key] = pickle.loads(buffer.rstrip(b'\x00'))
                        except KeyError:
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
                                    try:
                                        processSocket.inputObject = pickle.loads(buffer.rstrip(b'\x00'))
                                    except KeyError:
                                        pass
                                if "process_images" in processSocket.inputJson:
                                    inputNode = processSocket.inputJson["process_images"]
                                    for key in inputNode.keys():
                                        size = int(inputNode[key])
                                        buffer = self.largeBuffer[0:size]
                                        self.largeBuffer = self.largeBuffer[size:-1]
                                        try:
                                            processSocket.inputImage[key] = pickle.loads(buffer.rstrip(b'\x00'))
                                        except KeyError:
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
                                    try:
                                        processSocket.inputObject = pickle.loads(buffer.rstrip(b'\x00'))
                                    except KeyError:
                                        pass
                                if "process_images" in processSocket.outputJson:
                                    outputNode = processSocket.outputJson["process_images"]
                                    for key in outputNode.keys():
                                        size = int(outputNode[key])
                                    buffer = self.largeBuffer[0:size]
                                    self.largeBuffer = self.largeBuffer[size:-1]
                                    try:
                                        processSocket.inputImage[key] = pickle.loads(buffer.rstrip(b'\x00'))
                                    except KeyError:
                                        processSocket.inputImage[key] = None
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
                    buffer = pickle.dumps(_socket.outputObject)
                    bufferList.append(buffer)
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
                        buffer = pickle.dumps(image)
                        bufferList.append(buffer)
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
                    msg["process_socket_uid"] = uuid.uuid4().hex
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
                    buffer = pickle.dumps(_socket.inputObject)
                    bufferList.append(buffer)
                    _json["process_parameters_address"] = str(len(bufferList[-1]))
                if len(_socket.inputImage) > 0:
                    imageNode = {}
                    for key in _socket.inputImage.keys():
                        image = _socket.inputImage[key]
                        buffer = pickle.dumps(image)
                        bufferList.append(buffer)
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
                    msg["process_socket_uid"] = uuid.uuid4().hex
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
        uid = uuid.uuid4().hex
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
        
        self.try_connect_count = 10
        self.try_connect = True
        
    def __del__(self):
        self.stop()

    def start(self):
        if self.pid_ == 0:
            try:
                process = subprocess.Popen(
                    [self.url_] + self.args_,  # 命令和参数
                    cwd=self.env_,  # 设置工作目录
                    start_new_session=True  # 分离进程
                )
                self.pid_ = process.pid
                print(f"Process started successfully with PID: {self.pid_}")
            except Exception as e:
                print(f"Failed to start process: {e}")
                return None

            count = 0
            self.try_connect = True
            while count < self.try_connect_count and self.try_connect is True:
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
        self.try_connect = False
        if self.watcher_thread_ is not None:
            self.exitLoop_ = True
            self.watcher_thread_.join()
            self.watcher_thread_ = None
        if self.client_socket_ is not None:
            self.client_socket_.close()
        if self.pid_ != 0:
            try:
                os.kill(self.pid_, signal.SIGTERM)
            except OSError:
                print(f"Process {self.pid_} does not exist.")
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
                        try:
                            process = subprocess.Popen(
                                [self.url_] + self.args_,  # 命令和参数
                                cwd=self.env_,  # 设置工作目录
                                start_new_session=True  # 分离进程
                            )
                            self.pid_ = process.pid
                            print(f"Process started successfully with PID: {self.pid_}")
                        except Exception as e:
                            print(f"Failed to start process: {e}")
                            break
                    
                        count = 0
                        self.try_connect = True
                        while count < self.try_connect_count and self.try_connect is True:
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
    from PySide6.QtGui import QImage
    import threading
    import cv2 
    from ProcessQt import ndarray_to_qimage, qimage_to_ndarray
    
    app = QApplication(sys.argv)
    widget = QWidget()
    widget.show()    

    ip = '127.0.0.1'
    port = 1234
    url = r"D:\AIProgram\AiDetect.exe"
    args = [r'D:\Python\FramePro\SmokeDetection\deeplearn\AITest.py', "/ip", ip, '/port', str(port), '/display','True','/weights',r'D:\Python\FramePro\SmokeDetection\deeplearn\data\model1.pth'] 
    env = r'D:\Python\FramePro\SmokeDetection\deeplearn'

    # # Initialize the Client
    execuor = Executor(url, args, env, ip, port)
    
    exitLoop = False
    def loop():
        client = execuor.start()
        # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # client_socket.connect((ip, port))
        # client = Client(client_socket)
        # Create a ProcessSocket with a unique ID
        process_socket = ProcessSocket(uid="unique_process_id")

        image = QImage(r'D:\Python\FramePro\SmokeDetection\deeplearn\results\pred_Image_20250815122201276.jpg')
        # Set input parameters
        # process_socket.inputJson = {"param1": "value1", "param2": "value2"}
        process_socket.inputImage["image"] = qimage_to_ndarray(image)
        
        while exitLoop is False:
            try:
                if not client.is_connected():
                    time.sleep(1)
                    continue
                # Execute the process with a timeout of 10 seconds
                success = client.execute(process_socket, timeOut=5000)

                if success:
                    print("Process executed successfully.")
                    print("Output ", process_socket.outputJson)
                    # outImage = process_socket.outputImage['image']
                    # cv2.namedWindow("Output Image", cv2.WINDOW_NORMAL)
                    # cv2.imshow("Output Image", outImage)
                    # cv2.waitKey()
                    # with open('outputJson.json', 'w', encoding='utf-8') as json_file:
                        # json.dump(process_socket.outputJson, json_file, ensure_ascii=False, indent=4)
                else:
                    print("Process execution failed or timed out.")
            except Exception as e:
                print(f"An error occurred: {e}")
                break
            
        # client_socket.close()
        # client.stop()
            
    th = threading.Thread(target=loop)
    th.start()
    
    app.exec()
    exitLoop = True
    th.join()
    execuor.stop()