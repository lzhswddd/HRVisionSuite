# -*- coding: utf-8 -*-
import json
import base64
from threading import Thread, RLock
import threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os
import pickle
import argparse
import sys
import traceback
import uuid
import types
import time
import tempfile

import atexit as _atexit
import multiprocessing
import multiprocessing.shared_memory as _shm
import multiprocessing.synchronize
from typing import Generic, TypeVar

# 公司标记（写死）：授权码 company 字段必须匹配
LICENSE_COMPANY = "英锐捷（厦门）信息科技有限公司"


def _check_license(project=""):
    """认证入口（公司写死；项目名由 main --project 传入，空 = 不锁项目）。"""
    try:
        from .HRAuth import check_license
    except ImportError:
        from HRAuth import check_license
    # project 空 = 不锁项目（只锁公司）；非空 = 项目锁（--project 传入）
    return check_license(exit_on_fail=False, company=LICENSE_COMPANY,
                         project=project)

class _Node:
    def __init__(self):
        self.id = ""
        self.type = ""
        self.title = ""
        self.content = ""
        self.isRunning = False
        self.isSubthread = False
        self.isNormal = False
        self.isSwapped = False
        self.file_path = None

        self.next_ids = {}
        self.prev_id = []

        self.code = None
        self.source = None          # 节点源码（线程模式 import 重写用）
        self._rewritten = {}        # __thdata_module__ key -> 重写后的 code 对象

    def run(self, _globals, _locals = {}):
        __return = 0
        if self.code and self.isRunning:
            _globals["__file__"] = os.path.abspath(self.file_path)
            # _globals["__package__"] = os.path.dirname(self.file_path)
            code = self.code
            thd_key = _globals.get('__thdata_module__')
            if thd_key and self.source:
                # 线程模式多实例隔离：把节点源码里的
                #   from <flow>.ThreadGlobalData import *
                # 重写为 from <flow>.<uuid>.ThreadGlobalData import *
                # （sys.modules 中该 key 是当前执行器实例的 ThreadGlobalData）
                code = self._rewritten.get(thd_key)
                if code is None:
                    import re as _re
                    src2 = _re.sub(
                        r'from\s+([\w\.]+)\.ThreadGlobalData\s+import\s+\*',
                        lambda m: 'from %s.%s.ThreadGlobalData import *'
                                  % (m.group(1), thd_key.split('.')[1]),
                        self.source)
                    code = compile(src2, self.file_path, 'exec')
                    self._rewritten[thd_key] = code
            try:
                exec(code, _globals, _globals)
            except Exception as e:
                if "return" in e.args:
                    __return = e.args[1]
                else:
                    raise e
                #     traceback.print_exc()
                #     return ""
        if len(self.next_ids) > 0 and __return >= 0:
            if str(__return+1) in self.next_ids:
                return self.next_ids[str(__return+1)]
            else: 
                return ""
        elif len(self.next_ids) == 0:
            return ""
        elif __return < 0:
            return ""

class _Process:
    def __init__(self):
        self.nodes:dict[str, _Node] = {}
        self.start_id = ''
        self.is_main = False
        self.localCode = None
        self.localCodePath = None

class ThreadExecutor:
    globalMap = {}
    lock = RLock()
    
    def __init__(self, process):
        super().__init__()
        self.uuid = uuid.uuid1().hex
        self.process:_Process = process
        self.pthread = None
        self.globalMap[self.uuid] = self
        self.running = False
        self.stop_flag = False
    
    def run(self, _globals, _locals = {}, is_thread = False, **kwargs):
        if is_thread:
            self.pthread = Thread(target=self.run_main, args=(_globals, _locals), kwargs=kwargs)
            self.pthread.start()
        else:
            self.run_main(_globals, _locals, **kwargs)
    
    def run_main(self, _globals, _locals = {}, **kwargs):
        self.running = False
        self.stop_flag = False
        if self.process.start_id in self.process.nodes:
            self.running = True
            try:
                if self.pthread is not None:
                    if self.process.localCodePath and self.process.localCode:
                        # 线程模式多实例隔离：ThreadGlobalData 模块 key 按执行器实例唯一
                        # （同流程多实例并发时，sys.modules 不被彼此覆盖），节点代码的
                        # from <flow>.ThreadGlobalData import * 由 _Node.run 重写为
                        # from <flow>.<uuid>.ThreadGlobalData import *。
                        threadDataKey = self.process.localCodePath + '._' + self.uuid + '.ThreadGlobalData'
                        dynamic_module = types.ModuleType(threadDataKey)
                        exec(self.process.localCode, dynamic_module.__dict__)
                        sys.modules[threadDataKey] = dynamic_module
                        thd = getattr(dynamic_module, 'thData', None)
                        if thd is not None:
                            for _k, _v in kwargs.items():
                                setattr(thd, _k, _v)
                        _globals['thData'] = thd
                        _globals['__thdata_module__'] = threadDataKey
                now_node = self.process.nodes[self.process.start_id]
                while now_node and not self.stop_flag:
                    next_id = now_node.run(_globals, _locals)
                    if next_id != "":
                        now_node = self.process.nodes[next_id]
                    else:
                        break
            except Exception as e:
                traceback.print_exc()
        if self.pthread:
            self.pthread = None
        self.lock.acquire()
        self.globalMap.pop(self.uuid, None)
        self.lock.release()
        self.running = False
        
    def stop(self):
        if self.pthread and self.pthread.is_alive():
            self.stop_flag = True
            self.pthread.join()
        self.running = False
        self.lock.acquire()
        self.globalMap.pop(self.uuid, None)
        self.lock.release()

    def isAlive(self):
        return self.running

class ThreadStartor:
    def __init__(self, getProcess, gData, priority=None):
        self.getProcess = getProcess
        self.gData = gData
        self.priority = priority   # 线程优先级：idle/lowest/below/normal/above/highest/time_critical

    def start(self, is_thread = True, **kwargs):
        if is_thread:
            locals__ = {}
            locals__['gData'] = self.gData
            executor = ThreadExecutor(self.getProcess())
            executor.run(_globals = locals__, _locals = locals__, is_thread = is_thread, **kwargs)
        else:
            executor = ThreadExecutor(self.getProcess())
            executor.run(_globals = globals(), _locals = globals(), is_thread = is_thread, **kwargs)
        if is_thread and self.priority and executor.pthread is not None:
            _apply_thread_priority(executor.pthread.ident, self.priority)
        return executor

def _collect_signal_names(gData):
    """从 ProgramGlobalData 的 signal_instance 收集信号名（进程模式转发白名单）。"""
    sig = getattr(gData, 'signal_instance', None)
    if sig is None:
        module = sys.modules.get("ProgramGlobalData")
        if module is not None:
            sig = getattr(module, 'signal_instance', None)
    if sig is None:
        return []
    names = []
    for n in dir(sig):
        if n.startswith('_'):
            continue
        try:
            attr = getattr(sig, n)
            if 'Signal' in type(attr).__name__:
                names.append(n)
        except Exception:
            pass
    return names


class _Controller:
    def __init__(self, dir_path, main_process_name):
        self.dirPath = dir_path
        self.main_process_name = main_process_name
        
    def read_and_decode_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            base64_string = file.read()
            
        if base64_string == '':
            return None
    
        decoded_bytes = base64.b64decode(base64_string)
        return decoded_bytes.decode()
        
    def run(self):
        # if not _check_license():
        #     return
        cleanup_all_segments()   # 启动时清理上次强杀残留的共享内存段
        
        filePaths = []
        for root, dirs, files in os.walk(self.dirPath):
            for file in files:
                if file.endswith(".ndjs"):
                    filePath = os.path.join(root, file)
                    filePaths.append(filePath)
        if len(filePaths) == 0:
            print("No .ndjs file found in the directory.")
            return
        
        decrypted_data = []
        for filePath in filePaths:
            file_contents = _Controller.read_and_decode_file(filePath)
            dir_path = os.path.dirname(os.path.abspath(filePath))
            key_hash = 'secretkey-hr1234'.encode('utf-8')
            parts = file_contents.split("||")
            if len(parts) != 2:
                print("Invalid file format")
                return
            iv = base64.b64decode(parts[0])
            ciphertext = base64.b64decode(parts[1])
            cipher = AES.new(key_hash, AES.MODE_CBC, iv)
            decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
            decrypted_data_ = json.loads(decrypted_bytes.decode('utf-8'))
            decrypted_data.extend(decrypted_data_)
        
        codeDict = {}
            
        # with open("decrypted_flow.json", 'w', encoding='utf-8') as file:
            # json.dump(decrypted_data, file, ensure_ascii=False, indent=4)
            
        sys.path.append(os.path.abspath(self.dirPath))  
        
        dir_path = self.dirPath
        program_dir = dir_path
        
        main_process = None
        process_instance:dict[str, _Process] = {}
        for flow in decrypted_data:
            flowID = flow['flowID']
            is_main = flowID == self.main_process_name
            process = _Process()
            process.is_main = is_main
            process_instance[flowID] = process
            if is_main:
                main_process = process
                process.is_main = True
            
        os.chdir(dir_path)
        sys.path.append(dir_path)
        
        globals_ = {}
        locals_ = {}
        globalDataCode = os.path.join(program_dir, "ProgramGlobalData.py")
        if os.path.exists(globalDataCode):
            file_data = open(globalDataCode, encoding='utf-8').read()
            code = compile(file_data, globalDataCode, 'exec')
            module_name = "ProgramGlobalData"
            dynamic_module = types.ModuleType(module_name)
            exec(code, dynamic_module.__dict__)
            sys.modules[module_name] = dynamic_module
            relative = os.path.relpath(globalDataCode, start=os.getcwd())
            codeDict[relative] = file_data
            # exec(code, globals_, locals_)
            # exec('from ProgramGlobalData import *', globals_, locals_)

        gData = dynamic_module.gData
        locals_["gData"] = gData
        
        for flow in decrypted_data:
            flowID = flow['flowID']
            process = process_instance[flowID]
            
            for node in flow['nodes']:
                data = node['data']
                node_instance = _Node()
                node_instance.id = node['id']
                node_instance.type = node['type']
                node_instance.title = data['title']
                node_instance.content = (data['content'] if 'content' in data else "")
                node_instance.isRunning = (data['isRunning'] if 'isRunning' in data else False)
                node_instance.isSubthread = ('IsSubthread' in data and data['IsSubthread']) or False
                node_instance.isNormal = ('isNormal' in data and data['isNormal']) or False
                node_instance.isSwapped = ('isSwapped' in data and data['isSwapped']) or False
                codePath = os.path.join(program_dir, flowID, data['title'] + "_" + node['id'] + ".py")
                
                if os.path.exists(codePath):
                    file_data = open(codePath, encoding='utf-8').read()
                    node_instance.code = compile(file_data, codePath, 'exec')
                    node_instance.source = file_data
                    node_instance.file_path = codePath
                    relative = os.path.relpath(codePath, start=os.getcwd())
                    codeDict[relative] = file_data
                    
                process.nodes[node_instance.id] = node_instance
                
                if node_instance.type == 'StartNode':
                    process.start_id = node_instance.id
            
            for edge in flow['edges']:
                source = edge['source']
                target = edge['target']
                if source not in process.nodes or target not in process.nodes:
                    print("Invalid edge: ", source, target)
                    break
                if 'sourceHandle' in edge:
                    sourceHandle = edge['sourceHandle']
                else:
                    sourceHandle = "1"
                process.nodes[source].next_ids[sourceHandle] = target
                process.nodes[target].prev_id.append(source)
            
            # if process.is_main is False:
            threadDataCode = os.path.join(program_dir, flowID, "ThreadGlobalData.py")
            if os.path.exists(threadDataCode):
                file_data = open(threadDataCode, encoding='utf-8').read()
                code = compile(open(threadDataCode, encoding='utf-8').read(), threadDataCode, 'exec')
                process.localCode = code
                process.localCodePath = flowID
                relative = os.path.relpath(threadDataCode, start=os.getcwd())
                codeDict[relative] = file_data
  
            process_instance[flowID] = process
        
        for flowID in process_instance.keys():
            def __getProcess(flowID = flowID):
                return process_instance.get(flowID)
            gData.thCtrls[flowID] = ThreadStartor(__getProcess, gData)
            if not hasattr(gData, 'proCtrls'):
                gData.proCtrls = {}
            def __getProcProcess(flowID = flowID):
                return process_instance.get(flowID)
            gData.proCtrls[flowID] = ProcessStartor(
                __getProcProcess, gData, self.dirPath, self.main_process_name,
                signals=_collect_signal_names(gData))


        with open("ProgramCode.json", 'w', encoding='utf-8') as file:
            json.dump(codeDict, file, ensure_ascii=False, indent=4)
        
        _gloabals = locals_
        executor = ThreadExecutor(main_process)
        executor.run(_gloabals, is_thread = False)
    
    def run_release(self, codeConfig, project=""):
        if not _check_license(project):
            return
        if codeConfig:
            if codeConfig.endswith(".dat"):
                file_contents = _Controller.read_and_decode_file(codeConfig)
                key_hash = 'secretkey-hr1234'.encode('utf-8')
                parts = file_contents.split("||")
                if len(parts) != 2:
                    print("Invalid file format")
                    return
                iv = base64.b64decode(parts[0])
                ciphertext = base64.b64decode(parts[1])
                cipher = AES.new(key_hash, AES.MODE_CBC, iv)
                decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
                codeDict_ = json.loads(decrypted_bytes.decode('utf-8'))
                
            elif codeConfig.endswith(".json"):
                with open(codeConfig, 'r', encoding='utf-8') as file:
                    codeDict_ = json.load(file)
                
            if not codeDict_:
                print("Code configuration file is empty or invalid.")
                return
            
            codeDict = {}
            charset = os.path.sep
            for key, value in codeDict_.items():
                if isinstance(key, str):
                    if charset == "/":
                        key = key.replace("\\", charset)
                    elif charset == "\\":
                        key = key.replace("/", charset)
                codeDict[key] = value
                
            filePaths = []
            for root, dirs, files in os.walk(self.dirPath):
                for file in files:
                    if file.endswith(".ndjs"):
                        filePath = os.path.join(root, file)
                        filePaths.append(filePath)
            if len(filePaths) == 0:
                print("No .ndjs file found in the directory.")
                return
            
            decrypted_data = []
            for filePath in filePaths:
                file_contents = _Controller.read_and_decode_file(filePath)
                dir_path = os.path.dirname(os.path.abspath(filePath))
                key_hash = 'secretkey-hr1234'.encode('utf-8')
                parts = file_contents.split("||")
                if len(parts) != 2:
                    print("Invalid file format")
                    return
                iv = base64.b64decode(parts[0])
                ciphertext = base64.b64decode(parts[1])
                cipher = AES.new(key_hash, AES.MODE_CBC, iv)
                decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
                decrypted_data_ = json.loads(decrypted_bytes.decode('utf-8'))
                decrypted_data.extend(decrypted_data_)
                
            # with open("decrypted_flow.json", 'w', encoding='utf-8') as file:
                # json.dump(decrypted_data, file, ensure_ascii=False, indent=4)
                
            sys.path.append(os.path.abspath(self.dirPath))  
            
            dir_path = self.dirPath
            program_dir = dir_path
            
            main_process = None
            process_instance:dict[str, _Process] = {}
            for flow in decrypted_data:
                flowID = flow['flowID']
                is_main = flowID == self.main_process_name
                process = _Process()
                process.is_main = is_main
                process_instance[flowID] = process
                if is_main:
                    main_process = process
                    process.is_main = True
                
            os.chdir(dir_path)
            sys.path.append(dir_path)
            
            globals_ = {}
            locals_ = {}
            globalDataCode = os.path.join(program_dir, "ProgramGlobalData.py")
            relative = os.path.relpath(globalDataCode, start=os.getcwd())
            if relative in codeDict:
                file_data = codeDict[relative]
                code = compile(file_data, relative, 'exec')
                module_name = "ProgramGlobalData"
                dynamic_module = types.ModuleType(module_name)
                exec(code, dynamic_module.__dict__)
                sys.modules[module_name] = dynamic_module
                # exec(code, globals_, locals_)
                # exec('from ProgramGlobalData import *', globals_, locals_)

            gData = dynamic_module.gData
            locals_["gData"] = gData
            
            for flow in decrypted_data:
                flowID = flow['flowID']
                process = process_instance[flowID]
                
                for node in flow['nodes']:
                    data = node['data']
                    node_instance = _Node()
                    node_instance.id = node['id']
                    node_instance.type = node['type']
                    node_instance.title = data['title']
                    node_instance.content = (data['content'] if 'content' in data else "")
                    node_instance.isRunning = (data['isRunning'] if 'isRunning' in data else False)
                    node_instance.isSubthread = ('IsSubthread' in data and data['IsSubthread']) or False
                    node_instance.isNormal = ('isNormal' in data and data['isNormal']) or False
                    node_instance.isSwapped = ('isSwapped' in data and data['isSwapped']) or False
                    codePath = os.path.join(program_dir, flowID, data['title'] + "_" + node['id'] + ".py")
                    
                    relative = os.path.relpath(codePath, start=os.getcwd())
                    if relative in codeDict:
                        file_data = codeDict[relative]
                        node_instance.code = compile(file_data, relative, 'exec')
                        node_instance.source = file_data
                        node_instance.file_path = relative
                        
                    process.nodes[node_instance.id] = node_instance
                    
                    if node_instance.type == 'StartNode':
                        process.start_id = node_instance.id
                
                for edge in flow['edges']:
                    source = edge['source']
                    target = edge['target']
                    if source not in process.nodes or target not in process.nodes:
                        print("Invalid edge: ", source, target)
                        break
                    if 'sourceHandle' in edge:
                        sourceHandle = edge['sourceHandle']
                    else:
                        sourceHandle = "1"
                    process.nodes[source].next_ids[sourceHandle] = target
                    process.nodes[target].prev_id.append(source)
                
                # if process.is_main is False:
                threadDataCode = os.path.join(program_dir, flowID, "ThreadGlobalData.py")
                relative = os.path.relpath(threadDataCode, start=os.getcwd())
                if relative in codeDict:
                    file_data = codeDict[relative]
                    code = compile(file_data, relative, 'exec')
                    process.localCode = code
                    process.localCodePath = flowID
    
                process_instance[flowID] = process
            
            for flowID in process_instance.keys():
                def __getProcess(flowID = flowID):
                    return process_instance.get(flowID)
                gData.thCtrls[flowID] = ThreadStartor(__getProcess, gData)
                if not hasattr(gData, 'proCtrls'):
                    gData.proCtrls = {}
                def __getProcProcess(flowID = flowID):
                    return process_instance.get(flowID)
                gData.proCtrls[flowID] = ProcessStartor(
                    __getProcProcess, gData, self.dirPath, self.main_process_name,
                    signals=_collect_signal_names(gData),
                    codeDict=codeDict)


            # with open("ProgramCode.json", 'w', encoding='utf-8') as file:
                # json.dump(codeDict, file, ensure_ascii=False, indent=4)
            
            _globals = locals_
            executor = ThreadExecutor(main_process)
            executor.run(_globals, _globals, is_thread = False)
        else:
            print("Code configuration file not provided.")
            return

def main(flow=None, main_process="", code="", project=""):
    """框架入口：参数优先，缺省从 sys.argv 解析（--flow/--main/--code/--project）。

    Args:
        flow: Flow 目录（None 用 sys.argv --flow）
        main_process: 主流程名（默认 "main"）
        code: 发布版代码配置（.dat），非空走 run_release（含认证）
        project: 项目名（授权码项目锁，中文；空 = 不锁项目，仅公司锁）

    用法：
        main()                                  # 纯 sys.argv（HRStar.py 方式）
        main(flow="Flow", project="视觉检测项目")  # 代码直接传参
    """
    print('参数列表:', sys.argv)
    parser = argparse.ArgumentParser(description="Flow Controller")
    parser.add_argument("--flow", type=str, required=True, help="Path to the flow directory")
    parser.add_argument("--main", type=str, help="Name of the main process", default="main")
    parser.add_argument("--code", type=str, help="Path to the code configuration file", default="")
    parser.add_argument("--project", type=str, help="Project name (license project lock, Chinese ok)", default="")
    args = parser.parse_args()

    flow_path = flow or args.flow
    main_process_name = main_process or args.main
    
    if not os.path.exists(flow_path):
        print(f"Flow path '{flow_path}' does not exist.")
        sys.exit(1)
    
    controller = _Controller(flow_path, main_process_name)
    if code or args.code:
        controller.run_release(code or args.code, project=project or args.project)
    else:
        controller.run()

if __name__ == "__main__":
    main()


# ================= 进程模式（合并自 HRFlowControllerProcess.py） =================

_UserT = TypeVar("_UserT")



class GlobalDataBase(Generic[_UserT]):
    """流程框架系统数据基类。

    项目 ProgramGlobalData.py 的 GlobalData 应继承本类，获得系统字段的
    类型标注（IDE 可跳转/补全）。_UserT 为项目自定义 user 数据类型：
        from HRFlowControllerProcess import GlobalDataBase
        class GlobalData(GlobalDataBase[ProgramData]):
            def __init__(self):
                super().__init__()
                self.user = ProgramData()   # 类型即 ProgramData，IDE 可跳转

    系统字段（由框架 build_processes 填充）：
        thCtrls   线程流程控制器（ThreadStartor，原框架）
        proCtrls  进程流程控制器（ProcessStartor，本模块）
        exit_flag 全局退出标志（节点代码读取）
        user      项目自定义数据（子类指定类型）
    """

    thCtrls: "dict[str, ThreadStartor]"
    proCtrls: "dict[str, ProcessStartor]"
    exit_flag: bool
    user: _UserT

    def __init__(self):
        self.thCtrls = {}
        self.proCtrls = {}
        self.exit_flag = False
        self.user = None


class ThreadDataBase:
    """线程/进程数据基类（ThreadGlobalData.py 的 ThreadData 继承）。

    系统字段（由框架注入——ProcessStartor.start(**kwargs) 写入模块级 thData）：
        frame_name       共享内存帧缓冲名（_FrameBuffer，相机进程写/算法进程读）
        frame_event      帧就绪通知（multiprocessing.Event，相机 set / 算法 wait）
        frame_done_event 帧消费握手（multiprocessing.Event，算法 set / 相机 wait）
    项目自定义字段（prc_path/proc_name/vm_* 等）写在子类。

    用法：
        from HRFlowControllerProcess import ThreadDataBase
        class ThreadData(ThreadDataBase):
            def __init__(self):
                super().__init__()
                self.my_field = None
    """

    frame_name: "str | None"
    frame_event: "multiprocessing.synchronize.Event | None"
    frame_done_event: "multiprocessing.synchronize.Event | None"

    def __init__(self):
        self.frame_name = None
        self.frame_event = None
        self.frame_done_event = None


def _load_source(codeDict, codePath):
    """codeDict 优先（发布模式，key=相对路径）；否则从磁盘读。"""
    if codeDict is not None:
        relative = os.path.relpath(codePath, start=os.getcwd())
        return codeDict.get(relative)
    if os.path.exists(codePath):
        with open(codePath, encoding='utf-8') as f:
            return f.read()
    return None


def _decrypt_ndjs_file(filePath):
    """读取并解密单个 .ndjs（双重编码）→ 明文 JSON 列表。任何损坏抛 RuntimeError。"""
    try:
        file_contents = _Controller.read_and_decode_file(filePath)
        if file_contents is None:
            raise RuntimeError("Empty ndjs file: %s" % filePath)
        key_hash = ('secr' + 'etkey' + '-hr1' + '234').encode('utf-8')
        parts = file_contents.split("||")
        if len(parts) != 2:
            raise RuntimeError("Invalid file format: %s" % filePath)
        iv = base64.b64decode(parts[0])
        ciphertext = base64.b64decode(parts[1])
        cipher = AES.new(key_hash, AES.MODE_CBC, iv)
        decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return json.loads(decrypted_bytes.decode('utf-8'))
    except ValueError as e:
        raise RuntimeError("Invalid ndjs file %s: %s" % (filePath, e)) from e


def build_processes(dir_path, main_process_name, codeDict=None, startor_cls=None,
                    pro_startor_cls=None, process_signals=None):
    """扫描并解密 .ndjs → 建 _Process 图 → 加载 ProgramGlobalData → 注册控制器。

    实现复制自原 _Controller.run() 的构建段（原文件未修改）。
    codeDict: 发布模式下为源码字典（key=相对路径），为 None 时从磁盘读 .py。
    startor_cls: 注册到 gData.thCtrls 的启动器类，默认 ThreadStartor（线程版）。
    pro_startor_cls: 非 None 时同时注册 gData.proCtrls（进程版，Task 5 提供）。
    process_signals: dict {flowID: [信号名]}，进程版转发白名单。
    返回 (process_instance: dict[str,_Process], main_process: _Process, gData)。
    side effect: 与原 _Controller.run() 一致，构建期间 os.chdir(dir_path) 且不恢复；
    codeDict 的相对路径键以 chdir 后的 cwd 为准。
    """
    if startor_cls is None:
        startor_cls = ThreadStartor

    filePaths = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".ndjs"):
                filePath = os.path.join(root, file)
                filePaths.append(filePath)
    if len(filePaths) == 0:
        raise RuntimeError("No .ndjs file found in the directory.")

    decrypted_data = []
    for filePath in filePaths:
        decrypted_data.extend(_decrypt_ndjs_file(filePath))

    sys.path.append(os.path.abspath(dir_path))

    program_dir = dir_path

    main_process = None
    process_instance = {}
    for flow in decrypted_data:
        flowID = flow.get('flowID')
        if not flowID:
            # 编辑器保存的未命名子流程（parentID 关联，无 flowID）不可运行，跳过
            print("[HRFlowControllerProcess] skip flow without flowID:", flow.get('parentID', '?'))
            continue
        is_main = flowID == main_process_name
        process = _Process()
        process.is_main = is_main
        process_instance[flowID] = process
        if is_main:
            main_process = process

    if main_process is None:
        raise RuntimeError("main process '%s' not found in flow files" % main_process_name)

    os.chdir(dir_path)
    sys.path.append(dir_path)

    globalDataCode = os.path.join(program_dir, "ProgramGlobalData.py")
    file_data = _load_source(codeDict, globalDataCode)
    if file_data is None:
        raise RuntimeError("ProgramGlobalData.py not found")
    code = compile(file_data, globalDataCode, 'exec')
    module_name = "ProgramGlobalData"
    dynamic_module = types.ModuleType(module_name)
    exec(code, dynamic_module.__dict__)
    sys.modules[module_name] = dynamic_module

    gData = dynamic_module.gData

    for flow in decrypted_data:
        flowID = flow.get('flowID')
        if not flowID:
            continue  # 与建 process 循环一致：跳过编辑器未命名子流程
        process = process_instance[flowID]

        for node in flow['nodes']:
            data = node['data']
            node_instance = _Node()
            node_instance.id = node['id']
            node_instance.type = node['type']
            node_instance.title = data['title']
            node_instance.content = (data['content'] if 'content' in data else "")
            node_instance.isRunning = (data['isRunning'] if 'isRunning' in data else False)
            node_instance.isSubthread = ('IsSubthread' in data and data['IsSubthread']) or False
            node_instance.isNormal = ('isNormal' in data and data['isNormal']) or False
            node_instance.isSwapped = ('isSwapped' in data and data['isSwapped']) or False
            codePath = os.path.join(program_dir, flowID, data['title'] + "_" + node['id'] + ".py")

            node_file_data = _load_source(codeDict, codePath)
            if node_file_data is not None:
                node_instance.code = compile(node_file_data, codePath, 'exec')
                node_instance.source = node_file_data
                node_instance.file_path = codePath

            process.nodes[node_instance.id] = node_instance

            if node_instance.type == 'StartNode':
                process.start_id = node_instance.id

        for edge in flow['edges']:
            source = edge['source']
            target = edge['target']
            if source not in process.nodes or target not in process.nodes:
                raise RuntimeError("Invalid edge: %s -> %s" % (source, target))
            sourceHandle = edge.get('sourceHandle', "1")
            process.nodes[source].next_ids[sourceHandle] = target
            process.nodes[target].prev_id.append(source)

        threadDataCode = os.path.join(program_dir, flowID, "ThreadGlobalData.py")
        thread_file_data = _load_source(codeDict, threadDataCode)
        if thread_file_data is not None:
            process.localCode = compile(thread_file_data, threadDataCode, 'exec')
            process.localCodePath = flowID

    for flowID in process_instance.keys():
        def __getProcess(flowID=flowID):
            return process_instance.get(flowID)
        gData.thCtrls[flowID] = startor_cls(__getProcess, gData)
        if pro_startor_cls is not None:
            if not hasattr(gData, 'proCtrls'):
                gData.proCtrls = {}
            def __getProcProcess(flowID=flowID):
                return process_instance.get(flowID)
            gData.proCtrls[flowID] = pro_startor_cls(
                __getProcProcess, gData, dir_path, main_process_name,
                # 显式 process_signals 未提供该流程时回退自动收集（与 _Controller.run 一致）
                signals=(process_signals or {}).get(flowID) or _collect_signal_names(gData),
                codeDict=codeDict)

    return process_instance, main_process, gData


# ---------- Task 2: _FrameBuffer 帧共享内存缓冲 ----------
import multiprocessing
import multiprocessing as _mp  # ProcessStartor/ProcessExecutor 使用
import multiprocessing.shared_memory as _shm
import multiprocessing.synchronize  # ThreadDataBase 注解 multiprocessing.synchronize.Event 用
import numpy as np


class _FrameBuffer:
    """numpy 帧共享内存缓冲（单写单读）。

    布局: [seq:u64][rows:u32][cols:u32][dtype:u8][channels:u8][2 padding][像素数据...]
    写方 write() 返回递增序号（seq 最后提交，作为"提交标记"）;
    读方 read() 返回 (seq, frame 拷贝)。

    消费模式：读方应连续 read() 两次比较 seq，seq 相同才可接受该帧
    （配合 seq 最后提交，保证头部与数据一致）。
    2D 帧（channels=1）原样还原；3D 帧（channels=3）按 HWC（行主序）平铺，
    头部带通道数——读方无需外部 frame_shape 也能还原 3D（USB 相机等无文件探测源）。

    Windows 跨进程限制：形状变化重建（unlink+create）要求读方已退出，
    读方句柄打开时 Windows 不允许重名 create；demo 相机固定分辨率不会触发。
    启动顺序：写方必须先 create 再写；读方在写方首次 create 前 read() 会 FileNotFoundError。

    平台差异：Windows 句柄关闭即释放共享内存；POSIX（Linux）不随进程退出释放——
    创建方注册 atexit unlink（正常退出清理），异常退出残留由 unlink_orphan() 兜底。
    """
    _DTYPES = {0: 'uint8', 1: 'int16', 2: 'float32'}
    _DTYPE_ID = {v: k for k, v in _DTYPES.items()}
    _HEADER = 8 + 4 + 4 + 1 + 1 + 2  # 20 字节：seq u64|rows u32|cols u32|dtype u8|channels u8|2 padding

    def __init__(self, name: str):
        self.name = "HRVisionProc_" + name
        self._shm = None
        self._created = False

    def _size(self, rows, cols, dtype_id):
        return self._HEADER + rows * cols * np.dtype(self._DTYPES[dtype_id]).itemsize

    def _ensure(self, rows, cols, dtype_id):
        need = self._size(rows, cols, dtype_id)
        if self._shm is not None and self._shm.size >= need:
            return
        if self._shm is not None:
            if not self._created:
                raise RuntimeError("only the creator may resize the frame buffer %s" % self.name)
            self._shm.close()
            self._shm.unlink()
            self._shm = None
        # 残留段容错：上次进程被强杀可能留下同名段（_cleanup_on_exit 未执行）；
        # 类似 _ShmQueue——unlink 后重试；极端冲突兜底唯一名
        for _attempt in range(2):
            try:
                self._shm = _shm.SharedMemory(name=self.name, create=True, size=need)
                break
            except FileExistsError:
                try:
                    old = _shm.SharedMemory(name=self.name)
                    old.unlink()
                    old.close()
                except Exception:
                    pass
                time.sleep(0.05)
        else:
            self.name = self.name + "_" + uuid.uuid1().hex[:8]
            self._shm = _shm.SharedMemory(name=self.name, create=True, size=need)
        self._created = True
        _atexit.register(self._cleanup_on_exit)

    def _cleanup_on_exit(self):
        """进程退出时清理（POSIX 需要；Windows 无害——unlink 幂等）。"""
        if self._shm is not None and self._created:
            try:
                self._shm.unlink()
            except Exception:
                pass
            try:
                self._shm.close()
            except Exception:
                pass

    @staticmethod
    def unlink_orphan(name):
        """清理孤儿共享内存段（POSIX 上进程被强杀后残留，名字会补 HRVisionProc_ 前缀）。

        Windows 上同样有效（unlink 即释放名字）；段不存在时静默忽略。
        """
        try:
            seg = _shm.SharedMemory(name="HRVisionProc_" + name)
            seg.unlink()
            seg.close()
        except FileNotFoundError:
            pass

    def write(self, frame: np.ndarray) -> int:
        arr = np.ascontiguousarray(frame)
        dtype_id = self._DTYPE_ID.get(str(arr.dtype))
        if dtype_id is None:
            raise ValueError("unsupported dtype: %r (支持 %s)" % (arr.dtype, sorted(self._DTYPE_ID)))
        if arr.ndim == 2:
            rows, cols = arr.shape
            channels = 1
        elif arr.ndim == 3:
            rows, cols = arr.shape[0], arr.shape[1] * arr.shape[2]
            channels = arr.shape[2]
        else:
            raise ValueError("unsupported ndim: %d" % arr.ndim)
        self._ensure(rows, cols, dtype_id)
        buf = self._shm.buf
        # 先写尺寸/类型/通道，再拷数据，最后写 seq（seq 是"提交标记"，必须最后）
        np.frombuffer(buf[8:12], dtype=np.uint32)[0] = rows
        np.frombuffer(buf[12:16], dtype=np.uint32)[0] = cols
        buf[16] = dtype_id
        buf[17] = channels
        view = np.ndarray(arr.shape, dtype=arr.dtype, buffer=buf[self._HEADER:])
        np.copyto(view, arr)
        seq = int(np.frombuffer(buf[:8], dtype=np.uint64)[0]) + 1
        np.frombuffer(buf[:8], dtype=np.uint64)[0] = seq
        return seq

    def read(self):
        if self._shm is None:
            self._shm = _shm.SharedMemory(name=self.name)
        buf = self._shm.buf
        seq = int(np.frombuffer(buf[:8], dtype=np.uint64)[0])
        rows = int(np.frombuffer(buf[8:12], dtype=np.uint32)[0])
        cols = int(np.frombuffer(buf[12:16], dtype=np.uint32)[0])
        dtype_id = int(buf[16])
        dtype = self._DTYPES.get(dtype_id)
        if dtype is None:
            raise ValueError("unsupported dtype id: %d (支持 %s)" % (dtype_id, sorted(self._DTYPES)))
        dtype = np.dtype(dtype)
        channels = int(buf[17])
        # 头部带通道数：3D 帧直接还原（无需外部 frame_shape）；旧段/灰度保持 2D 原样
        if channels == 3 and cols % 3 == 0:
            view = np.ndarray((rows, cols // 3, 3), dtype=dtype, buffer=buf[self._HEADER:])
        else:
            view = np.ndarray((rows, cols), dtype=dtype, buffer=buf[self._HEADER:])
        return seq, view.copy()

    def close(self):
        if self._shm is not None:
            self._shm.close()
            if self._created:
                try:
                    self._shm.unlink()
                except FileNotFoundError:
                    pass  # POSIX: 名字已被删（unlink_orphan/atexit/重建）时 shm_unlink 抛此异常
            self._shm = None
            self._created = False


# ---------- Task 3: _SignalProxy/_SignalRelay 信号跨进程转发 ----------
class _SignalProxy:
    """子进程内替换 signal_instance：emit 参数经控制 Pipe 发往主进程。

    signal_names: 允许的信号名列表（与主进程 SignalProgram 一致）。
    注意：emit 参数会经 Pipe pickle 传输——大对象（图像帧）必须走 _FrameBuffer，
    不要作为 emit 参数。
    """

    def __init__(self, conn, signal_names):
        self._conn = conn
        self._names = set(signal_names)
        self._emits = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._names:
            raise AttributeError("unknown signal: %s" % name)
        if name not in self._emits:
            self._emits[name] = _SignalProxyEmit(self._conn, name)
        return self._emits[name]


class _SignalProxyEmit:
    """代理信号对象：调用 .emit(*args) 即发送 ('signal', name, args)。"""

    def __init__(self, conn, name):
        self._conn = conn
        self._name = name

    def emit(self, *args):
        self._conn.send(("signal", self._name, args))


class _SignalRelay:
    """主进程侧：从 Pipe 收子进程消息，把 ('signal', name, args) 转发到真实信号。"""

    def __init__(self, signal_instance):
        self._sig = signal_instance
        self._warned = set()

    def _handle_msg(self, msg):
        if msg is None:
            return False
        kind = msg[0]
        if kind == "signal":
            _, name, args = msg
            signal = getattr(self._sig, name, None)
            if signal is not None:
                signal.emit(*args)
            else:
                if name not in self._warned:
                    self._warned.add(name)
                    print("[HRFlowController] relay: unknown signal %r" % name)
        return True

    def run_once(self, conn, timeout=0.1):
        """消费 conn 上已到达的一条消息（阻塞至多 timeout 秒）。

        返回 True 表示消费了一条消息（含被忽略的控制消息）；False 表示超时或连接已关闭
        （子进程退出时 recv 抛 EOFError，此处转为 False，供循环层检测子进程退出）。
        """
        try:
            if not conn.poll(timeout):
                return False
        except BrokenPipeError:
            pass  # 连接已断；若仍有缓冲消息 recv 可排空，否则 recv 抛 EOFError
        try:
            msg = conn.recv()
        except (EOFError, BrokenPipeError):
            return False
        return self._handle_msg(msg)

    def run_once_from_msg(self, msg):
        """处理一条已 recv 的消息（不阻塞）。"""
        return self._handle_msg(msg)


# ---------- Task 4: _process_main 子进程运行时 ----------
class _ProcessStubThreadStartor:
    """子进程内占位 ThreadStartor：build_processes 注册用，实际不会启动流程。"""

    def __init__(self, getProcess, gData):
        self.getProcess = getProcess
        self.gData = gData

    def start(self, is_thread=True, **kwargs):
        raise RuntimeError("cannot start flows inside a child process")


def _process_main(flow_id, dir_path, main_process_name, control_conn, proc_config=None,
                  codeDict=None, **kwargs):
    """子进程入口：在独立进程里运行 flow_id 对应的流程链。

    control_conn: 与主进程的双向 Pipe（子进程端）。
    proc_config: dict，可含:
        signals: 允许转发到主进程的信号名列表
    kwargs: 写入子进程模块级 thData 的属性（如 frame_name/frame_event 通道配置）。
            注意：不用 ThreadData(**kwargs) 构造注入——节点代码 import * 拿到的是模块级实例。
    语义约定：("status", "finished") 表示子进程执行结束（含节点异常被框架吞掉的情况——
    与原框架一致，节点异常经 traceback.print_exc 输出到 stderr，不进入控制通道）。
    ("status", "thdata_failed") 表示 thData 注入不完整但不中止流程；依赖 thData 的节点
    会失败于 stderr。父进程如需区分成败，须结合 stderr 或扩展协议。
    run_failed 仅覆盖构建/注入阶段异常；节点链异常被框架 ThreadExecutor 吞掉（只在 stderr），
    不会触发 run_failed。
    """
    if proc_config is None:
        proc_config = {}
    signal_names = proc_config.get("signals", [])
    try:
        process_instance, main_process, gData = build_processes(
            dir_path, main_process_name, codeDict=codeDict,
            startor_cls=_ProcessStubThreadStartor)
    except Exception as e:
        control_conn.send(("status", "build_failed", str(e)))
        return

    # 替换 signal_instance 为转发代理（ProgramGlobalData 模块属性和节点 globals 都覆盖）
    proxy = _SignalProxy(control_conn, signal_names)
    module = sys.modules.get("ProgramGlobalData")
    if module is not None:
        module.signal_instance = proxy

    process = process_instance.get(flow_id)
    if process is None:
        control_conn.send(("status", "build_failed", "flow not found: " + flow_id))
        return

    control_conn.send(("status", "ready"))

    # 注入节点执行上下文（与线程版 run_main 的 _globals 结构一致）
    locals_ = {}
    locals_["gData"] = gData
    locals_["signal_instance"] = proxy
    locals_["thData"] = None  # 下面按实际注入

    executor = ThreadExecutor(process)
    # 注入 thData：节点代码里 `from <flow>.ThreadGlobalData import *` 拿到的 thData
    # 是模块级实例（import * 会覆盖 globals 注入），所以直接把 kwargs 打到模块级实例属性上
    try:
        if process.localCodePath and process.localCode:
            threadDataKey = process.localCodePath + '.ThreadGlobalData'
            dynamic_module = types.ModuleType(threadDataKey)
            exec(process.localCode, dynamic_module.__dict__)
            sys.modules[threadDataKey] = dynamic_module
            thd = getattr(dynamic_module, 'thData', None)
            if thd is None and kwargs:
                control_conn.send(("status", "thdata_failed",
                                   "ThreadGlobalData has no thData attribute"))
            elif thd is not None:
                for _k, _v in kwargs.items():
                    setattr(thd, _k, _v)
                locals_['thData'] = thd
        elif kwargs:
            control_conn.send(("status", "thdata_failed",
                               "flow has no ThreadGlobalData.py"))
    except Exception as e:
        control_conn.send(("status", "thdata_failed", str(e)))

    try:
        executor.run(locals_, locals_, is_thread=False)
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        control_conn.send(("status", "run_failed", str(e)))
    control_conn.send(("status", "finished"))


# ---------- Task 5: ProcessExecutor/ProcessStartor 进程启动器 ----------
# 「指定解释器跑进程流程」（ProcessStartor.python_exe）已提炼为独立模块：
# HRVision.ProcessIsolate（bootstrap / 具名锁 / 外部 spawn），框架只保留调用入口。

class ProcessExecutor:
    """进程版执行器：管理子进程生命周期（API 与线程版 ThreadExecutor 对齐：start/stop/isAlive）。"""

    def __init__(self, proc, conn):
        self.proc = proc
        self.conn = conn  # 主进程端 Pipe

    def isAlive(self):
        return self.proc is not None and self.proc.is_alive()

    def stop(self):
        """停止子进程：发 ("stop",) 为协议预留——子进程当前无消息循环（v1 无响应式
        stop），实际停止由 join(2s) 超时后的 terminate 兜底。
        注意：子进程从不读控制 Pipe（v1），父→子消息必须远小于 Windows 匿名管道缓冲
        （约 4KB），否则 send 会永久阻塞。"""
        if self.proc is not None and self.proc.is_alive():
            try:
                self.conn.send(("stop",))
            except Exception:
                pass
            self.proc.join(timeout=2)
            if self.proc.is_alive():
                self.proc.terminate()
                self.proc.join(timeout=2)
        try:
            self.conn.close()
        except Exception:
            pass

    def join(self, timeout=None):
        if self.proc is not None:
            self.proc.join(timeout)


_PROC_PRIORITY_MAP = {
    "idle": 0, "below": 1, "normal": 2, "above": 3, "high": 4, "realtime": 5,
}
_THREAD_PRIORITY_MAP = {
    "idle": -15, "lowest": -2, "below": -1, "normal": 0,
    "above": 1, "highest": 2, "time_critical": 15,
}


def _apply_process_priority(pid, priority):
    """Windows 进程优先级（psutil）。priority: idle/below/normal/above/high/realtime。"""
    try:
        import psutil
        p = psutil.Process(pid)
        nice = {0: psutil.IDLE_PRIORITY_CLASS, 1: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                2: psutil.NORMAL_PRIORITY_CLASS, 3: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                4: psutil.HIGH_PRIORITY_CLASS, 5: psutil.REALTIME_PRIORITY_CLASS}
        p.nice(nice[_PROC_PRIORITY_MAP[priority]])
    except Exception:
        pass


def _apply_cpu_affinity(pid, cores):
    """进程 CPU 亲和性（锁核）。cores: 核列表，如 [0, 1]。"""
    try:
        import psutil
        psutil.Process(pid).cpu_affinity(list(cores))
    except Exception:
        pass


def _apply_thread_priority(tid, priority):
    """Windows 线程优先级（SetThreadPriority）。priority: idle/lowest/below/normal/above/highest/time_critical。"""
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadPriority(
            ctypes.c_void_p(tid), _THREAD_PRIORITY_MAP[priority])
    except Exception:
        pass


class ProcessStartor:
    """进程版启动器：start() 拉起子进程跑流程（API 与 ThreadStartor 对齐）。

    flow_id 取自流程的 localCodePath（ThreadGlobalData.py 目录名）。
    start() 的 kwargs 会写入子进程模块级 thData 属性（见 _process_main）。
    priority: 进程优先级（idle/below/normal/above/high/realtime）。
    cpu_affinity: 进程锁核（核列表，如 [0, 1]；None 不锁）。
    python_exe: 指定子进程运行的解释器（None = 当前环境 multiprocessing spawn）。
        非 None 时走「外部 spawn」路径：参数 pickle 到临时文件 → 目标 python 执行
        bootstrap → 控制通道用 multiprocessing.connection（Win 命名管道 / POSIX 回环）。
        注意：目标环境必须能 import HRVision.HRFlowController（cp 版本匹配 +
        PyHRVision 已安装或 pyd 可导入），且节点参数（通道对象等）需可 pickle（同 spawn）。
        start() 的 kwargs 里 python_exe 可再覆盖（节点级参数 → PipelineManager 透传）。
    """

    def __init__(self, getProcess, gData, dir_path, main_process_name, signals=None,
                 start_method="spawn", priority=None, cpu_affinity=None,
                 python_exe=None, codeDict=None):
        self.getProcess = getProcess
        self.gData = gData
        self.dir_path = dir_path
        self.main_process_name = main_process_name
        self.signals = signals or []
        self.start_method = start_method
        self.priority = priority
        self.cpu_affinity = cpu_affinity
        self.python_exe = python_exe
        self.codeDict = codeDict        # 发布模式源码字典（子进程不再回盘读 .py）

    def start(self, is_thread=True, **kwargs):
        python_exe = kwargs.pop("python_exe", self.python_exe)
        if python_exe:
            return self._start_external(python_exe, **kwargs)
        ctx = _mp.get_context(self.start_method)
        parent_conn, child_conn = ctx.Pipe()
        flow_id = self.getProcess().localCodePath  # flowID 目录名；无 ThreadGlobalData 时回退
        proc = ctx.Process(target=_process_main, args=(
            flow_id if flow_id else "", self.dir_path, self.main_process_name,
            child_conn, {"signals": self.signals}),
            kwargs=dict(kwargs, codeDict=self.codeDict))   # ★ codeDict 随子进程
        proc.start()
        child_conn.close()
        _pending_processes.append(proc)   # 主进程退出时终止（避免残留持有段）
        if self.priority:
            _apply_process_priority(proc.pid, self.priority)
        if self.cpu_affinity:
            _apply_cpu_affinity(proc.pid, self.cpu_affinity)
        return ProcessExecutor(proc, parent_conn)

    def _start_external(self, python_exe, **kwargs):
        """外部解释器路径：委托 HRVision.ProcessIsolate.start_external_process。

        控制通道：Windows 命名管道 / POSIX 回环；mp 同步原语按名字序列化；
        参数 pickle → 目标 python bootstrap → _process_main（详见模块文档）。
        """
        from HRVision.ProcessIsolate import start_external_process
        return start_external_process(
            python_exe, self.getProcess, self.dir_path, self.main_process_name,
            signals=self.signals, kwargs=kwargs,
            priority=self.priority, cpu_affinity=self.cpu_affinity,
            codeDict=self.codeDict)                        # ★ codeDict 随外部子进程

# 兼容别名：原框架 Executor/Startor 更名为 ThreadExecutor/ThreadStartor，旧代码仍可用
Executor = ThreadExecutor
Startor = ThreadStartor


_SHM_QUEUE_MAGIC = 0x48524251   # "HRBQ"
# Header 布局（96B）：[0:4]magic [4:8]maxlen [8:12]msg_size [12:16]write_idx
#   [16:20]read_idx [20:24]count [24:28]gen [28:32]obj_size
#   [32:36]next_name_len（扩容预告：下一段名长度；0=无预告）
#   [36:96]next_name 76B（扩容预告：下一段名（换名扩容，"_v{gen}" 后缀））
_SHM_QUEUE_HEADER = 96
_SEGMENTS_FILE = os.path.join(tempfile.gettempdir(), "hrvision_segments.txt")
_pending_processes = []         # 主进程退出时统一终止的子进程


def _register_segment(name):
    """登记共享内存段名（清理兜底唯一名段用）。"""
    try:
        with open(_SEGMENTS_FILE, "a", encoding="utf-8") as f:
            f.write(name + "\n")
    except Exception:
        pass


def _unregister_segment(name):
    try:
        with open(_SEGMENTS_FILE, encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip() and l.strip() != name]
        with open(_SEGMENTS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(names))
    except Exception:
        pass


def cleanup_all_segments():
    """按登记名单清理所有残留共享内存段（含兜底唯一名段）。

    强杀进程残留的段名无法枚举（Windows 无 API），但创建时已登记——
    按名单 unlink；被其他进程持有（正在使用）的段 unlink 失败自动跳过。
    建议在应用启动时调用一次（_Controller.run 已默认调用）。
    """
    try:
        with open(_SEGMENTS_FILE, encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip()]
    except Exception:
        names = []
    for name in names:
        try:
            seg = _shm.SharedMemory(name=name)
            seg.unlink()
            seg.close()
        except Exception:
            pass
    try:
        open(_SEGMENTS_FILE, "w", encoding="utf-8").close()
    except Exception:
        pass


def _kill_pending_processes():
    """主进程正常退出时终止所有子进程（避免 spawn 子进程残留持有段句柄）。"""
    for proc in _pending_processes:
        try:
            if proc.is_alive():
                proc.terminate()
        except Exception:
            pass


_atexit.register(_kill_pending_processes)


def _shm_segment_valid(name):
    """验证同名共享内存段是否有效（magic 匹配）。"""
    try:
        old = _shm.SharedMemory(name=name)
        try:
            return int(np.frombuffer(old.buf[0:4], np.uint32)[0]) == _SHM_QUEUE_MAGIC
        finally:
            old.close()
    except Exception:
        return False


def _resolve_shm_name(name):
    """段名解析（attach 时旧名可能已被扩容换名）：从登记名单回溯 {name}_v* 最新段。"""
    candidates = [name]
    try:
        with open(_SEGMENTS_FILE, encoding="utf-8") as f:
            for ln in f:
                n = ln.strip()
                if n.startswith(name + "_v"):
                    candidates.append(n)
    except Exception:
        pass
    # 最大化后缀名优先（新段为准）；未登记则仅原始名
    return max(candidates)


class _ShmQueue:
    """共享内存环形消息队列（进程间，零管道拷贝）。

    布局（单段共享内存，双区）：
        [0:4] magic  [4:8] maxlen  [8:12] msg_size  [12:16] write_idx
        [16:20] read_idx  [20:24] count
        [24...] 消息槽 ×maxlen：每槽 = [flag:u32][len:u32][meta_len:u32][meta][payload]
        [消息区后] 对象槽 ×maxlen：大对象（numpy 帧）原始字节区（同槽格式）

    消息语义（put/get）：
        - 小对象（非 numpy）：消息槽直接存 pickle 字节（flag=0）
        - 大对象（numpy 帧）：**原始字节写入对象槽**（免序列化），消息槽只放
          描述字典 {"__obj__": uid, "shape": ..., "dtype": ...}（flag=2，几百字节）
          ——大数据不走消息通道，按 uid（槽索引）从对象区取，传输量大幅减少。
    消息槽 i ↔ 对象槽 i 1:1 对齐：drop_oldest 覆盖时两区同步（ridx/widx 共用）。
    互斥由外部 mp.Lock 提供（SemLock 内核对象，经 spawn 参数继承）。
    """
    _FLAG_PICKLE = 0      # 消息槽：pickle 小对象
    _FLAG_OBJ_DESC = 2    # 消息槽：对象描述（大对象在对象槽）

    @staticmethod
    def _serialize(data):
        """返回 (flag, meta, payload)。numpy 数组直写原始字节（免序列化）。"""
        if isinstance(data, np.ndarray):
            arr = np.ascontiguousarray(data)
            return 1, pickle.dumps((arr.shape, str(arr.dtype))), arr.tobytes()
        return 0, b'', pickle.dumps(data)

    @staticmethod
    def _deserialize(flag, meta, payload):
        if flag == 1:
            shape, dtype = pickle.loads(meta)
            return np.frombuffer(payload, dtype=np.dtype(dtype)).reshape(shape).copy()
        return pickle.loads(payload)

    def __init__(self, name, maxlen, msg_size, obj_size, create):
        self.name = name
        self.msg_size = int(msg_size)
        self.obj_size = int(obj_size)
        self.slot_size = 12 + self.msg_size    # 消息槽
        self.obj_slot_size = 12 + self.obj_size  # 对象槽
        self.maxlen = int(maxlen)
        self._msg_off = _SHM_QUEUE_HEADER
        self._obj_off = self._msg_off + self.slot_size * self.maxlen
        self.total = self._obj_off + self.obj_slot_size * self.maxlen
        self._created = create
        if create:
            for _attempt in range(3):
                try:
                    self._shm = _shm.SharedMemory(name=self.name, create=True, size=self.total)
                    break
                except FileExistsError:
                    # 同名段已存在：先验魔数——有效则**复用**（其他进程正持有，
                    # 如 UI 附接/独立驱动进程；unlink 会拆掉别人正用的段导致命令丢失）；
                    # 无魔数/垃圾段才 unlink 重建（Windows 名字释放有延迟，重试）
                    if _shm_segment_valid(name):
                        self._shm = _shm.SharedMemory(name=name)
                        self._created = False   # 复用标记：跳过头部初始化
                        break
                    try:
                        old = _shm.SharedMemory(name=self.name)
                        old.unlink()
                        old.close()
                    except Exception:
                        pass
                    time.sleep(0.05)
            else:
                # 残留进程仍持有句柄（如 spawn 子进程未被回收）：改用唯一名兜底
                self.name = self.name + "_" + uuid.uuid1().hex[:8]
                self._shm = _shm.SharedMemory(name=self.name, create=True, size=self.total)
            if self._created:              # 复用已有段：跳过头部写（不干扰原持有进程）
                _register_segment(self.name)   # 登记段名（清理兜底残留段用）
                self._init_header(self._shm.buf, 0, self.obj_size)
        else:
            try:
                self._shm = _shm.SharedMemory(name=self.name)
            except FileNotFoundError:
                # attach 前写方已扩容换名（旧名段删除）：从登记名单回溯最新 _v* 段
                resolved = _resolve_shm_name(self.name)
                if resolved == self.name:
                    raise
                self.name = resolved
                self._shm = _shm.SharedMemory(name=self.name)
            if int(np.frombuffer(self._shm.buf[0:4], np.uint32)[0]) != _SHM_QUEUE_MAGIC:
                raise RuntimeError("bad shared queue: %s" % self.name)
            # attach：布局以段头为准（扩容后段大小由写方维护）
            self.maxlen = int(np.frombuffer(self._shm.buf[4:8], np.uint32)[0])
            self.msg_size = int(np.frombuffer(self._shm.buf[8:12], np.uint32)[0])
            self.obj_size = int(np.frombuffer(self._shm.buf[28:32], np.uint32)[0])
            self.obj_slot_size = 12 + self.obj_size
            self._obj_off = self._msg_off + self.slot_size * self.maxlen
            self.total = self._obj_off + self.obj_slot_size * self.maxlen
        self._buf = self._shm.buf
        self._gen = int(np.frombuffer(self._buf[24:28], np.uint32)[0])

    def _slot_off(self, idx):
        return self._msg_off + idx * self.slot_size

    def _obj_slot_off(self, idx):
        return self._obj_off + idx * self.obj_slot_size

    def qsize(self):
        return int(np.frombuffer(self._buf[20:24], np.uint32)[0])

    def _init_header(self, buf, gen, obj_size, write_indices=True):
        b = buf
        np.frombuffer(b[0:4], np.uint32)[0] = _SHM_QUEUE_MAGIC
        np.frombuffer(b[4:8], np.uint32)[0] = self.maxlen
        np.frombuffer(b[8:12], np.uint32)[0] = self.msg_size
        if write_indices:
            np.frombuffer(b[12:16], np.uint32)[0] = 0
            np.frombuffer(b[16:20], np.uint32)[0] = 0
            np.frombuffer(b[20:24], np.uint32)[0] = 0
        np.frombuffer(b[24:28], np.uint32)[0] = gen
        np.frombuffer(b[28:32], np.uint32)[0] = obj_size
        np.frombuffer(b[32:36], np.uint32)[0] = 0            # 无下一段名预告
        b[36:96] = b"\x00" * 60

    def _check_gen(self):
        """代际检查（每次 put/get 持锁后调用）：读方发现段被扩容 → 换名重 attach。

        扩容（写方 _grow）在锁内创建**新名**段（`{name}_v{gen}`）并把"下一段名"
        写进当前段 header 预告；读方（仍持旧段）发现 gen 变化 → 按预告名 attach 新段。
        换名（而非同名重建）绕开 Windows unlink→create 同名语义的不确定性。
        """
        gen = int(np.frombuffer(self._buf[24:28], np.uint32)[0])
        if gen == self._gen:
            return
        nlen = int(np.frombuffer(self._buf[32:36], np.uint32)[0])
        new_name = self.name
        if 0 < nlen <= 76:
            candidate = bytes(self._buf[36:36 + nlen]).decode("utf-8", "replace")
            if candidate:
                new_name = candidate
        try:
            self._shm.close()
        except Exception:
            pass
        self._shm = _shm.SharedMemory(name=new_name)
        self.name = new_name
        self._buf = self._shm.buf
        self._gen = int(np.frombuffer(self._buf[24:28], np.uint32)[0])
        self.maxlen = int(np.frombuffer(self._buf[4:8], np.uint32)[0])
        self.msg_size = int(np.frombuffer(self._buf[8:12], np.uint32)[0])
        self.obj_size = int(np.frombuffer(self._buf[28:32], np.uint32)[0])
        self.obj_slot_size = 12 + self.obj_size
        self._obj_off = self._msg_off + self.slot_size * self.maxlen
        self.total = self._obj_off + self.obj_slot_size * self.maxlen

    def _grow(self, new_obj_size, lock):
        """按需扩容（仅在 put 持锁内调用）：新建更大段（换名 `_v{gen}`）→ 代际+1。

        只涨不缩（new_obj_size 不大于当前则忽略）；count/ridx/widx 清零——
        旧数据丢弃（maxlen=1/drop_oldest 语义安全；多槽场景整条队列清空）。
        旧段保持原样（其他进程仍持有句柄时也不受影响——读方经 header 预告换名）。
        """
        new_obj_size = int(new_obj_size)
        if new_obj_size <= self.obj_size:
            return
        self._gen += 1
        new_name = self.name + "_v%d" % self._gen
        # 1) 预告写进当前段（读方挂旧段也能感知 gen + 下一段名）
        b = self._buf
        np.frombuffer(b[24:28], np.uint32)[0] = self._gen
        nb = new_name.encode("utf-8", "replace")[:76]
        np.frombuffer(b[32:36], np.uint32)[0] = len(nb)
        b[36:96] = b"\x00" * 60
        b[36:36 + len(nb)] = nb
        # 2) 销毁当前段对象（unlink 旧名：失败的残留由 cleanup 兜底）
        try:
            self._shm.close()
            try:
                self._shm.unlink()
            except Exception:
                pass
        except Exception:
            pass
        self.obj_size = new_obj_size
        self.obj_slot_size = 12 + self.obj_size
        self._obj_off = self._msg_off + self.slot_size * self.maxlen
        self.total = self._obj_off + self.obj_slot_size * self.maxlen
        # 3) 换名创建新段（残留同名段（上次崩溃未清理）→ unlink 重试）
        for _attempt in range(5):
            try:
                self._shm = _shm.SharedMemory(name=new_name, create=True, size=self.total)
                break
            except FileExistsError:
                try:
                    old = _shm.SharedMemory(name=new_name)
                    old.unlink()
                    old.close()
                    _unregister_segment(new_name)
                except Exception:
                    pass
                time.sleep(0.05)
        else:
            raise RuntimeError("unable to create shared segment: %s" % new_name)
        self.name = new_name
        self._buf = self._shm.buf
        self._init_header(self._buf, self._gen, self.obj_size)
        _register_segment(self.name)

    def _write_slot(self, off, flag, meta, payload):
        buf = self._buf
        np.frombuffer(buf[off:off + 4], np.uint32)[0] = flag
        np.frombuffer(buf[off + 4:off + 8], np.uint32)[0] = len(payload)
        np.frombuffer(buf[off + 8:off + 12], np.uint32)[0] = len(meta)
        buf[off + 12:off + 12 + len(meta)] = meta
        buf[off + 12 + len(meta):off + 12 + len(meta) + len(payload)] = payload

    def _read_slot(self, off):
        buf = self._buf
        flag = int(np.frombuffer(buf[off:off + 4], np.uint32)[0])
        n = int(np.frombuffer(buf[off + 4:off + 8], np.uint32)[0])
        mlen = int(np.frombuffer(buf[off + 8:off + 12], np.uint32)[0])
        meta = bytes(buf[off + 12:off + 12 + mlen])
        # 大对象 payload 用 memoryview（避免 bytes() 额外 6MB 拷贝，降低堆碎片）
        payload = memoryview(buf)[off + 12 + mlen:off + 12 + mlen + n]
        return flag, meta, payload

    def put(self, data, lock, overflow):
        """写入一条消息。

        numpy 大对象：原始字节进对象槽，消息槽只放描述（uid=槽索引，几百字节）；
        小对象：pickle 直接进消息槽。drop_new 满返回 False；drop_oldest 覆盖最旧。
        """
        if isinstance(data, np.ndarray):
            # 大对象路径：对象槽存原始字节，消息槽存 {"__obj__": uid, shape, dtype}
            arr = np.ascontiguousarray(data)
            raw = arr.tobytes()
            desc = pickle.dumps({"__obj__": 0, "shape": arr.shape, "dtype": str(arr.dtype)})
        else:
            flag, meta, payload = self._serialize(data)
            total = len(meta) + len(payload)
            if total > self.msg_size:
                raise ValueError("message too large for queue %s: %d > %d"
                                 % (self.name, total, self.msg_size))
            raw = None
            desc = None
        while True:
            with lock:
                self._check_gen()      # 读方/写方都可能经历扩段：先对齐代际
                if raw is not None and len(raw) > self.obj_size:
                    # 按需扩容（持锁）：比当前档更大 → 自动扩大段（只涨不缩，见 _grow）
                    self._grow(len(raw) + 256 * 1024, lock)
                count = int(np.frombuffer(self._buf[20:24], np.uint32)[0])
                if count < self.maxlen:
                    widx = int(np.frombuffer(self._buf[12:16], np.uint32)[0])
                    if raw is not None:
                        # 大对象：对象槽（widx 对齐）写原始字节
                        self._write_slot(self._obj_slot_off(widx), 1, b'', raw)
                        # 消息槽写描述
                        self._write_slot(self._slot_off(widx), self._FLAG_OBJ_DESC,
                                         b'', desc)
                    else:
                        self._write_slot(self._slot_off(widx), flag, meta, payload)
                    np.frombuffer(self._buf[12:16], np.uint32)[0] = (widx + 1) % self.maxlen
                    np.frombuffer(self._buf[20:24], np.uint32)[0] = count + 1
                    return True
                if overflow == "drop_new":
                    return False
                if overflow == "drop_oldest":
                    ridx = int(np.frombuffer(self._buf[16:20], np.uint32)[0])
                    np.frombuffer(self._buf[16:20], np.uint32)[0] = (ridx + 1) % self.maxlen
                    np.frombuffer(self._buf[20:24], np.uint32)[0] = count - 1
                    continue
                # block：轮询等待空间
            time.sleep(0.001)

    def get(self, lock, timeout=None):
        """读取一条消息。大对象按消息槽描述从对象槽取（uid=槽索引）。超时/空返回 None。"""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            with lock:
                self._check_gen()      # 读方：扩容代际变化 → 重 attach 新段
                count = int(np.frombuffer(self._buf[20:24], np.uint32)[0])
                if count > 0:
                    ridx = int(np.frombuffer(self._buf[16:20], np.uint32)[0])
                    msg_off = self._slot_off(ridx)
                    flag, meta, payload = self._read_slot(msg_off)
                    if flag == self._FLAG_OBJ_DESC:
                        # 大对象：按描述（uid=ridx 槽对齐）从对象槽取原始字节
                        desc = pickle.loads(payload)
                        oflag, ometa, opayload = self._read_slot(self._obj_slot_off(ridx))
                        shape = desc.get("shape")
                        dtype = np.dtype(desc.get("dtype"))
                        result = np.frombuffer(opayload, dtype=dtype).reshape(shape).copy()
                    else:
                        result = self._deserialize(flag, meta, payload)
                    np.frombuffer(self._buf[16:20], np.uint32)[0] = (ridx + 1) % self.maxlen
                    np.frombuffer(self._buf[20:24], np.uint32)[0] = count - 1
                    return result
            if deadline is not None and time.time() >= deadline:
                return None
            time.sleep(0.001)

    def close(self):
        try:
            self._shm.close()
            if self._created:
                self._shm.unlink()
                _unregister_segment(self.name)
        except Exception:
            pass


class DataBus:
    """通用数据总线：进程间/线程间消息通信统一接口。

    进程模式（mode="process"）基于**共享内存环形队列**（零管道拷贝，
    帧/大对象直接写入共享内存段）；线程模式（mode="thread"）基于 threading.Queue。

    支持消息队列 + 最大长度防溢出（溢出策略可配）：
        overflow="drop_oldest"  队列满时覆盖最旧消息（最新优先，默认）
        overflow="drop_new"     队列满时丢弃新消息（返回 False）
        overflow="block"        队列满时阻塞 put 直到有空间

    用法（线程/进程节点代码通用）：
        bus = DataBus("CCD1_frame", maxlen=1, mode="process")   # 主进程创建
        bus.put(frame)                    # 发送
        data = bus.get(timeout=1)         # 接收（超时返回 None）
        bus.close()                       # 进程退出/不再使用时释放

    进程模式经 spawn 参数传给子进程（自动按名字 attach，不重复创建）。
    """

    def __init__(self, name="", maxlen=100, mode="auto", overflow="drop_oldest",
                 max_msg_size=1024 * 1024, max_obj_size=None):
        if mode == "auto":
            mode = "thread"
        if mode not in ("thread", "process"):
            raise ValueError("mode must be 'thread'/'process': %r" % mode)
        if overflow not in ("drop_oldest", "drop_new", "block"):
            raise ValueError("overflow must be drop_oldest/drop_new/block: %r" % overflow)
        self.name = name
        self.maxlen = int(maxlen)
        self.mode = mode
        self.overflow = overflow
        self.max_msg_size = int(max_msg_size)
        if max_obj_size is None:
            max_obj_size = 8 * 1024 * 1024   # 大对象槽默认 8MB（1920x1080x3 帧 6.2MB 够用）
        self.max_obj_size = int(max_obj_size)
        if mode == "thread":
            import queue as _queue
            self._q = _queue.Queue(maxsize=self.maxlen)
            self._lock = threading.Lock()
        else:
            self._q = _ShmQueue("HRVisionBus_" + name, self.maxlen, self.max_msg_size, self.max_obj_size, create=True)
            # 具名锁（HRVision.ProcessIsolate）：外部解释器路径（python_exe）pickle
            # 按名字重建，无需句柄继承/传递即可跨进程共享；spawn 路径同样兼容
            if sys.platform == "win32":
                from HRVision.ProcessIsolate import make_named_lock
                self._lock = make_named_lock(name)
            else:
                self._lock = _mp.Lock()

    # pickle 支持：spawn 子进程按名字 attach（不携带共享内存句柄）
    def __getstate__(self):
        # 进程模式用实际段名（兜底唯一名时 _ShmQueue.name 已改，self.name 仍是原名）
        name = self._q.name if self.mode == "process" else self.name
        return {"name": name, "maxlen": self.maxlen, "mode": self.mode,
                "overflow": self.overflow, "max_msg_size": self.max_msg_size,
                "max_obj_size": self.max_obj_size,
                "_lock": self._lock}

    def __setstate__(self, state):
        self.name = state["name"]
        self.maxlen = state["maxlen"]
        self.mode = state["mode"]
        self.overflow = state["overflow"]
        self.max_msg_size = state["max_msg_size"]
        self.max_obj_size = state["max_obj_size"]
        self._lock = state["_lock"]
        if self.mode == "thread":
            import queue as _queue
            self._q = _queue.Queue(maxsize=self.maxlen)
        else:
            self._q = _ShmQueue(self.name, self.maxlen, self.max_msg_size, self.max_obj_size, create=False)

    def put(self, data) -> bool:
        """发送消息。drop_new 满时返回 False；其余策略返回 True。"""
        if self.mode == "thread":
            if self.overflow == "drop_oldest":
                with self._lock:
                    if self._q.qsize() >= self.maxlen:
                        try:
                            self._q.get_nowait()
                        except Exception:
                            pass
                    try:
                        self._q.put_nowait(data)
                    except Exception:
                        return False
                return True
            if self.overflow == "drop_new":
                try:
                    self._q.put_nowait(data)
                    return True
                except Exception:
                    return False
            self._q.put(data)
            return True
        return self._q.put(data, self._lock, self.overflow)

    def get(self, timeout=None):
        """接收消息。超时/空返回 None。"""
        if self.mode == "thread":
            try:
                return self._q.get(timeout=timeout)
            except Exception:
                return None
        return self._q.get(self._lock, timeout)

    def qsize(self) -> int:
        try:
            return self._q.qsize()
        except Exception:
            return 0

    def empty(self) -> bool:
        return self.qsize() == 0

    def close(self):
        try:
            self._q.close()
        except Exception:
            pass


# ================= 通用组件：显示槽 / 帧探测 / 运行监控 =================
# （原 FlowFourCam services 层通用能力，与业务解耦后集成进框架，
#   任何项目可复用：DisplaySlot 显示数据共享内存、Monitor 运行监控）

# ---------- 帧尺寸探测（DataBus 槽位自适应 / 显示槽 reshape 用） ----------

def frame_bytes(video_path):
    """按视频首帧尺寸计算单帧缓冲字节数 = height × stride。

    stride（每行字节）从帧数组取：BGR 图 = w*3、灰度图 = w、行填充也覆盖；
    槽位既不浪费也不超限。打不开视频返回 None（沿用 DataBus 默认槽）。
    """
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            return frame.strides[0] * frame.shape[0]
    except Exception:
        pass
    return None


def frame_shape(video_path):
    """视频/图片首帧尺寸 (h, w)；打不开返回 None。"""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            return frame.shape[:2]
    except Exception:
        pass
    return None


# ---------- 显示槽：窗体显示数据的共享内存（_FrameBuffer 封装） ----------

class DisplaySlot:
    """单写单读显示槽：写方覆盖写最新帧，读方按 seq 感知新帧。

    职责（收拢 _FrameBuffer 细节）：
        - 槽名生成（HRDisplay_ 命名空间；_FrameBuffer 内部再加 HRVisionProc_ 前缀）
        - 展平存储 reshape（_FrameBuffer 把 BGR 3D 存为 (h, w*3)，读方按帧尺寸恢复）
        - seq 语义：写方写完数据才提交 seq（提交标记）；读方 seq 变化 = 有新帧
        - 写方未就绪（段未创建）静默返回 None，调用方无需 try/except
        - 共享引用：多个窗格引用同一 DisplaySlot 对象 = 共享一段共享内存

    用法：
        主进程（创建 + 读）：slot = DisplaySlot.origin("CCD1", frame_shape)
                             slot = DisplaySlot.res("CCD1", 3, frame_shape)
        写方（相机/算法进程）：slot = DisplaySlot(name); slot.write(frame)
        读方（UI/监控）：seq, frame3d = slot.read() 或 seq = slot.read_seq()
    """

    _PREFIX = "HRDisplay_"

    def __init__(self, name, frame_shape=None):
        self.name = name                # 原始名（不含 HRVisionProc_ 前缀，子进程可重建）
        self.frame_shape = frame_shape  # (h, w)：读方 reshape 用（写方可为 None）
        self._fb = _FrameBuffer(name)   # 主进程惰性 create；子进程 attach 后 write

    # ---- 工厂（槽名 + 主进程侧创建） ----

    @classmethod
    def origin(cls, cam, frame_shape=None):
        """相机原图槽：fan-out 多窗格共享一段（相机进程写一次）。"""
        return cls("%s%s_origin" % (cls._PREFIX, cam), frame_shape)

    @classmethod
    def res(cls, cam, algo_id=None, frame_shape=None):
        """算法结果槽：algo_id=None 为共享结果槽（同相机算法共享一段，多写者覆盖写）。"""
        if algo_id is None:
            return cls("%s%s_res" % (cls._PREFIX, cam), frame_shape)
        return cls("%s%s_A%d_res" % (cls._PREFIX, cam, algo_id), frame_shape)

    # ---- 写方（相机/算法进程） ----

    def write(self, frame) -> int:
        """覆盖写最新帧，返回 seq（数据写完才提交，读方凭此感知新帧）。"""
        return self._fb.write(frame)

    # ---- 读方（UI/Monitor） ----

    def read(self):
        """返回 (seq, frame3d) 或 (None, None)（写方未就绪时静默跳过）。

        _FrameBuffer 展平存储（BGR 存为 (h, w*3)），按 frame_shape reshape 回 3D。
        """
        try:
            seq, img = self._fb.read()
        except Exception:
            return None, None
        if img is not None and img.ndim == 2 and self.frame_shape:
            h, w = self.frame_shape
            if img.shape == (h, w * 3):
                img = img.reshape(h, w, 3)
        return seq, img

    def read_seq(self):
        """只读 seq（FPS 统计等轻量场景）。"""
        try:
            seq, _ = self._fb.read()
            return seq
        except Exception:
            return None


# ---------- 运行监控：槽 seq FPS / 子进程 MEM / 线程栈 ----------

class Monitor:
    """运行监控：显示槽 seq 增量统计 FPS + 周期性 [FPS]/[MEM]/线程栈日志。

    FPS 按数据源（algo_key）统计：写方每刷新槽一次 seq +1，读方增量/时间
    即真实帧率（无需信号）。数据源通过 gData_user 鸭子类型注入
    （需含 algo_keys / display_slots / fps_stats / executors / cameraList /
    run_mode 字段，框架 build_processes 体系与 FlowFourCam 结构兼容）。
    """

    def __init__(self, gData_user, fps_interval=2.0, mem_interval=5.0,
                 dump_interval=5.0):
        self.user = gData_user
        self.fps_interval = fps_interval
        self.mem_interval = mem_interval
        self.dump_interval = dump_interval
        self._fps_t0 = 0.0
        self._mem_t0 = 0.0
        self._dump_t0 = 0.0
        self._last_seq = {}   # algo_key -> 上次 seq（从显示槽读取）

    def _sample_fps(self):
        """读各窗格显示槽 seq 增量 → fps_stats（写方刷新率 = 真实处理率）。"""
        now = time.time()
        for key in getattr(self.user, "algo_keys", []) or []:
            slots = getattr(self.user, "display_slots", {}).get(key)
            if slots is None:
                continue
            seq = slots["res"].read_seq()
            if seq is None:
                continue
            last = self._last_seq.get(key)
            st = self.user.fps_stats.setdefault(
                key, {"count": 0, "t0": now, "fps": 0.0, "last_seq": 0})
            if last is not None and seq > last:
                st["count"] += seq - last
            self._last_seq[key] = seq
            if now - st["t0"] >= 1.0:
                st["fps"] = st["count"] / (now - st["t0"])
                st["count"] = 0
                st["t0"] = now

    def tick(self, now=None):
        """周期日志：每 2s [FPS]、每 5s [MEM]、线程模式每 5s 线程栈。"""
        now = now or time.time()
        if now - self._fps_t0 >= self.fps_interval:
            self._fps_t0 = now
            self._sample_fps()
            keys = getattr(self.user, "algo_keys", None) or \
                   getattr(self.user, "cameraList", []) or []
            fps_str = " ".join(
                "%s=%.1f" % (key, self.user.fps_stats.get(key, {}).get("fps", 0.0))
                for key in keys)
            print("[FPS] %s" % fps_str, flush=True)
        if now - self._mem_t0 >= self.mem_interval:
            self._mem_t0 = now
            self._dump_mem()
        if getattr(self.user, "run_mode", "") == "thread" and \
                now - self._dump_t0 >= self.dump_interval:
            self._dump_t0 = now
            self._dump_threads()

    def _dump_mem(self):
        """各子进程 RSS（executors 结构：camera 单执行器 / algo 执行器列表）。"""
        try:
            import psutil as _ps
            mems = []
            algo_keys = getattr(self.user, "algo_keys", []) or []
            for cam in getattr(self.user, "cameraList", []) or []:
                exs = getattr(self.user, "executors", {}).get(cam, {})
                for ex, label in [((exs.get("camera"), "camera"))] + \
                                 [(e, algo_keys[i] if i < len(algo_keys) else "algo%d" % i)
                                  for i, e in enumerate(exs.get("algo", []))]:
                    if ex and ex.proc and ex.proc.is_alive():
                        try:
                            mems.append("%s=%.0fMB" % (
                                label, _ps.Process(ex.proc.pid).memory_info().rss / 1e6))
                        except Exception:
                            pass
            print("[MEM] %s" % " ".join(mems), flush=True)
        except Exception:
            pass

    def _dump_threads(self):
        import sys as _sys
        import traceback as _tb
        frames = _sys._current_frames()
        alive = [th for th in threading.enumerate() if th.is_alive()]
        print("---- 存活线程数 %d ----" % len(alive), flush=True)
        for th in alive:
            print("== 线程 %s (ident=%s) ==" % (th.name, th.ident), flush=True)
            f = frames.get(th.ident)
            if f is None:
                print("  (无栈帧)", flush=True)
                continue
            for line in _tb.format_stack(f):
                print("  " + line.strip(), flush=True)


# ================= 通用管线：spec 单步配置 / 图解释器 / 配置工具 =================
# （集成自 FlowFourCam services：pipeline + spec_tool，框架级通用组件）

# ---------- SpecBuilder：单步配置生成完整 pipeline_spec ----------

class PipelineSpecBuilder:
    """pipeline_spec 单步配置器：一步步添加节点/通道/窗格，build() 生成完整 spec。

    用法（链式）：
        spec = (PipelineSpecBuilder("process")
                .add_node("grabber_1", flow="camera", source="videos/ccd1.avi")
                .add_node("algo_1", flow="algo", algo_load=1)
                .add_channel("ch_grabber_1_algo_1", "grabber_1", "algo_1",
                             kind="queue", maxlen=1, overflow="drop_oldest")
                .add_channel("ch_algo_1_res", "algo_1", "ui",
                             kind="shm", slot="res")
                .add_pane("pane_algo_1", origin="ch_grabber_1_origin",
                          res="ch_algo_1_res")
                .build())
    生成的 spec 可注册进 PipelineManager 或 export 为 JSON。
    """

    def __init__(self, run_mode="process", **globals_):
        self._spec = {
            "run_mode": run_mode,
            "cam_affinity": None,
            "algo_affinity": None,
            "cam_priority": None,
            "algo_priority": None,
            "nodes": [],
            "channels": [],
            "panes": [],
        }
        for k, v in globals_.items():
            if k in self._spec:
                self._spec[k] = v

    # ---- 单步配置（每步返回 self，可链式） ----

    def add_node(self, node_id, flow, **params):
        """添加流程实例节点（flow = 项目流程名；params 原样注入进程）。"""
        self._spec["nodes"].append(dict({"id": node_id, "flow": flow}, **params))
        return self

    def add_channel(self, ch_id, from_node, to_node, kind="queue", **params):
        """添加数据通道（kind=queue 队列 / shm 内存映射；to 可为 "ui"）。"""
        self._spec["channels"].append(dict(
            {"id": ch_id, "from": from_node, "to": to_node, "kind": kind}, **params))
        return self

    def add_pane(self, pane_id, origin, res, node=None):
        """添加显示窗格（origin/res 为通道 id，UI 勾选切换；node 关联结果信号源）。"""
        self._spec["panes"].append({"id": pane_id, "origin": origin, "res": res,
                                    "node": node})
        return self

    # ---- 查询 / 生成 ----

    def nodes(self):
        return list(self._spec["nodes"])

    def channels(self):
        return list(self._spec["channels"])

    def panes(self):
        return list(self._spec["panes"])

    def build(self):
        """校验并返回完整 spec。"""
        validate_pipeline_spec(self._spec)
        return self._spec

    def export(self, path=None):
        """序列化为 JSON（path 给出时写文件）。"""
        return export_pipeline_spec(self._spec, path)


def make_pipeline_spec(camera_nodes, algo_nodes, run_mode="process", **globals_):
    """快捷生成「相机 → 算法」拓扑（队列通道 + 显示通道 + 窗格自动装配）。

    camera_nodes: {"grabber_1": {"flow": "camera", "source": "videos/ccd1.avi", ...}}
    algo_nodes:   {"algo_1": {"flow": "algo", "algo_load": 1, ...}}
    更复杂拓扑用 PipelineSpecBuilder 单步配置。
    """
    b = PipelineSpecBuilder(run_mode, **globals_)
    for nid, params in camera_nodes.items():
        b.add_node(nid, flow=params.pop("flow", "camera"), **params)
    for nid, params in algo_nodes.items():
        b.add_node(nid, flow=params.pop("flow", "algo"), **params)
    for nid in camera_nodes:
        for aid in algo_nodes:
            b.add_channel("ch_%s_%s" % (nid, aid), nid, aid,
                          kind="queue", maxlen=1, overflow="drop_oldest")
        b.add_channel("ch_%s_origin" % nid, nid, "ui", kind="shm", slot="origin")
    for aid in algo_nodes:
        b.add_channel("ch_%s_res" % aid, aid, "ui", kind="shm", slot="res")
        b.add_pane("pane_%s" % aid, "ch_%s_origin" % next(iter(camera_nodes)),
                   "ch_%s_res" % aid, node=aid)
    return b.build()


# ---------- spec 配置工具：导出 / 导入 / 校验 ----------

def export_pipeline_spec(spec, path=None):
    """pipeline_spec 序列化为 JSON 字符串；path 给出时写文件（UTF-8，缩进 2）。"""
    import json
    text = json.dumps(spec, ensure_ascii=False, indent=2)
    if path:
        import os as _os
        _os.makedirs(_os.path.dirname(_os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def load_pipeline_spec(path):
    """从 JSON 文件加载 pipeline_spec（带校验）。"""
    import json
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    validate_pipeline_spec(spec)
    return spec


def validate_pipeline_spec(spec):
    """校验 pipeline_spec 结构；错误抛 ValueError。返回 True。"""
    if not isinstance(spec, dict):
        raise ValueError("pipeline_spec 必须是 dict")
    errors = []
    node_ids = set()
    for n in spec.get("nodes", []):
        nid = n.get("id")
        if not nid:
            errors.append("节点缺少 id")
            continue
        if nid in node_ids:
            errors.append("节点 id 重复: %r" % nid)
        node_ids.add(nid)
        if not n.get("flow"):
            errors.append("节点 %r 缺少 flow（流程名）" % nid)
    ch_ids = set()
    for c in spec.get("channels", []):
        cid = c.get("id")
        if cid in ch_ids:
            errors.append("通道 id 重复: %r" % cid)
        ch_ids.add(cid)
        if c.get("from") not in node_ids and c.get("to") != "ui":
            errors.append("通道 %r from 节点 %r 未定义" % (cid, c.get("from")))
        if c.get("to") not in node_ids and c.get("to") != "ui":
            errors.append("通道 %r to 节点 %r 未定义" % (cid, c.get("to")))
        if c.get("kind") not in ("queue", "shm"):
            errors.append("通道 %r kind 必须是 queue/shm（当前 %r）"
                          % (cid, c.get("kind")))
    for p in spec.get("panes", []):
        for key in ("origin", "res"):
            if p.get(key) not in ch_ids:
                errors.append("窗格 %r 引用未定义的通道 %r" % (p.get("id"), p.get(key)))
    if errors:
        raise ValueError("pipeline_spec 校验失败:\n  " + "\n  ".join(errors))
    return True


# ---------- 聚合通道：节点输入/输出的统一入口（channel_in / channel_out） ----------

class _ChannelIn:
    """聚合读通道：从第一个有数据的 in 通道取数据（队列 get）。"""

    def __init__(self, channels):
        self._chs = list(channels)

    def get(self, timeout=None):
        for ch in self._chs:
            if hasattr(ch, "get"):
                return ch.get(timeout=timeout)
        return None


class _ChannelOut:
    """聚合写通道：put 写队列（每帧），write 写映射（throttle 降频，内部计数）。

    节点代码统一入口，不关心通道类型/数量：
        thData.channel_out.put(frame)              # 队列通道（每帧发送）
        thData.channel_out.write(res, throttle=2)  # 映射通道（每 N 次写一次）
    """

    def __init__(self, channels):
        self._chs = list(channels)
        self._wcount = 0

    def put(self, data):
        for ch in self._chs:
            if hasattr(ch, "put"):
                ch.put(data)

    def write(self, data, throttle=1):
        self._wcount += 1
        if self._wcount % max(1, throttle) != 0:
            return
        for ch in self._chs:
            if hasattr(ch, "write"):
                ch.write(data)


# ---------- PipelineManager：pipeline_spec（通用流程图）解释器 ----------

class PipelineManager:
    """pipeline_spec 解释器：任意流程 + 声明式通道的拓扑装配。

    图模型（不假设相机/算法流程——节点是任意流程实例，联通方式按需求声明）：
        nodes:    流程实例 {"id", "flow"(流程名), ...参数}——参数原样注入进程
        channels: 数据通道 {"id", "from", "to", "kind", ...参数}
                  kind="queue"  DataBus 队列：from 节点注入 ch_<id>_out（写），
                                to 节点注入 ch_<id>_in（读）；槽位按帧尺寸自适应
                  kind="shm"    DisplaySlot 内存映射（槽名=通道 id）：from 写；
                                to="ui" 时按 slot 角色进显示系统
        panes:    显示窗格 {"id", "origin"(通道), "res"(通道)}——UI 勾选切换
        flow_dir: 节点 source 相对路径基准（缺省 ""）

    依赖注入：
        - gData：框架保证存在（thCtrls/proCtrls），可直接用
        - spec：管线配置，显式传入；state：运行态容器，显式传入
          （管理器只写约定字段：run_mode/pane_list/algo_keys/display_slots/
            executors/frame_shape/buses，不假设字段已存在）
    """

    def __init__(self, gData, signal_instance, spec, state):
        self.gData = gData
        self.spec = spec
        self.state = state
        self.signal_instance = signal_instance
        self._relay_stop = threading.Event()
        self._relay_threads = []
        self.started = False

    # state 读写封装（鸭子类型：getattr/setattr，不假设字段存在）
    def _state_set(self, key, value):
        setattr(self.state, key, value)

    def _state_get(self, key, default=None):
        return getattr(self.state, key, default)

    # ---------- 启动 ----------

    def start(self):
        spec = self.spec
        run_mode = spec.get("run_mode", "process")
        self._state_set("run_mode", run_mode)
        # 流程级默认解释器：spec 顶层 python_exe（如 "D:/AIProgram/python.exe"）
        # 未显式配置的进程流程用它拉起子进程；节点级 python_exe 走 kwargs 透传覆盖
        _ext_py = spec.get("python_exe")
        if _ext_py:
            for _st in getattr(self.gData, "proCtrls", {}).values():
                if not getattr(_st, "python_exe", None):
                    _st.python_exe = _ext_py
        # 节点级运行方式：节点可单独 mode="process"/"thread"（缺省继承全局 run_mode）。
        # 通道模式由读写双方决定：任一方是进程 → 通道必须走共享内存（process 模式）；
        # 双方都是线程 → 可用线程队列（同进程内引用传递）。
        node_mode = {n["id"]: n.get("mode", run_mode) for n in spec.get("nodes", [])}
        nodes = spec.get("nodes", [])
        channels = spec.get("channels", [])
        panes = spec.get("panes", [])
        flow_dir = spec.get("flow_dir", "")

        # 派生运行时字段（UI/监控按此组织；窗格 = 显示单元；
        # algo_keys 为 pane_list 别名——框架 Monitor 兼容读取；
        # pane_nodes: pane_id -> 结果信号源节点 id（UI 信号路由过滤用）
        self._state_set("pane_list", [p["id"] for p in panes])
        self._state_set("algo_keys", [p["id"] for p in panes])
        self._state_set("pane_nodes",
                        {p["id"]: p.get("node") for p in panes})
        self._state_set("display_slots", {})
        self._state_set("executors", {})
        self._state_set("frame_shape", None)

        buses = self._state_get("buses", {})
        display_slots = self._state_get("display_slots", {})
        executors = self._state_get("executors", {})
        fs = self._state_get("frame_shape")
        pane_list = self._state_get("pane_list", [])

        channel_inject = {}   # node_id -> kwargs（通道对象注入）
        in_of = {}    # node_id -> [读通道]（聚合 channel_in）
        out_of = {}   # node_id -> [写通道]（聚合 channel_out）

        # 帧尺寸探测（有 source 的节点）：queue 槽位自适应 + 显示槽 reshape
        for n in nodes:
            src = n.get("source")
            if src:
                shape = frame_shape(os.path.join(flow_dir, src))
                if shape:
                    fs = shape
                    break
        frame_size = (fs[0] * fs[1] * 3 + 256 * 1024) if fs else None

        # ---- 1. 通道装配（按 kind 建传输，注入读写双方） ----
        for ch in channels:
            cid = ch["id"]
            kind = ch["kind"]
            if kind == "queue":
                # DataBus 队列：from 写 / to 读（槽位按帧尺寸自适应）
                # 通道模式 = 任一方进程 → 共享内存；双方线程 → 线程队列
                ch_mode = ("process" if node_mode.get(ch["from"]) == "process"
                           or node_mode.get(ch["to"]) == "process" else "thread")
                bus = DataBus(name=cid, maxlen=ch.get("maxlen", 1), mode=ch_mode,
                              overflow=ch.get("overflow", "drop_oldest"),
                              max_obj_size=ch.get("max_obj_size") or frame_size)
                buses[cid] = bus
                channel_inject.setdefault(ch["from"], {})["ch_%s_out" % cid] = bus
                channel_inject.setdefault(ch["to"], {})["ch_%s_in" % cid] = bus
                out_of.setdefault(ch["from"], []).append(bus)
                in_of.setdefault(ch["to"], []).append(bus)
            elif kind == "shm":
                # 内存映射（DisplaySlot）：槽名 = 通道 id（唯一）；
                # 多窗格引用同一通道 = 共享同一段；from 写，to="ui" 时进显示系统
                slot = ch.get("slot", "res")
                fb_slot = DisplaySlot(cid, fs)
                channel_inject.setdefault(ch["from"], {})["ch_%s_out" % cid] = fb_slot
                out_of.setdefault(ch["from"], []).append(fb_slot)
                if ch["to"] == "ui":
                    for p in panes:
                        if p.get("origin") == cid:
                            display_slots.setdefault(p["id"], {})["origin"] = fb_slot
                        if p.get("res") == cid:
                            display_slots.setdefault(p["id"], {})["res"] = fb_slot
                    if not any(p.get("origin") == cid or p.get("res") == cid
                               for p in panes):
                        display_slots[cid] = {"origin" if slot == "origin"
                                              else "res": fb_slot}

        # ---- 2. 节点启动（任意流程名，参数 + 聚合通道注入） ----
        for n in nodes:
            nid = n["id"]
            kwargs = {k: v for k, v in n.items() if k not in ("id", "flow")}
            kwargs.update(channel_inject.get(nid, {}))
            if in_of.get(nid):
                kwargs["channel_in"] = _ChannelIn(in_of[nid])
            if out_of.get(nid):
                kwargs["channel_out"] = _ChannelOut(out_of[nid])
            kwargs["cam_str"] = nid
            kwargs["algo_key"] = nid
            flow = n["flow"]
            mode = node_mode[nid]
            kwargs.setdefault("mode", mode)   # 节点模式注入 thData（数据点自动探测用）
            if mode == "process":
                ex = self.gData.proCtrls[flow].start(**kwargs)
            else:
                ex = self.gData.thCtrls[flow].start(**kwargs)
            executors[nid] = ex
            print("已启动 %s（flow=%s，%s）" % (nid, flow, mode), flush=True)

        # 写回运行态
        self._state_set("buses", buses)
        self._state_set("display_slots", display_slots)
        self._state_set("executors", executors)
        self._state_set("frame_shape", fs)
        self._state_set("pane_list", pane_list)

        if run_mode == "process":
            self._start_relay()
        self.started = True
        return self

    # ---------- 信号 relay（进程模式） ----------

    def _start_relay(self):
        relay = _SignalRelay(self.signal_instance)

        def _loop(conn, label):
            while not self._relay_stop.is_set():
                try:
                    if not conn.poll(0.05):
                        continue
                    msg = conn.recv()
                except (EOFError, BrokenPipeError):
                    break
                if msg[0] == "signal":
                    relay.run_once_from_msg(msg)
                elif msg[0] == "status":
                    print("[main] %s status: %s" % (label, msg[1:]), flush=True)

        for nid, ex in self._state_get("executors", {}).items():
            if not hasattr(ex, "conn"):
                continue                 # 线程执行器：信号主进程内直连，无需 relay
            t = threading.Thread(target=_loop, args=(ex.conn, nid), daemon=True)
            t.start()
            self._relay_threads.append(t)
        print("relay 线程已启动（%d 条）" % len(self._relay_threads), flush=True)

    # ---------- 停止 ----------

    def stop(self):
        """优雅停止：停 relay → 终止所有执行器 → 清理共享内存孤儿段。"""
        self._relay_stop.set()
        for ex in self._state_get("executors", {}).values():
            if ex is None:
                continue
            try:
                ex.stop()
            except Exception:
                pass
        try:
            cleanup_all_segments()
        except Exception:
            pass
        self.started = False
        print("管线已停止", flush=True)
