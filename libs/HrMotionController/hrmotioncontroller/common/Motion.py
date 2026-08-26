from abc import ABC, abstractmethod
import threading
import time
import pandas as pd

class AxisStatus:
    def __init__(self):
        self.dpos: float = 0.0  # Desired position
        self.mpos: float = 0.0  # Measured position
        self.velocity: float = 0.0  # Current velocity
        self.idle: bool = True  # Whether the axis is idle
        self.enabled: bool = False  # Whether the axis is enabled
        self.homed: bool = False  # Whether the axis is homed
        
    def __eq__(self, value):
        if isinstance(value, AxisStatus):
            return (self.dpos == value.dpos and
                    self.mpos == value.mpos and
                    self.idle == value.idle and
                    self.enabled == value.enabled and
                    self.homed == value.homed)
        return False
    
    def from_dict(self, data: dict):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def to_dict(self) -> dict:
        return self.__dict__

class MotionStatus:
    def __init__(self):
        self.in_table:dict[str, int] = {}
        self.out_table:dict[str, int] = {}
        self.in_state:dict[str, int] = {}
        self.out_state:dict[str, int] = {}
        self.axis_table:dict[str, int] = {}
        self.axis_state:dict[str, AxisStatus] = {}
        
    def get_input_info(self) -> tuple[list[str], list[int]]:
        names = list(self.in_table.keys())
        ios = list(self.in_table.values())
        return names, ios
    
    def get_output_info(self) -> tuple[list[str], list[int]]:
        names = list(self.out_table.keys())
        ios = list(self.out_table.values())
        return names, ios
    
    def get_axis_info(self) -> tuple[list[str], list[int]]:
        names = list(self.axis_table.keys())
        axis_nums = list(self.axis_table.values())
        return names, axis_nums
        
    def load_input_config(self, file_path):
        try:
            # 读取Excel文件并提取'Name'和'IO'列
            df = pd.read_excel(file_path)
            
            names = df['Name']
            ios = df['IO']

            self.in_table = {name: io for name, io in zip(names, ios)}
            self.in_state = {name: 0 for name in names}  # 初始化输入状态为0
        except Exception as e:
            print(f"Error loading input configuration: {e}")
        
    def load_output_config(self, file_path):
        try:
            # 读取Excel文件并提取'Name'和'IO'列
            df = pd.read_excel(file_path)
            
            names = df['Name']
            ios = df['IO']

            self.out_table = {name: io for name, io in zip(names, ios)}
            self.out_state = {name: 0 for name in names}  # 初始化输出状态为0  
        except Exception as e:
            print(f"Error loading output configuration: {e}")
       
    def from_dict(self, data: dict):
        for key, value in data.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                # 如果是 axis_state，需要递归处理
                if key == "axis_state" and isinstance(attr, dict):
                    for axis_key, axis_value in value.items():
                        if axis_key not in attr:
                            attr[axis_key] = AxisStatus()  # 创建 AxisStatus 实例
                        attr[axis_key].from_dict(axis_value)
                else:
                    setattr(self, key, value) 
                    
    def to_dict(self) -> dict:
        data = {}
        for key in self.__dict__:
            value = getattr(self, key)
            if isinstance(value, dict):
                sub_dict = {}
                for sub_key, sub_value in value.items():
                    if getattr(sub_value, 'to_dict', None) is not None:
                        # 如果 sub_value 有 to_dict 方法，则调用它
                        sub_dict[sub_key] = sub_value.to_dict()
                    else:
                        sub_dict[sub_key] = sub_value
                data[key] = sub_dict
            else:
                data[key] = value
        return data

class AxisBase(ABC):
    def __init__(self, axis_id):
        self.axis_id = axis_id
        self.name = f"Axis_{axis_id}"

    @abstractmethod
    def init(self, **kwargs):
        """
        初始化轴
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def is_enabled(self, **kwargs) -> bool:
        """
        检查轴是否已启用
        :return: True 如果轴已启用，否则 False
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def enable(self, **kwargs):
        """
        启用轴
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def disable(self, **kwargs):
        """
        禁用轴
        :return: None
        """
        print(f"Axis {self.axis_id} disabled.")
    
    @abstractmethod
    def setvalue(self, **kwargs):
        """
        设置轴的参数
        :param kwargs: 参数字典
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def getvalue(self, key, **kwargs):
        """
        获取轴的参数值
        :param key: 参数键
        :param kwargs: 其他参数
        :return: 参数值
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
        
    @abstractmethod
    def idle(self) -> bool:
        """
        检查轴是否处于空闲状态
        :return: True 如果轴处于空闲状态，否则 False
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_idle(self) -> int:
        """
        获取轴的IDLE状态值
        :return: IDLE状态值(-1 表示空闲)
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_axis_status(self) -> int:
        """
        获取轴的运行状态值
        :return: 运行状态值(0 表示就绪)
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def home(self):
        """
        回零操作
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def is_homed(self) -> bool:
        """
        检查轴是否已回零
        :return: True 如果轴已回零，否则 False
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def move_absolute(self, position: float, velocity: float = None):
        """
        移动到绝对位置
        :param position: 绝对位置
        :param velocity: 移动速度
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def move_relative(self, distance: float, velocity: float = None):
        """
        相对移动
        :param distance: 相对距离
        :param velocity: 移动速度
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def continuous_move(self, direction: int, velocity: float = None):
        """
        开始连续移动
        :param direction: 移动方向，1 为正方向，-1 为负方向
        :param velocity: 移动速度
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def stop(self):
        """
        停止轴运动
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_dpos(self) -> float:
        """
        获取当前轴的目标位置
        :return: 当前轴的目标位置
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def get_mpos(self) -> float:
        """
        获取当前轴的实际位置
        :return: 当前轴的实际位置
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_dpos(self) -> float:
        """
        获取当前轴的目标位置
        :return: 当前轴的目标位置
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def set_mpos(self, position: float):
        """
        设置当前轴的位置（通常用于初始化或校准）
        :param position: 位置值
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_velocity(self) -> float:
        """
        获取当前轴的速度
        :return: 当前轴的速度
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def set_velocity(self, velocity: float):
        """
        设置当前轴的速度
        :param velocity: 速度值
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def set_soft_limit(self, min_position: float = None, max_position: float = None):
        """
        设置轴的软极限
        :param min_position: 最小位置限制
        :param max_position: 最大位置限制
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_soft_limit(self) -> tuple:
        """
        获取轴的软极限
        :return: (min_position, max_position) 元组
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_alarm(self) -> int:
        """
        获取轴的报警信号状态
        :return: 报警信号状态值(0 表示无报警)
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_stop_reason(self) -> int:
        """
        获取轴的停止原因(位掩码,不同位表示不同状态)
        :return: 停止原因值
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_hard_limit(self) -> tuple:
        """
        获取正/反向硬限位的输入口编号及当前电平
        :return: ((正向输入口编号, 正向电平), (反向输入口编号, 反向电平)),未配置的输入口编号为 None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def pause(self):
        """
        暂停轴运动
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def resume(self):
        """
        继续轴运动
        :return: None
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    def clear_alarms(self, **kwargs):
        """
        清除轴的报警状态
        :return: None
        """
        pass

class MotionBase(ABC):
    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查是否已连接到运动控制器
        :return: True 如果已连接，否则 False
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    # IO 操作接口
    @abstractmethod
    def get_input(self, name) -> int:
        """
        读取输入信号
        :param name: 输入信号名称
        :return: 输入信号值
        """
        pass
    
    @abstractmethod
    def get_output(self, name) -> int:
        """
        读取输出信号
        :param name: 输出信号名称
        :return: 输出信号值
        """
        pass
    
    @abstractmethod
    def set_output(self, name, value):
        """
        设置输出信号
        :param name: 输出信号名称
        :param value: 输出信号值
        """
        pass
    
    @abstractmethod
    def get_all_axis(self) -> dict[object, AxisBase]:
        """
        获取所有轴的编号
        :return: 轴编号列表
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    # 获取轴控制接口
    @abstractmethod
    def get_axis(self, axis: int) -> AxisBase:
        """
        获取指定轴的控制接口
        :param axis: 轴编号
        :return: 轴控制接口
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    def execute(self, command: str, *args, **kwargs):
        """
        执行运动控制命令
        :param command: 命令名称
        :param args: 命令参数
        :param kwargs: 命令关键字参数
        :return: None
        """
        pass
    
    def reset(self):
        """
        重置运动控制器
        :return: None
        """
        pass
    
class VirtualAxis(AxisBase):
    def __init__(self, axis_id, **kwargs):
        super().__init__(axis_id)
        self.pulse_equivalent = 1.0
        self.mpos = 0.0 # Measured position
        self.dpos = 0.0  # Desired position
        self.min_position = None  # 软极限:最小位置限制
        self.max_position = None  # 软极限:最大位置限制
        self.velocity = 10.0
        self.acceleration = 0.0
        self.deceleration = 0.0
        self.max_velocity = 100.0
        self.target_position = 0.0
        self.homed = False
        self._is_moving = False
        self._is_paused = False
        self._move_thread = None
        self.dt = kwargs.get('dt', 0.05)  # Default time step for simulation
        self._enable = False  # Axis enable state

    def init(self, pulse_equivalent: float = 1.0, max_velocity: float = 100.0,
             acceleration: float = 10.0, deceleration: float = 10.0, velocity: float = 10.0):
        self.pulse_equivalent = pulse_equivalent
        self.max_velocity = max_velocity
        self.acceleration = acceleration
        self.deceleration = deceleration
        self.velocity = velocity

    def setvalue(self, **kwargs):
        """
        设置轴的参数
        :param kwargs: 参数字典
        :return: None
        """
        if 'pulse_equivalent' in kwargs:
            self.pulse_equivalent = kwargs['pulse_equivalent']
        if 'max_velocity' in kwargs:
            self.max_velocity = kwargs['max_velocity']
        if 'acceleration' in kwargs:
            self.acceleration = kwargs['acceleration']
        if 'deceleration' in kwargs:
            self.deceleration = kwargs['deceleration']
        if 'position' in kwargs:
            self.mpos = kwargs['position']
        if 'dt' in kwargs:
            self.dt = kwargs['dt']
            
    def getvalue(self, key, **kwargs):
        """
        获取轴的参数值
        :param key: 参数键
        :param kwargs: 其他参数
        :return: 参数值
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            raise KeyError(f"Axis {self.axis_id} does not have attribute '{key}'.")

    def is_enabled(self) -> bool:
        return self._enable
    
    def enable(self):
        """
        启用轴
        :return: None
        """
        self._enable = True
        
    def disable(self):
        """
        禁用轴
        :return: None
        """
        self._enable = False
        self.stop()
    
    def home(self):
        print(f"Axis {self.axis_id}: Homing...")
        self.mpos = 0.0
        self.dpos = 0.0
        self.homed = True
        print(f"Axis {self.axis_id}: Homed to position {self.mpos}.")

    def is_homed(self) -> bool:
        return self.homed

    def idle(self) -> bool:
        return not self._is_moving

    def get_idle(self) -> int:
        return -1 if not self._is_moving else 0

    def get_axis_status(self) -> int:
        return 0 if not self._is_moving else 1

    def _simulate_motion(self, distance):
        direction = 1 if distance >= 0 else -1
        total_distance = abs(distance)
        pos_start = self.mpos
        pos_end = pos_start + distance

        self._is_moving = True
        current_velocity = 0.0
        dt = self.dt
        moved_distance = 0.0
        self.dpos = pos_end
        while moved_distance < total_distance and self._is_moving:
            while self._is_paused and self._is_moving:
                time.sleep(dt)
            # Acceleration phase
            if current_velocity < self.velocity:
                current_velocity += self.acceleration * dt
                current_velocity = min(current_velocity, self.velocity)

            # Deceleration planning
            remaining_distance = total_distance - moved_distance
            decel_distance = (current_velocity ** 2) / (2 * self.deceleration)
            if decel_distance >= remaining_distance:
                current_velocity -= self.deceleration * dt
                current_velocity = max(current_velocity, 0)

            delta = current_velocity * dt
            if moved_distance + delta > total_distance:
                delta = total_distance - moved_distance

            self.mpos += delta * direction
            moved_distance += delta
            # record_velocity = current_velocity * direction

            time.sleep(dt)
            
        if self._is_moving:
            self.mpos = pos_end
            
        # self.velocity = 0.0
        self._is_moving = False
        print(f"Axis {self.axis_id}: Reached position {self.mpos}.")

    def __move(self, position: float, velocity: float):
        distance = position - self.mpos
        if self._is_moving:
            print(f"Axis {self.axis_id}: Already moving. Command ignored.")
            return
        self.velocity = min(velocity, self.max_velocity)
        self.target_position = position
        self._move_thread = threading.Thread(target=self._simulate_motion,
                                             args=(distance,))
        self._move_thread.start()
        
    def move_absolute(self, position: float, velocity: float = None):
        if not self._enable:
            raise RuntimeError(f"Axis {self.axis_id} is not enabled. Cannot move.")

        if not self.homed:
            raise RuntimeError(f"Axis {self.axis_id} is not homed. Cannot move to absolute position.")
        if self.min_position is not None and position < self.min_position:
            raise ValueError(f"Position {position} is below the minimum allowed position {self.min_position} for axis {self.axis_id}.")
        if self.max_position is not None and position > self.max_position:
            raise ValueError(f"Position {position} is above the maximum allowed position {self.max_position} for axis {self.axis_id}.")
        if not velocity:
            velocity = self.velocity
        self.__move(position, velocity)

    def move_relative(self, distance: float, velocity: float = None):
        if not self._enable:
            raise RuntimeError(f"Axis {self.axis_id} is not enabled. Cannot move.")
        target = self.mpos + distance
        if self.min_position is not None and target < self.min_position:
            raise ValueError(f"Relative move {distance} from current position {self.mpos} exceeds minimum allowed position {self.min_position} for axis {self.axis_id}.")
        if self.max_position is not None and target > self.max_position:
            raise ValueError(f"Relative move {distance} from current position {self.mpos} exceeds maximum allowed position {self.max_position} for axis {self.axis_id}.")
        if not velocity:
            velocity = self.velocity
        self.__move(target, velocity)

    def continuous_move(self, direction: int, velocity: float = None):
        if not self._enable:
            raise RuntimeError(f"Axis {self.axis_id} is not enabled. Cannot move.")
        if direction not in [-1, 1]:
            raise ValueError("Direction must be -1 (negative) or 1 (positive).")
        if self._is_moving:
            print(f"Axis {self.axis_id}: Already moving. Command ignored.")
        if not velocity:
            velocity = self.velocity
        velocity = direction * min(velocity, self.max_velocity)
        self.__move(direction * (2**31 - 1), velocity)

    def stop(self):
        print(f"Axis {self.axis_id}: Stopping...")
        self._is_moving = False
        self._is_paused = False
        if self._move_thread and self._move_thread.is_alive():
            self._move_thread.join()
        print(f"Axis {self.axis_id}: Stopped.")

    def get_alarm(self) -> int:
        return 0

    def get_stop_reason(self) -> int:
        return 0

    def get_hard_limit(self) -> tuple:
        return (None, None), (None, None)

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def get_dpos(self) -> float:
        # print(f"Axis {self.axis_id}: Current position is {self.position}.")
        return self.dpos

    def get_mpos(self) -> float:
        # print(f"Axis {self.axis_id}: Current position is {self.position}.")
        return self.mpos
    
    def set_dpos(self, position: float):
        # print(f"Axis {self.axis_id}: Setting desired position to {position}.")
        self.dpos = position
        if not self._is_moving:
            self.mpos = position

    def set_mpos(self, position: float):
        # print(f"Axis {self.axis_id}: Setting position to {position}.")
        self.mpos = position

    def set_soft_limit(self, min_position: float = None, max_position: float = None):
        if min_position is not None:
            self.min_position = min_position
        if max_position is not None:
            self.max_position = max_position

    def get_soft_limit(self) -> tuple:
        return self.min_position, self.max_position

    def get_velocity(self) -> float:
        # print(f"Axis {self.axis_id}: Current velocity is {self.velocity}.")
        return self.velocity
    
    def set_velocity(self, velocity: float):
        # print(f"Axis {self.axis_id}: Setting velocity to {velocity}.")
        if velocity < 0:
            raise ValueError("Velocity cannot be negative.")
        self.velocity = min(velocity, self.max_velocity)
        if self._is_moving:
            print(f"Axis {self.axis_id}: Velocity changed while moving. Current move will continue with new velocity.")

class VirtualMotion(MotionBase):
    def __init__(self, status:MotionStatus=MotionStatus(), axis_numbers=[], **kwargs):
        super().__init__()
        self.in_state = {}
        for name, io in status.in_table.items():
            self.in_state[io] = status.in_state.get(name, 0)
        self.out_state = {}
        for name, io in status.out_table.items():
            self.out_state[io] = status.out_state.get(name, 0)
        self.axis_numbers = axis_numbers
        self.axis = {i: VirtualAxis(i, **kwargs) for i in self.axis_numbers}

    def is_connected(self) -> bool:
        """
        检查是否已连接到运动控制器
        :return: True 如果已连接，否则 False
        """
        return True
        
    def get_input(self, name):
        """
        读取输入信号
        :param name: 输入信号名称
        :return: 输入信号值
        """
        return self.in_state.get(name, 0)
    
    def set_input(self, name, value):
        """
        设置输入信号
        :param name: 输入信号名称
        :param value: 输入信号值
        """
        self.in_state[name] = value
    
    def get_output(self, name):
        """
        读取输出信号
        :param name: 输出信号名称
        :return: 输出信号值
        """
        return self.out_state.get(name, 0)
    
    def set_output(self, name, value):
        """
        设置输出信号
        :param name: 输出信号名称
        :param value: 输出信号值
        """
        self.out_state[name] = value

    def get_all_axis(self):
        """
        获取所有轴的编号
        :return: 轴编号列表
        """
        return self.axis
        
    def get_axis(self, axis):
        if axis not in self.axis:
            raise ValueError(f"Axis {axis} does not exist.")
        return self.axis[axis]
    
if __name__ == "__main__":
    # Example usage
    motion = VirtualMotion(axis_number=2)
    axis0 = motion.get_axis(0)
    axis0.init(pulse_equivalent=1.0, max_velocity=300.0, acceleration=10.0, deceleration=10.0)
    
    axis0.home()
    axis0.move_absolute(100.0, velocity=300.0)
    
    for _ in range(10):
        print(f"Position: {axis0.get_dpos():.2f}")
        time.sleep(0.1)
    
    axis0.stop()
    # while not axis0.idle():
    #     print(f"Position: {axis0.get_position():.2f}")
    #     time.sleep(0.1)
    
    print(f"Axis 0 Position: {axis0.get_dpos()}")
    print(f"Axis 0 Velocity: {axis0.get_velocity()}")
    
    axis0.stop()