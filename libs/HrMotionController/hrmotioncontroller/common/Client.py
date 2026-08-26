import socket
import time
import json
import uuid
from threading import Thread, Event
import traceback 
from .Motion import MotionBase, AxisBase, MotionStatus, AxisStatus

_debug = False  # Global debug flag, can be set to True for debugging purposes

class ParseSocketJson:
    def __init__(self, callback=None):
        self._tempMsg = b""
        self._callback = callback  # Optional callback for processing JSON data

    def register_callback(self, callback):
        """Register a callback function to process JSON data."""
        self._callback = callback

    def handle_received_msg(self, message:bytes):
        if message != '':
            if self._tempMsg != "":
                message = self._tempMsg + message
            ret, strJsons, remain, middle = self._split_json(message)
            if ret == 0:
                for _str in strJsons:
                    try:
                        _json = json.loads(_str)
                        if callable(self._callback):
                            self._callback(_json)
                        self._tempMsg = remain.encode('utf-8')
                    except Exception as e:
                        self._tempMsg = message
                        # traceback.print_exc()
            elif ret == 1:
                self._tempMsg = message
                             
    def _split_json(self, str:bytes):
        _list = []
        remain = ''
        middle = []
        _ret = -1
        try:
            message = str.decode('utf-8')
        except Exception as ex:
            pass
            # print(str)
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
    
class SocketJsonBase:
    def __init__(self):
        self._parse = ParseSocketJson(self.process_jsondata)
    
    def process_jsondata(self, json_data):
        """Process the received JSON data."""
        # This method should be overridden in subclasses to handle the JSON data.
        pass
    
    def handle_received_msg(self, message:bytes):
        self._parse.handle_received_msg(message)
                
class ClientBase:
    def __init__(self, ip='127.0.0.1', port=8080):
        self.ip = ip
        self.port = port
        self.socket = None
        
    def __del__(self):
        """Ensure the socket is closed when the object is deleted."""
        if self.is_connected():
            self.close()

    def set_ip(self, ip):
        """Set the IP address of the server."""
        self.ip = ip
        
    def set_port(self, port):
        """Set the port of the server."""
        self.port = port
        
    def set_host(self, ip, port):
        """Set the host address (IP and port) of the server."""
        self.ip = ip
        self.port = port
        
    def get_host(self):
        """Get the current host address (IP and port) of the server."""
        return self.ip, self.port

    def is_connected(self):
        """Check if the socket is connected to the server."""
        if self.socket:
            try:
                self.socket.getpeername()
                return True
            except (socket.error, OSError):
                return False
        return False

    def connect(self):
        """Establish a connection to the server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            if _debug:
                print(f"Connected to server at {self.ip}:{self.port}")
        except (socket.error, ConnectionRefusedError) as e:
            if _debug:
                print(f"Connection failed: {e}.")

    def send(self, message:str):
        """Send a message to the server."""
        try:
            self.socket.send(message.encode('utf-8'))
        except (socket.error, BrokenPipeError):
            if _debug:
                print("Connection lost.")

    def receive(self, buffer_size=1024):
        """Receive a message from the server."""
        try:
            return self.socket.recv(buffer_size)
        except (socket.error, BrokenPipeError):
            if _debug:
                print("Connection lost...")
            return None

    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            self.socket = None
            if _debug:
                print("Connection closed.")

class IPC_Client(ClientBase, SocketJsonBase):
    def __init__(self, ip='127.0.0.1', port=8080, **kwargs):
        ClientBase.__init__(self, ip, port)
        SocketJsonBase.__init__(self)
        
        self._retry_gaptime = kwargs.get('retry_gaptime', 1)
        self._receive_buffer_size = kwargs.get('buffer_size', 1024)
        self._receive_thread:Thread = None
        
        self._receive_events = {'data_change': self.__data_change_handler}
        
        self._execute_waitevents:dict[str,Event] = {}
        self._execute_datas:dict[str,dict] = {}
        
    def register_event_handler(self, event_name:str, handler):
        """Register an event handler for a specific event."""
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self._receive_events[event_name] = handler
        
    def unregister_event_handler(self, event_name:str):
        """Unregister an event handler for a specific event."""
        if event_name in self._receive_events:
            del self._receive_events[event_name]
        else:
            if _debug:
                print(f"No handler registered for event: {event_name}")
    
    def clear_event_handlers(self):
        """Clear all registered event handlers."""
        self._receive_events.clear()
        if _debug:
            print("All event handlers cleared.")
        
    def connect(self):
        """Establish a connection to the server and start the receive thread."""
        super().connect()
        if self.is_connected():
            self._connected_event()
      
    def close(self):
        for uuid_str in self._execute_waitevents.keys():
            if self._execute_waitevents[uuid_str].is_set() is False:
                self._execute_waitevents[uuid_str].set()
        self._execute_waitevents = {}
        self._execute_datas = {}
        super().close()
      
    def wait_for_connection(self, timeout=10):
        """Wait for the connection to be established."""
        start_time = time.time()
        while not self.is_connected():
            if time.time() - start_time > timeout:
                if _debug:
                    print("Connection timed out.")
                return False
            self.connect()
        if _debug:
            print("Connection established successfully.")
        return True
        
    def send_request(self, json_data:dict):
        """Send a request to the server with the specified JSON data."""
        self.send(json.dumps(json_data))

    def execute_request(self, json_data:dict, timeout=2000):
        """Execute a request and wait for a response."""
        if 'uuid' not in json_data:
            json_data['uuid'] = uuid.uuid4().hex
        uuid_str = json_data['uuid']
        if uuid_str not in self._execute_waitevents:
            self._execute_waitevents[uuid_str] = Event()
        if uuid_str not in self._execute_datas:
            self._execute_datas[uuid_str] = {}
        
        self.send_request(json_data)
        
        ret = self._execute_waitevents[uuid_str].wait(timeout / 1000)
        if ret:
            data = self._execute_datas[uuid_str]
            if 'success' in data and data['success']:
                ret = True
            else:
                ret = False
            # if _debug:
                # print(f"Request {uuid_str} executed successfully.")
        else:
            data = 'timed out'
            if _debug:
                print(f"Request {uuid_str} timed out after {timeout} milliseconds.")

        del self._execute_waitevents[uuid_str]
        del self._execute_datas[uuid_str]
        return ret, data
        
    def _receive_message_loop(self):
        while self.is_connected():
            try:
                message = self.receive(self._receive_buffer_size)
                if message:
                    self.handle_received_msg(message)
                else:
                    if _debug:
                        print("No message received, connection might be lost.")
                    self.close()  # Close the connection if no message is received
            except Exception as e:
                if _debug:
                    print(f"Error receiving message: {e}")
                Event().wait(self._retry_gaptime)  # Wait before retrying
                
    def _connected_event(self):
        """Event triggered when the client connects to the server."""
        if _debug:
            print("Client connected to server.")
        self._receive_thread = Thread(target=self._receive_message_loop, daemon=True)
        self._receive_thread.start()

    def process_jsondata(self, json_data):
        if 'uuid' in json_data:
            uuid_str = json_data['uuid']
            if uuid_str in self._execute_waitevents:
                self._execute_datas[uuid_str] = json_data
                self._execute_waitevents[uuid_str].set()
                if _debug:
                    print(f"Response received for request {json_data}.")
            else:
                if _debug:
                    print(f"Received response for unknown request {json_data}.")

        if 'header' in json_data:
            if json_data['header'] in self._receive_events:
                receive_event = self._receive_events[json_data['header']]
                if callable(receive_event):
                    try:
                        receive_event(json_data)
                    except:
                        if _debug:
                            traceback.print_exc()
    
    def read_data(self, name, timeout=2000) -> float:
        """
        获取数据映射的值
        :param name: 数据映射名称
        :return: 数据映射值
        """
        ret, msg = self.execute_request({
            "header": "datamap_read",
            "key": name
        }, timeout)
        if not ret:
            raise RuntimeError(f"Failed to read data map '{name}'. Error: {msg}.")
        if 'data' in msg:
            return msg['data']
        else:
            if _debug:
                print(f"Data map '{name}' not found in response.")
            raise KeyError(f"Data map '{name}' not found in response.")
        
    def write_data(self, name, value, timeout=2000):
        """
        设置数据映射的值
        :param name: 数据映射名称
        :param value: 数据映射值
        :return: None
        """
        ret, msg = self.execute_request({
            "header": "datamap_write",
            "key": name,
            "value": value
        }, timeout)
        if not ret:
            raise RuntimeError(f"Failed to write data map '{name}' with value {value}. Error: {msg}.")
        if _debug:
            print(f"Data map '{name}' set to {value} successfully.")
            
    def set_data(self, datamap, timeout=2000):
        """
        批量设置数据映射的值
        :param datamap: 数据映射字典
        :return: None
        """
        ret, msg = self.execute_request({
            "header": "datamap_set",
            "data": datamap
        }, timeout)
        if not ret:
            raise RuntimeError(f"Failed to set data map. Error: {msg}.")
        if _debug:
            print(f"Data map set successfully: {datamap}.")
        
    def get_data(self, names, timeout=2000) -> dict:
        """
        批量获取数据映射的值
        :param names: 数据映射名称列表
        :return: 数据映射值字典
        """
        ret, msg = self.execute_request({
            "header": "datamap_get",
            "keys": names
        }, timeout)
        if not ret:
            raise RuntimeError(f"Failed to get data map for keys {names}. Error: {msg}.")
        if 'data' in msg:
            return msg['data']
        else:
            if _debug:
                print(f"Data map not found in response for keys {names}.")
            raise KeyError(f"Data map not found in response for keys {names}.")

    def __data_change_handler(self, json_data:dict):
        if 'key' in json_data and 'value' in json_data:
            key = json_data['key']
            value = json_data['value']
            self.data_change_handler(key, value)

    def data_change_handler(self, key, value):
        """Handle data change events."""
        pass

class AxisClient(AxisBase):
    def __init__(self, axis_number, client:'MotionClient', status=None):
        AxisBase.__init__(self, axis_number)
        self._client = client
        if status is None:
            status = AxisStatus()
            self._axis_isinitialized = False
        else:
            self._axis_isinitialized = True
        self._status = status
        
    def set_status(self, data:dict):
        """Set the status of the axis."""
        for key, value in data.items():
            if hasattr(self._status, key):
                setattr(self._status, key, value)
            else:
                if _debug:
                    print(f"Unknown status attribute: {key}")
        if not self._axis_isinitialized:
            self._axis_isinitialized = True
        
    def init(self, **kwargs):
        info = {
            "header": "axis_init",
            "axis_id": self.axis_id,
            "params": kwargs
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to initialize axis {self.axis_id}.")
    
    def is_enabled(self) -> bool:
        """
        检查轴是否已启用
        :return: True 如果轴已启用，否则 False
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before checking enabled state.")
        
        return self._status.enabled
    
    def enable(self, **kwargs):
        """
        启用轴
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before enabling.")
        
        info = {
            "header": "axis_enable",
            "axis_id": self.axis_id,
            "params": kwargs
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to enable axis {self.axis_id}.")
        
        if _debug:
            print(f"Enabling axis {self.axis_id} with params: {kwargs}")
    
    def disable(self, **kwargs):
        """
        禁用轴
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before disabling.")
        
        info = {
            "header": "axis_disable",
            "axis_id": self.axis_id,
            "params": kwargs
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to disable axis {self.axis_id}.")
        
        if _debug:
            print(f"Disabling axis {self.axis_id} with params: {kwargs}")
    
    def setvalue(self, **kwargs):
        """
        设置轴的参数
        :param kwargs: 参数字典
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before setting values.")
        
        info = {
            "header": "axis_setvalue",
            "axis_id": self.axis_id,
            "params": kwargs
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to set values for axis {self.axis_id}.")
        
        if _debug:
            print(f"Setting values for axis {self.axis_id} with params: {kwargs}")
    
    def getvalue(self, key, **kwargs):
        """
        获取轴的参数值
        :param key: 参数名称
        :param kwargs: 可选的其他参数
        :return: 参数值
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting values.")
        
        info = {
            "header": "axis_getvalue",
            "axis_id": self.axis_id,
            "key": key,
            "params": kwargs
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to get value '{key}' for axis {self.axis_id}.")
        
        if _debug:
            print(f"Getting value '{key}' for axis {self.axis_id} with params: {kwargs}")
    
    def idle(self) -> bool:
        """
        检查轴是否处于空闲状态
        :return: True 如果轴处于空闲状态，否则 False
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before checking idle state.")

        return self._status.idle

    def get_idle(self) -> int:
        """
        获取轴的IDLE状态值
        :return: IDLE状态值(-1 表示空闲)
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before checking idle state.")

        return -1 if self._status.idle else 0

    def get_axis_status(self) -> int:
        """
        获取轴的运行状态值
        :return: 运行状态值(0 表示就绪)
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before checking axis status.")

        return 0 if self._status.idle else 1
    
    def home(self):
        """
        回零轴
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before homing.")
        
        info = {
            "header": "axis_home",
            "axis_id": self.axis_id
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to home axis {self.axis_id}.")
        
        if _debug:
            print(f"Homing axis {self.axis_id}.")

    def is_homed(self) -> bool:
        """
        检查轴是否已归零
        :return: True 如果轴已归零，否则 False
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before checking homed state.")
        
        return self._status.homed

    def move_absolute(self, position: float, velocity: float):
        """
        绝对移动
        :param position: 目标位置
        :param velocity: 移动速度
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before moving.")
        
        info = {
            "header": "axis_move_absolute",
            "axis_id": self.axis_id,
            "position": position,
            "velocity": velocity
        }
        
        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to move axis {self.axis_id} to absolute position {position} Error: {msg}.")
        
        if _debug:
            print(f"Moving axis {self.axis_id} to absolute position {position} with velocity {velocity} Error: {msg}.")
    
    def move_relative(self, distance: float, velocity: float):
        """
        相对移动
        :param distance: 相对距离
        :param velocity: 移动速度
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before moving.")
        
        info = {
            "header": "axis_move_relative",
            "axis_id": self.axis_id,
            "distance": distance,
            "velocity": velocity
        }
        
        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to move axis {self.axis_id} relative by {distance} Error: {msg}.")
        
        if _debug:
            print(f"Moving axis {self.axis_id} relative by {distance} with velocity {velocity} Error: {msg}.")

    def continuous_move(self, direction, velocity):
        """
        连续移动
        :param direction: 移动方向（正向或负向）
        :param velocity: 移动速度
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before moving.")
        
        info = {
            "header": "axis_continuous_move",
            "axis_id": self.axis_id,
            "direction": direction,
            "velocity": velocity
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to continuously move axis {self.axis_id} in {direction} direction with velocity {velocity}.")
        
        if _debug:
            print(f"Continuously moving axis {self.axis_id} in {direction} direction with velocity {velocity}.")

    def stop(self):
        """
        停止轴的运动
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before stopping.")
        
        info = {
            "header": "axis_stop",
            "axis_id": self.axis_id
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to stop axis {self.axis_id}.")
        
        if _debug:
            print(f"Stopping axis {self.axis_id}.")

    def get_dpos(self) -> float:
        """
        获取当前轴的目标位置
        :return: 当前轴的目标位置
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting position.")
        
        return self._status.dpos
    
    def get_mpos(self) -> float:
        """
        获取当前轴的实际位置
        :return: 当前轴的实际位置
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting position.")
        
        return self._status.mpos

    def get_dpos(self) -> float:
        """
        获取当前轴的目标位置
        :return: 当前轴的目标位置
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting position.")
        
        return self._status.dpos

    def set_mpos(self, position: float):
        """
        设置当前轴的实际位置
        :param position: 要设置的实际位置
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before setting position.")
        
        info = {
            "header": "axis_set_mpos",
            "axis_id": self.axis_id,
            "position": position
        }
        
        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to set actual position for axis {self.axis_id} to {position}.")
        
        if _debug:
            print(f"Setting axis {self.axis_id} actual position to {position}.")

    def get_velocity(self) -> float:
        """
        获取当前轴的速度
        :return: 当前轴的速度
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting velocity.")
        
        return self._status.velocity
    
    def set_velocity(self, velocity: float):
        """
        设置当前轴的速度
        :param velocity: 要设置的速度
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before setting velocity.")

        info = {
            "header": "axis_set_velocity",
            "axis_id": self.axis_id,
            "velocity": velocity
        }

        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to set velocity for axis {self.axis_id} to {velocity}.")

        if _debug:
            print(f"Setting axis {self.axis_id} velocity to {velocity}.")

    def set_soft_limit(self, min_position: float = None, max_position: float = None):
        """
        设置轴的软极限
        :param min_position: 最小位置限制
        :param max_position: 最大位置限制
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before setting soft limit.")

        info = {
            "header": "axis_set_soft_limit",
            "axis_id": self.axis_id,
            "min_position": min_position,
            "max_position": max_position
        }

        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to set soft limit for axis {self.axis_id}.")

        if _debug:
            print(f"Setting axis {self.axis_id} soft limit to min={min_position}, max={max_position}.")

    def get_soft_limit(self) -> tuple:
        """
        获取轴的软极限
        :return: (min_position, max_position) 元组
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting soft limit.")

        info = {
            "header": "axis_get_soft_limit",
            "axis_id": self.axis_id
        }

        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to get soft limit for axis {self.axis_id}.")

        data = msg.get('data', {})
        return data.get('min_position'), data.get('max_position')

    def get_alarm(self) -> int:
        """
        获取轴的报警信号状态
        :return: 报警信号状态值(0 表示无报警)
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting alarm.")

        info = {
            "header": "axis_get_alarm",
            "axis_id": self.axis_id
        }

        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to get alarm for axis {self.axis_id}.")

        return msg.get('data', 0)

    def get_stop_reason(self) -> int:
        """
        获取轴的停止原因(位掩码,不同位表示不同状态)
        :return: 停止原因值
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting stop reason.")

        info = {
            "header": "axis_get_stop_reason",
            "axis_id": self.axis_id
        }

        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to get stop reason for axis {self.axis_id}.")

        return msg.get('data', 0)

    def get_hard_limit(self) -> tuple:
        """
        获取正/反向硬限位的输入口编号及当前电平
        :return: ((正向输入口编号, 正向电平), (反向输入口编号, 反向电平)),未配置的输入口编号为 None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before getting hard limit.")

        info = {
            "header": "axis_get_hard_limit",
            "axis_id": self.axis_id
        }

        ret, msg = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to get hard limit for axis {self.axis_id}.")

        data = msg.get('data', {})
        fwd = data.get('fwd', {})
        rev = data.get('rev', {})
        return (fwd.get('port'), fwd.get('level')), (rev.get('port'), rev.get('level'))

    def pause(self):
        """
        暂停轴运动
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before pausing.")

        info = {
            "header": "axis_pause",
            "axis_id": self.axis_id
        }

        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to pause axis {self.axis_id}.")

        if _debug:
            print(f"Pausing axis {self.axis_id}.")

    def resume(self):
        """
        继续轴运动
        :return: None
        """
        if not self._axis_isinitialized:
            raise RuntimeError("Axis must be initialized before resuming.")

        info = {
            "header": "axis_resume",
            "axis_id": self.axis_id
        }

        ret, _ = self._client.execute_request(info)
        if not ret:
            raise RuntimeError(f"Failed to resume axis {self.axis_id}.")

        if _debug:
            print(f"Resuming axis {self.axis_id}.")

class MotionClient(IPC_Client, MotionBase):
    def __init__(self, ip='127.0.0.1', port=8080, **kwargs):
        IPC_Client.__init__(self, ip, port)
        
        self._scan_interval = kwargs.get('scan_interval', 0.3)
        self._scan_thread:Thread = None
        self._scan_event = Event()
        
        self._status = MotionStatus()
        self.axis = {}
        
        self._motion_isinitialized = False
        self.register_event_handler('motion_status', self.on_receive_motion_status)
        
        self._execute_waitevents:dict[str,Event] = {}
        self._execute_datas:dict[str,dict] = {}
        
    @property
    def motion_status(self) -> MotionStatus:
        """Get the current motion status."""
        return self._status
        
    def set_scan_interval(self, interval: float):
        """Set the interval for scanning updates from the server."""
        if interval > 0:
            self._scan_interval = interval
            if _debug:
                print(f"Scan interval set to {self._scan_interval} seconds.")
        else:
            raise ValueError("Scan interval must be greater than 0.")
        
    def wait_for_initialization(self, timeout=10):
        """Wait for the motion status to be initialized."""
        start_time = time.time()
        while not self._motion_isinitialized:
            if time.time() - start_time > timeout:
                if _debug:
                    print("Initialization timed out.")
                return False
            Event().wait(0.1)
        if _debug:
            print("Motion status initialized successfully.")
        return True
             
    def _scan_loop(self):
        """Continuously scan for updates at the specified interval."""
        while self.is_connected():
            try:
                self.send_update_request()
                Event().wait(self._scan_interval)
            except Exception as e:
                if _debug:
                    print(f"Error in scan loop: {e}")
                Event().wait(self._retry_gaptime)
                
    def _connected_event(self):
        """Event triggered when the client connects to the server."""
        super()._connected_event()
        self._scan_thread = Thread(target=self._scan_loop, daemon=True)
        self._scan_thread.start()

    def send_update_request(self):
        info = {
            "header": "motion_status"
        }
        self.send_request(info)
        
    def on_receive_motion_status(self, json_data:dict):
        """Handle the received motion status data."""
        data = json_data.get('data', None)
        if data is not None:
            self._status.from_dict(data)
            # if _debug:
            #     print(f"Motion status updated: {self._status}")
            if not self._motion_isinitialized:
                for axis_number in self._status.axis_table.keys():
                    if axis_number not in self.axis:
                        self.axis[axis_number] = AxisClient(axis_number, self, self._status.axis_state[axis_number])
                self._motion_isinitialized = True
                if _debug:
                    print("Motion status initialized.")
       
    def get_input(self, name) -> int:
        """
        读取输入信号
        :param name: 输入信号名称
        :return: 输入信号值
        """
        if name in self._status.in_state:
            return self._status.in_state[name]
        else:            
            if _debug:
                print(f"Input signal '{name}' not found.")
    
    def get_output(self, name) -> int:
        """
        读取输出信号
        :param name: 输出信号名称
        :return: 输出信号值
        """
        if name in self._status.out_state:
            return self._status.out_state[name]
        else:
            if _debug:
                print(f"Output signal '{name}' not found.")
            raise KeyError(f"Output signal '{name}' not found.")
    
    def set_output(self, name, value):
        """
        设置输出信号
        :param name: 输出信号名称
        :param value: 输出信号值
        """
        if name in self._status.out_table:
            # self._status.out_state[name] = value
            info = {
                "header": "set_output",
                "name": self._status.out_table[name],
                "value": value
            }
            self.send(json.dumps(info))
            if _debug:
                print(f"Set output '{name}' to {value}.")
        else:
            if _debug:
                print(f"Output signal '{name}' not found.")
            raise KeyError(f"Output signal '{name}' not found.")

    def get_all_axis(self) -> dict[object, AxisBase]:
        """
        获取所有轴的编号
        :return: 轴编号列表
        """
        return self.axis
    
    def get_axis(self, axis) -> AxisBase:
        """
        获取指定轴的控制接口
        :param axis: 轴编号
        :return: 轴控制接口
        """
        if axis in self.axis:
            return self.axis[axis]
        else:
            if _debug:
                print(f"Axis {axis} not found.")
            raise KeyError(f"Axis {axis} not found.")
        
if __name__ == "__main__":
    client = MotionClient(ip="127.0.0.1", port=8080)
    client.connect()

    try:
        while True:
            message = input("Enter message to send: ")
            if message.lower() == "exit":
                break
            client.send(message)
            response = client.receive()
            if response:
                print(f"Server response: {response}")
    finally:
        client.close()