from pathlib import Path
from .zauxdllPython import ZAUXDLL
from ...common.Motion import MotionBase, AxisBase
import threading
from enum import Enum

# class HomeMode(Enum):
#     Z_POSITIVE_HOME = 1                 # Z相正向回零
#     Z_NEGATIVE_HOME = 2                 # Z相负向回零
#     ORIGIN_POSITIVE_HOME_REVERSE = 3    # 原点正向回零+反找
#     ORIGIN_NEGATIVE_HOME_REVERSE = 4    # 原点负向回零+反找
#     ORIGIN_POSITIVE_HOME = 13           # 原点正向回零
#     ORIGIN_NEGATIVE_HOME = 14           # 原点负向回零
    
class ZauxAxis(AxisBase):
    def __init__(self, axis_id, zaux_dll: ZAUXDLL):
        super().__init__(axis_id)
        self._zaux = zaux_dll
        self.home_mode = 4
        self.home_speed = 20.0  # 默认回零速度
        self.home_creep = 5.0  # 默认回零爬行速度
        self.stop_mode = 0
        self.run_mode = 8  # 运行模式，默认位置模式

    def init(self, 
             home_mode: int = 4, 
             pulse_equivalent: float = 1000.0, 
             acceleration: float = 100.0, 
             deceleration: float = 100.0, 
             sramp: float = 20.0,
             run_mode: int = 8,
             **kwargs) -> None:
        """
        初始化轴参数
        :param home_mode: 回零模式
        :param pulse_equivalent: 脉冲当量
        :param acceleration: 加速度
        :param deceleration: 减速度
        :param sramp: S型加减速时间
        """
        self.setvalue(
            home_mode=home_mode,
            pulse_equivalent=pulse_equivalent,
            acceleration=acceleration,
            deceleration=deceleration,
            sramp=sramp,
            run_mode=run_mode,
            **kwargs
        )

    def is_enabled(self, **kwargs) -> bool:
        """
        检查轴是否已启用
        :return: True 如果轴已启用，否则 False
        """
        ret, enabled = self._zaux.ZAux_Direct_GetAxisEnable(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is enabled: {ret}")
        return enabled.value == 1

    def enable(self, **kwargs):
        """
        启用轴
        :return: True 如果启用成功，否则 False
        """
        ionum = kwargs.get('ionum', 0)  # 默认使用第一个IO端口
        ret = self._zaux.ZAux_Direct_SetOp(ionum, 1)  # 设置IO端口为高电平以启用轴
        if ret != 0:
            raise RuntimeError(f"Failed to enable axis {self.axis_id}: {ret}")
        
    def disable(self, **kwargs):
        """
        禁用轴
        :return: True 如果禁用成功，否则 False
        """
        ionum = kwargs.get('ionum', 0)
        ret = self._zaux.ZAux_Direct_SetOp(ionum, 0)  # 设置IO端口为低电平以禁用轴
        if ret != 0:
            raise RuntimeError(f"Failed to disable axis {self.axis_id}: {ret}")

    def setvalue(self, **kwargs):
        if 'home_mode' in kwargs:
            self.home_mode = kwargs['home_mode']
        if 'home_speed' in kwargs:
            self.home_speed = kwargs['home_speed']
        if 'home_creep' in kwargs:
            self.home_creep = kwargs['home_creep']
        if 'stop_mode' in kwargs:
            self.stop_mode = kwargs['stop_mode']
        if 'pulse_equivalent' in kwargs:
            pulse_equivalent = kwargs['pulse_equivalent']
            ret = self._zaux.ZAux_Direct_SetUnits(self.axis_id, pulse_equivalent)
            if ret != 0:
                raise RuntimeError(f"Failed to set pulse equivalent for axis {self.axis_id}: {ret}")
        if 'acceleration' in kwargs:
            acceleration = kwargs['acceleration']
            ret = self._zaux.ZAux_Direct_SetAccel(self.axis_id, acceleration)
            if ret != 0:
                raise RuntimeError(f"Failed to set acceleration for axis {self.axis_id}: {ret}")
        if 'deceleration' in kwargs:
            deceleration = kwargs['deceleration']
            ret = self._zaux.ZAux_Direct_SetDecel(self.axis_id, deceleration)
            if ret != 0:
                raise RuntimeError(f"Failed to set deceleration for axis {self.axis_id}: {ret}")
        if 'sramp' in kwargs:
            sramp = kwargs['sramp']
            ret = self._zaux.ZAux_Direct_SetSramp(self.axis_id, sramp)
            if ret != 0:
                raise RuntimeError(f"Failed to set S-ramp for axis {self.axis_id}: {ret}")
        if 'min_position' in kwargs or 'max_position' in kwargs:
            self.set_soft_limit(
                min_position=kwargs.get('min_position'),
                max_position=kwargs.get('max_position')
            )
        if 'run_mode' in kwargs:
            self._write_run_mode(kwargs['run_mode'])
            self.run_mode = kwargs['run_mode']  # 缓存,供 EtherCat 停止/回零后恢复模式

    def getvalue(self, key, **kwargs):
        if key == 'home_mode':
            return self.home_mode
        elif key == 'home_speed':
            return self.home_speed
        elif key == 'home_creep':
            return self.home_creep
        elif key == 'stop_mode':
            return self.stop_mode
        elif key == 'run_mode':
            return self._read_run_mode()
        elif key == 'pulse_equivalent':
            ret, pulse_equivalent = self._zaux.ZAux_Direct_GetUnits(self.axis_id)
            if ret != 0:
                raise RuntimeError(f"Failed to get pulse equivalent for axis {self.axis_id}: {ret}")
            return pulse_equivalent.value
        elif key == 'acceleration':
            ret, acceleration = self._zaux.ZAux_Direct_GetAccel(self.axis_id)
            if ret != 0:
                raise RuntimeError(f"Failed to get acceleration for axis {self.axis_id}: {ret}")
            return acceleration.value
        elif key == 'deceleration':
            ret, deceleration = self._zaux.ZAux_Direct_GetDecel(self.axis_id)
            if ret != 0:
                raise RuntimeError(f"Failed to get deceleration for axis {self.axis_id}: {ret}")
            return deceleration.value
        elif key == 'sramp':
            ret, sramp = self._zaux.ZAux_Direct_GetSramp(self.axis_id)
            if ret != 0:
                raise RuntimeError(f"Failed to get S-ramp for axis {self.axis_id}: {ret}")
            return sramp.value
        else:
            raise KeyError(f"Unknown key: {key}")

    def _write_run_mode(self, run_mode: int):
        """
        写入轴运行模式(标准轴:轴类型AType)
        :param run_mode: 运行模式
        :return: None
        """
        ret = self._zaux.ZAux_Direct_SetAtype(self.axis_id, run_mode)
        if ret != 0:
            raise RuntimeError(f"Failed to set run mode for axis {self.axis_id}: {ret}")

    def _read_run_mode(self) -> int:
        """
        读取轴运行模式(标准轴:轴类型AType)
        :return: 运行模式
        """
        ret, run_mode = self._zaux.ZAux_Direct_GetAtype(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get run mode for axis {self.axis_id}: {ret}")
        return run_mode.value

    def set_soft_limit(self, min_position: float = None, max_position: float = None):
        """
        设置轴的软极限(同步到运动控制卡SDK)
        :param min_position: 最小位置限制(负向软限位),None 表示不修改
        :param max_position: 最大位置限制(正向软限位),None 表示不修改
        :return: None
        """
        if min_position is not None:
            ret = self._zaux.ZAux_Direct_SetRsLimit(self.axis_id, min_position)
            if ret != 0:
                raise RuntimeError(f"Failed to set minimum soft limit for axis {self.axis_id}: {ret}")
        if max_position is not None:
            ret = self._zaux.ZAux_Direct_SetFsLimit(self.axis_id, max_position)
            if ret != 0:
                raise RuntimeError(f"Failed to set maximum soft limit for axis {self.axis_id}: {ret}")

    def get_soft_limit(self) -> tuple:
        """
        获取轴的软极限(从运动控制卡SDK读取)
        :return: (min_position, max_position) 元组
        """
        ret, min_position = self._zaux.ZAux_Direct_GetRsLimit(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get minimum soft limit for axis {self.axis_id}: {ret}")
        ret, max_position = self._zaux.ZAux_Direct_GetFsLimit(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get maximum soft limit for axis {self.axis_id}: {ret}")
        return min_position.value, max_position.value

    def get_alarm(self) -> int:
        """
        获取轴的报警信号状态
        :return: 报警信号状态值(0 表示无报警)
        """
        ret, alarm = self._zaux.ZAux_Direct_GetAlmIn(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get alarm for axis {self.axis_id}: {ret}")
        return alarm.value

    def get_stop_reason(self) -> int:
        """
        获取轴的停止原因(位掩码,不同位表示不同状态)
        :return: 停止原因值
        """
        ret, reason = self._zaux.ZAux_Direct_GetAxisStopReason(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get stop reason for axis {self.axis_id}: {ret}")
        return reason.value

    def get_hard_limit(self) -> tuple:
        """
        获取正/反向硬限位的输入口编号及当前电平
        :return: ((正向输入口编号, 正向电平), (反向输入口编号, 反向电平)),未配置的输入口编号为 None
        """
        ret, fwd_port = self._zaux.ZAux_Direct_GetFwdIn(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get forward hard limit for axis {self.axis_id}: {ret}")
        ret, rev_port = self._zaux.ZAux_Direct_GetRevIn(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get reverse hard limit for axis {self.axis_id}: {ret}")
        fwd_port = fwd_port.value if fwd_port.value != -1 else None
        rev_port = rev_port.value if rev_port.value != -1 else None
        fwd_level = None
        rev_level = None
        if fwd_port is not None:
            ret, level = self._zaux.ZAux_Direct_GetIn(fwd_port)
            if ret != 0:
                raise RuntimeError(f"Failed to get forward hard limit level for axis {self.axis_id}: {ret}")
            fwd_level = level.value
        if rev_port is not None:
            ret, level = self._zaux.ZAux_Direct_GetIn(rev_port)
            if ret != 0:
                raise RuntimeError(f"Failed to get reverse hard limit level for axis {self.axis_id}: {ret}")
            rev_level = level.value
        return (fwd_port, fwd_level), (rev_port, rev_level)

    def pause(self):
        """
        暂停轴运动
        :return: None
        """
        ret = self._zaux.ZAux_Direct_MovePause(self.axis_id, 0)
        if ret != 0:
            raise RuntimeError(f"Failed to pause axis {self.axis_id}: {ret}")

    def resume(self):
        """
        继续轴运动
        :return: None
        """
        ret = self._zaux.ZAux_Direct_MoveResume(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to resume axis {self.axis_id}: {ret}")

    def get_idle(self) -> int:
        """
        查询轴的IDLE状态
        :return: 轴的IDLE状态值(-1 表示空闲)
        """
        ret, isidle = self._zaux.ZAux_Direct_GetIfIdle(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is idle: {ret}")
        return isidle.value

    def get_axis_status(self) -> int:
        """
        查询轴的运行状态
        :return: 轴的运行状态值(0 表示就绪)
        """
        ret, state = self._zaux.ZAux_Direct_GetAxisStatus(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is status: {ret}")
        return state.value

    def idle(self) -> bool:
        """
        检查轴是否空闲(IDLE状态与运行状态合并判断)
        :return: True 如果轴空闲，否则 False
        """
        return self.get_idle() == -1 and self.get_axis_status() == 0

    def home(self):
        """
        回零操作
        :return: None
        """
        if self.get_idle() == -1:
            # print(f"Axis {self.axis_id} is idle, proceeding with homing.")
            # 设置回零速度
            ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, self.home_speed)
            if ret != 0:
                raise RuntimeError(f"Failed to set home speed for axis {self.axis_id} to {self.home_speed}: {ret}")
            # 设置回零爬行速度
            ret = self._zaux.ZAux_Direct_SetCreep(self.axis_id, self.home_creep)
            if ret != 0:
                raise RuntimeError(f"Failed to set home creep speed for axis {self.axis_id} to {self.home_creep}: {ret}")
            # 执行回零操作
            ret = self._zaux.ZAux_Direct_Single_Datum(self.axis_id, self.home_mode)
            if ret != 0:
                raise RuntimeError(f"Failed to home axis {self.axis_id} with mode {self.home_mode}: {ret}")
        else:
            raise RuntimeError(f"Axis {self.axis_id} is not idle, cannot perform homing.")
    
    def is_homed(self) -> bool:
        """
        检查轴是否已回零
        :return: True 如果轴已回零，否则 False
        """
        ret, homed = self._zaux.ZAux_Direct_GetHomeStatus(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is homed: {ret}")
        return homed.value == 1
        
    def stop(self):
        """
        停止轴运动
        :return: None
        """
        if self.get_idle() != -1:
            # print(f"Axis {self.axis_id} is idle, stopping.")
            ret = self._zaux.ZAux_Direct_Single_Cancel(self.axis_id, self.stop_mode)
            if ret != 0:
                raise RuntimeError(f"Failed to stop axis {self.axis_id}: {ret}")
        else:
            raise RuntimeError(f"Axis {self.axis_id} is idle, cannot stop.")
        
    def move_absolute(self, position: float, velocity: float = None):
        """
        移动到目标位置
        :param position: 目标位置
        :param velocity: 移动速度
        :return: None
        """
        if self.get_idle() == -1:
            min_position, max_position = self.get_soft_limit()
            if min_position is not None and position < min_position:
                raise ValueError(f"Position {position} is below the minimum allowed position {min_position} for axis {self.axis_id}.")
            if max_position is not None and position > max_position:
                raise ValueError(f"Position {position} is above the maximum allowed position {max_position} for axis {self.axis_id}.")
            if velocity is not None:
                ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, velocity)
                if ret != 0:
                    raise RuntimeError(f"Failed to set speed for axis {self.axis_id} to {velocity}: {ret}")
            ret = self._zaux.ZAux_Direct_Single_MoveAbs(self.axis_id, position)
            if ret != 0:
                raise RuntimeError(f"Failed to move axis {self.axis_id} to position {position}: {ret}")
        else:
            raise RuntimeError(f"Axis {self.axis_id} is not idle, cannot perform move operation.")

    def move_relative(self, distance: float, velocity: float = None):
        """
        相对移动
        :param distance: 相对距离
        :param velocity: 移动速度
        :return: None
        """
        if self.get_idle() == -1:
            min_position, max_position = self.get_soft_limit()
            if min_position is not None and (self.get_dpos() + distance) < min_position:
                raise ValueError(f"Relative move {distance} from current position {self.get_dpos()} exceeds minimum allowed position {min_position} for axis {self.axis_id}.")
            if max_position is not None and (self.get_dpos() + distance) > max_position:
                raise ValueError(f"Relative move {distance} from current position {self.get_dpos()} exceeds maximum allowed position {max_position} for axis {self.axis_id}.")
            if velocity is not None:
                ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, velocity)
                if ret != 0:
                    raise RuntimeError(f"Failed to set speed for axis {self.axis_id} to {velocity}: {ret}")
            ret = self._zaux.ZAux_Direct_Single_Move(self.axis_id, distance)
            if ret != 0:
                raise RuntimeError(f"Failed to move axis {self.axis_id} by distance {distance}: {ret}")
        else:
            raise RuntimeError(f"Axis {self.axis_id} is not idle, cannot perform move operation.")

    def continuous_move(self, direction, velocity = None):
        """
        开始Jog运动
        :param direction: 运动方向，1为正向，-1为负向
        :param velocity: Jog速度
        :return: None
        """
        if self.get_idle() == -1:
            if velocity is not None:
                ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, velocity)
                if ret != 0:
                    raise RuntimeError(f"Failed to set jog speed for axis {self.axis_id} to {velocity}: {ret}")
            ret = self._zaux.ZAux_Direct_Single_Vmove(self.axis_id, direction)
            if ret != 0:
                raise RuntimeError(f"Failed to start jog for axis {self.axis_id} in direction {direction}: {ret}")
        else:
            raise RuntimeError(f"Axis {self.axis_id} is not idle, cannot perform jog operation.")

    def get_dpos(self):
        """
        获取当前轴的目标位置
        :return: 当前轴的目标位置
        """
        ret, position = self._zaux.ZAux_Direct_GetDpos(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get target position for axis {self.axis_id}: {ret}")
        return position.value
    
    def get_mpos(self):
        """
        获取当前轴的实际位置
        :return: 当前轴的实际位置
        """
        ret, position = self._zaux.ZAux_Direct_GetMpos(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get actual position for axis {self.axis_id}: {ret}")
        return position.value
    
    def set_dpos(self, position: float):
        """
        设置当前轴的位置（通常用于初始化或校准）
        :param position: 位置值
        :return: None
        """
        ret = self._zaux.ZAux_Direct_SetDpos(self.axis_id, position)
        if ret != 0:
            raise RuntimeError(f"Failed to set position for axis {self.axis_id} to {position}: {ret}")
        
    def set_mpos(self, position):
        """
        设置当前轴的实际位置（通常用于初始化或校准）
        :param position: 位置值
        :return: None
        """
        ret = self._zaux.ZAux_Direct_SetMpos(self.axis_id, position)
        if ret != 0:
            raise RuntimeError(f"Failed to set actual position for axis {self.axis_id} to {position}: {ret}")
        
    def get_velocity(self):
        """
        获取当前轴的速度
        :return: 当前轴的速度
        """
        ret, velocity = self._zaux.ZAux_Direct_GetSpeed(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to get velocity for axis {self.axis_id}: {ret}")
        return velocity.value
    
    def set_velocity(self, velocity: float):
        """
        设置当前轴的速度
        :param velocity: 速度值
        :return: None
        """
        ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, velocity)
        if ret != 0:
            raise RuntimeError(f"Failed to set velocity for axis {self.axis_id} to {velocity}: {ret}")

class ZauxMotion(MotionBase):
    def __init__(self, axis_numbers = [], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zaux = ZAUXDLL()
        self.axis_numbers = axis_numbers
        self._axis = {i:self.create_axis(i) for i in self.axis_numbers}
        self._reset_bas_path = None

    def create_axis(self, axis_id: int) -> ZauxAxis:
        """
        创建ZauxAxis实例
        :param axis_id: 轴编号
        :return: ZauxAxis实例
        """
        return ZauxAxis(axis_id, self._zaux)

    def download_bas(self, bas_filepath: str, run_mode: int = 0):
        """
        下载并运行基础程序文件
        :param bas_filepath: 基础程序文件路径
        :param run_mode: 运行模式
        :return: None
        """
        path = Path(bas_filepath)
        if not path.exists():
            raise FileNotFoundError(f"Base file {bas_filepath} does not exist.")
        if not path.is_file():
            raise ValueError(f"Base file {bas_filepath} is not a valid file.")
        if path.suffix.lower() != '.bas':
            raise ValueError(f"Base file {bas_filepath} must have a .bas extension.")
        ret = self._zaux.ZAux_BasDown(str(path), run_mode)
        if ret != 0:
            raise RuntimeError(f"Failed to download base file {bas_filepath}: {ret}")

    def reset(self):
        """
        重置ZAux运动控制器
        :return: None
        """
        if self._reset_bas_path is not None:
            self.download_bas(self._reset_bas_path, run_mode=0)
        else:
            raise RuntimeError("Reset base file path is not set.")
        
    @property
    def zaux(self):
        """
        获取ZAUXDLL实例
        :return: ZAUXDLL实例
        """
        return self._zaux
    
    @property
    def axis_nums(self):
        """
        获取轴编号列表
        :return: 轴编号列表
        """
        return self.axis_numbers
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到ZAux运动控制器
        :return: True 如果已连接，否则 False
        """
        return self._zaux.handle.value is not None

    def get_input(self, ionum: int):
        """
        读取输入信号
        :param ionum: 输入信号编号
        :return: 输入信号值
        """
        ret, value = self.zaux.ZAux_Direct_GetIn(ionum)
        if ret != 0:
            raise RuntimeError(f"Failed to get input {ionum}: {ret}")
        return value.value
    
    def get_output(self, ionum: int):
        """
        读取输出信号
        :param ionum: 输出信号编号
        :return: 输出信号值
        """
        ret, value = self.zaux.ZAux_Direct_GetOp(ionum)
        if ret != 0:
            raise RuntimeError(f"Failed to get output {ionum}: {ret}")
        return value.value
    
    def set_output(self, name, value:int):
        """
        设置输出信号
        :param name: 输出信号名称
        :param value: 输出信号值
        """
        ret = self.zaux.ZAux_Direct_SetOp(name, value)
        if ret != 0:
            raise RuntimeError(f"Failed to set output {name} to {value}: {ret}")

    def get_all_axis(self) -> dict[object, ZauxAxis]:
        """
        获取所有轴的控制接口
        :return: 包含所有轴的ZauxAxis实例的字典
        """
        return self._axis
        
    def get_axis(self, axis: int) -> ZauxAxis:
        """
        获取指定轴的控制接口
        :param axis: 轴编号
        :return: ZauxAxis实例
        """
        if axis not in self.axis_numbers:
            raise ValueError(f"Invalid axis number: {axis}")
        return self._axis[axis]
    
class ZauxEtherCatAxis(ZauxAxis):
    def __init__(self, axis_id, zaux_dll: ZAUXDLL):
        super().__init__(axis_id, zaux_dll)
        self.homing = False

    def __del__(self):
        self.homing = False

    def _write_run_mode(self, run_mode: int):
        """
        写入轴运行模式(EtherCat:通过SDO写0x6060)
        :param run_mode: 运行模式
        :return: None
        """
        ret = self._zaux.ZAux_BusCmd_SDOWriteAxis(self.axis_id, 0x6060, 0, 2, run_mode)
        if ret != 0:
            raise RuntimeError(f"Failed to set run mode for axis {self.axis_id}: {ret}")

    def _read_run_mode(self) -> int:
        """
        读取轴运行模式(EtherCat:通过SDO读0x6061)
        :return: 运行模式
        """
        ret, run_mode = self._zaux.ZAux_BusCmd_SDOReadAxis(self.axis_id, 0x6061, 0, 2)
        if ret != 0:
            raise RuntimeError(f"Failed to get run mode for axis {self.axis_id}: {ret}")
        return run_mode.value

    def init(self, run_mode: int = 0, **kwargs):
        self._write_run_mode(run_mode)
        self.run_mode = run_mode
        # path = Path(bas_filepath)
        # if not path.exists():
        #     raise FileNotFoundError(f"Base file {bas_filepath} does not exist.")
        # if not path.is_file():
        #     raise ValueError(f"Base file {bas_filepath} is not a valid file.")
        # if path.suffix.lower() != '.bas':
        #     raise ValueError(f"Base file {bas_filepath} must have a .bas extension.")
        # ret = self._zaux.ZAux_BasDown(str(path), run_mode)
        # if ret != 0:
        #     raise RuntimeError(f"Failed to download base file {bas_filepath} for axis {self.axis_id}: {ret}")
            
    def is_enabled(self) -> bool:
        """
        检查轴是否已启用
        :return: True 如果轴已启用，否则 False
        """
        ret, enabled = self._zaux.ZAux_Direct_GetAxisEnable(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is enabled: {ret}")
        return enabled.value == 1
            
    def enable(self):
        self._zaux.ZAux_BusCmd_DriveClear(self.axis_id, 0)
        self._zaux.ZAux_Direct_SetAxisEnable(self.axis_id, 1)
        
    def disable(self):
        self._zaux.ZAux_Direct_SetAxisEnable(self.axis_id, 0)
        self._zaux.ZAux_BusCmd_DriveClear(self.axis_id, 0)

    def stop(self):
        """
        停止轴运动
        :return: None
        """
        super().stop()
        self._zaux.ZAux_BusCmd_SDOWriteAxis(self.axis_id, 0x6060, 0, 2, self.run_mode)
        self.homing = False
        
    def home(self):
        """
        回零操作
        :return: None
        """
        if self.get_idle() == -1:
            # 设置回零速度
            ret = self._zaux.ZAux_Direct_SetSpeed(self.axis_id, self.home_speed)
            if ret != 0:
                raise RuntimeError(f"Failed to set home speed for axis {self.axis_id} to {self.home_speed}: {ret}")
            # 设置回零爬行速度
            ret = self._zaux.ZAux_Direct_SetCreep(self.axis_id, self.home_creep)
            if ret != 0:
                raise RuntimeError(f"Failed to set home creep speed for axis {self.axis_id} to {self.home_creep}: {ret}")
            ret = self._zaux.ZAux_BusCmd_SDOWriteAxis(self.axis_id, 0x6060, 0, 2, 6)
            if ret != 0:
                raise RuntimeError(f"Failed to write SDO for axis {self.axis_id}: {ret}")
            threading.Event().wait(0.1)
            # 执行回零操作
            ret = self._zaux.ZAux_BusCmd_Datum(self.axis_id, self.home_mode)
            if ret != 0:
                raise RuntimeError(f"Failed to home axis {self.axis_id} with mode {self.home_mode}: {ret}")
            def wait_for_homing():
                self.homing = True
                while not self.__is_homed():
                    if not self.homing:
                        break
                    threading.Event().wait(0.1)
                self.homing = False
                self._zaux.ZAux_BusCmd_SDOWriteAxis(self.axis_id, 0x6060, 0, 2, self.run_mode)
            threading.Thread(target=wait_for_homing, daemon=True).start()
        else:
            raise RuntimeError(f"Axis {self.axis_id} is not idle, cannot perform homing.")

    def __is_homed(self) -> bool:
        """
        检查轴是否已回零
        :return: True 如果轴已回零，否则 False
        """
        ret, homed = self._zaux.ZAux_BusCmd_GetHomeStatus(self.axis_id)
        if ret != 0:
            raise RuntimeError(f"Failed to check if axis {self.axis_id} is homed: {ret}")
        return homed.value == 1
    
    def is_homed(self) -> bool:
        return self.__is_homed() and not self.homing

    def clear_alarms(self):
        self._zaux.ZAux_BusCmd_DriveClear(self.axis_id, 0)    
    
class ZauxEtherCatMotion(ZauxMotion):
    def create_axis(self, axis_id: int) -> ZauxEtherCatAxis:
        """
        创建ZauxAxis实例
        :param axis_id: 轴编号
        :return: ZauxAxis实例
        """
        return ZauxEtherCatAxis(axis_id, self._zaux)
        
    def get_axis(self, axis: int) -> ZauxEtherCatAxis:
        return super().get_axis(axis)
        
class ZauxMotionV2(ZauxMotion):
    class AxisType(Enum):
        STANDARD = 0
        ETHERCAT = 1

    def __init__(self, axis_numbers = [], axis_type:list[AxisType] = None, *args, **kwargs):
        super().__init__(axis_numbers, *args, **kwargs)
        # V2特有的初始化代码可以放在这里
        self.axis_type = axis_type if axis_type is not None else [self.AxisType.STANDARD]*len(axis_numbers)
        
    def create_axis(self, axis_id: int) -> AxisBase:
        """
        创建轴实例
        :param axis_id: 轴编号
        :return: 轴实例
        """
        index = self.axis_numbers.index(axis_id)
        atype = self.axis_type[index]
        if atype == self.AxisType.STANDARD:
            return ZauxAxis(axis_id, self._zaux)
        elif atype == self.AxisType.ETHERCAT:
            return ZauxEtherCatAxis(axis_id, self._zaux)
        else:
            raise ValueError(f"Unknown axis type: {atype}")
    
if __name__ == "__main__":
    import time
    # Example usage
    zaux_motion = ZauxMotion([1])
    
    # ipaddr = '127.0.0.1'
    # zaux_motion.zaux.ZAux_OpenEth(ipaddr)
    
    # icomid = 0
    # zaux_motion.zaux.ZAux_OpenCom(icomid)
    
    # card_num = 0
    # zaux_motion.zaux.ZAux_OpenPci(card_num)
    
    # type = 5
    # pconnectstring = '5'
    # uims = 1000
    # zaux_motion.zaux.ZAux_FastOpen(type, pconnectstring, uims)
    
    # 轴初始化
    axis = zaux_motion.get_axis(1)
    
    axis.init(
        pulse_equivalent=1000.0,
        acceleration=100.0,
        deceleration=100.0,
        sramp=20.0)
    
    # 回零
    axis.home()
    
    while not axis.is_homed():
        print("Waiting for axes to home...")
        time.sleep(0.5)
    print("Axes are homed.")
    
    # 移动到绝对位置
    axis.move_absolute(1000.0, 100.0)
        