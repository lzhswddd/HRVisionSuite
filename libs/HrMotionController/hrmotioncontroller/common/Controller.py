from .Motion import MotionBase, VirtualMotion, MotionStatus, AxisStatus
from .Task import TaskerBase, TaskState, Action, TaskConditionItem
from typing import Callable
import threading
import time

class Controller:
    def __init__(self):
        self._status = MotionStatus()
        self.tasker_state:dict[str, int] = {}
        self.user_state:dict[str, int] = {}
        self.watch_state:dict[str, tuple[str, int]] = {}
        self.watch_enable:dict[str, bool] = {}
        self.watch_execute:dict[str, Callable[[Controller]]] = {}
        
        # IO消抖相关属性
        self.__debounce_time:dict[str, float] = {}  # 每个输入的消抖时间配置
        self.__debounce_state:dict[str, int] = {}   # 消抖过滤后的状态
        self.__debounce_raw_state:dict[str, int] = {}  # 原始状态
        self.__debounce_last_change:dict[str, float] = {}  # 最后状态变化时间
        self.__debounce_stable_time:dict[str, float] = {}  # 状态稳定时间
        
        self.__taskers:dict[str,TaskerBase] = {}
        self._motion:MotionBase = None
        
        self.__scan_interval = 0.03
        self.__run_thread = None
        self._stop_thread = False
        self._sleep_thread = threading.Event()
        
        self._tasker_event :dict[TaskState, Callable] = {}
        self._run_code = 0
        
    @property
    def status(self) -> MotionStatus:
        """ Returns the current motion status object. """
        return self._status
    
    @status.setter
    def status(self, value:MotionStatus):
        """ Sets the motion status object. """
        if not isinstance(value, MotionStatus):
            raise TypeError("Status must be an instance of MotionStatus.")
        self._status = value
        
    @property
    def motion(self) -> MotionBase:
        """ Returns the current motion object. """
        return self._motion
    
    @property
    def scan_interval(self) -> float:
        """ Returns the current scan interval. """
        return self.__scan_interval
    
    @scan_interval.setter
    def scan_interval(self, value:float):
        """ Sets the scan interval for the controller.
        :param value: The scan interval in seconds.
        """
        if value <= 0:
            raise ValueError("Scan interval must be greater than 0 seconds.")
        self.__scan_interval = value
        
    @property
    def run_code(self) -> int:
        """ Returns the current run code. """
        return self._run_code
    
    @run_code.setter
    def run_code(self, value:int):
        """ Sets the run code for the controller.
        :param value: The run code to set.
        """
        self._run_code = value
    
    def register_tasker_event(self, state:TaskState, event:Callable[[TaskerBase], None]):
        """ Registers an event handler for a specific tasker state.
        :param state: The TaskState to register the event for.
        :param event: The event handler to call when the state is triggered.
        """
        if not isinstance(event, Callable):
            print(f"Event {event} is not an instance of Callable.")
            return
        self._tasker_event[state] = event
        
    def unregister_tasker_event(self, state:TaskState):
        """ Unregisters the event handler for a specific tasker state.
        :param state: The TaskState to unregister the event for.
        """
        if state in self._tasker_event:
            del self._tasker_event[state]
        else:
            print(f"No event registered for state {state}.")
    
    def set_watch_state(self, name:str, ioname:str, value:int):
        """ Sets a watch state by input name and expected value.
        :param name: The name of the watch state.
        :param ioname: The name of the input to watch.
        :param value: The expected value of the input.
        """
        if ioname not in self._status.in_table:
            print(f"Input {name} does not exist.")
            return
        self.watch_state[name] = (ioname, value)
        self.watch_enable[name] = True
    
    def set_watch_state_by_ioname(self, ioname:str, value:int):
        """ Sets a watch state by input name and expected value.
        :param ioname: The name of the input to watch.
        :param value: The expected value of the input.
        """
        if ioname not in self._status.in_table:
            print(f"Input {ioname} does not exist.")
            return
        for name in self.watch_state.keys():
            if self.watch_state[name][0] == ioname:
                self.watch_state[name] = (ioname, value)
                self.watch_enable[name] = True
                return
        self.watch_state[ioname] = (ioname, value)
        self.watch_enable[ioname] = True
        
    def get_watch_state(self, name:str):
        if name not in self.watch_state:
            print(f"Watch state {name} does not exist.")
            return None
        return self.watch_state[name]
    
    def remove_watch_state(self, name:str):
        if name in self.watch_state:
            del self.watch_state[name]
            del self.watch_enable[name]
    
    def set_watch_execute(self, name:str, execute:Callable[['Controller'], None]):
        """ Sets an action to be executed when the watch state is triggered.
        :param name: The name of the input to watch.
        :param action: The action to execute when the watch state is triggered.
        """
        if name not in self.watch_state:
            print(f"Watch state {name} does not exist.")
            return
        if not isinstance(execute, Callable):
            print(f"Execute {execute} is not an instance of Callable.")
            return
        self.watch_execute[name] = execute
        
    def get_watch_execute(self, name:str) -> Callable:
        if name not in self.watch_execute:
            print(f"Watch execute {name} does not exist.")
            return None
        return self.watch_execute[name]
    
    def remove_watch_execute(self, name:str):
        if name in self.watch_execute:
            del self.watch_execute[name]
            
    def set_watch_enable(self, name:str, enable:bool):
        """ Enables or disables a watch state.
        :param
        name: The name of the watch state.
        :param enable: True to enable, False to disable.
        """
        if name not in self.watch_enable:
            print(f"Watch state {name} does not exist.")
            return
        self.watch_enable[name] = enable
        
    def is_watch_enabled(self, name:str) -> bool:
        """ Checks if a watch state is enabled.
        :param name: The name of the watch state.
        :return: True if enabled, False otherwise.
        """
        return self.watch_enable.get(name, False)
            
    def set_debounce_time(self, name:str, debounce_time:float):
        """ 设置指定输入的消抖时间
        :param name: 输入名称
        :param debounce_time: 消抖时间（秒），必须大于0
        """
        if name not in self._status.in_table:
            print(f"Input {name} does not exist.")
            return
        if debounce_time <= 0:
            print("Debounce time must be greater than 0 seconds.")
            return
        self.__debounce_time[name] = debounce_time
        # 初始化相关状态
        if name not in self.__debounce_state:
            self.__debounce_state[name] = 0
            self.__debounce_raw_state[name] = 0
            self.__debounce_last_change[name] = 0
            self.__debounce_stable_time[name] = 0
    
    def get_debounce_time(self, name:str) -> float:
        """ 获取指定输入的消抖时间
        :param name: 输入名称
        :return: 消抖时间，如果未设置则返回0
        """
        return self.__debounce_time.get(name, 0)
    
    def remove_debounce(self, name:str):
        """ 移除指定输入的消抖配置
        :param name: 输入名称
        """
        if name in self.__debounce_time:
            del self.__debounce_time[name]
        if name in self.__debounce_state:
            del self.__debounce_state[name]
        if name in self.__debounce_raw_state:
            del self.__debounce_raw_state[name]
        if name in self.__debounce_last_change:
            del self.__debounce_last_change[name]
        if name in self.__debounce_stable_time:
            del self.__debounce_stable_time[name]
    
    def get_debounce_state(self, name:str) -> int:
        """ 获取指定输入的消抖后状态
        :param name: 输入名称
        :return: 消抖后的状态值，如果不存在则返回-1
        """
        return self.__debounce_state.get(name, -1)
    
    def get_raw_state(self, name:str) -> int:
        """ 获取指定输入的原始状态（未消抖）
        :param name: 输入名称
        :return: 原始状态值，如果不存在则返回-1
        """
        return self.__debounce_raw_state.get(name, -1)
    
    def __update_debounce(self, name:str):
        """ 更新指定输入的消抖状态
        :param name: 输入名称
        """
        if name not in self.__debounce_time:
            return  # 没有配置消抖时间，不进行消抖处理
        
        current_time = time.time()
        raw_value = self._motion.get_input(self._status.in_table[name]) if self._motion else 0
        
        # 更新原始状态
        self.__debounce_raw_state[name] = raw_value
        
        # 检查状态是否发生变化
        if raw_value != self.__debounce_state[name]:
            # 状态变化了，更新最后变化时间
            self.__debounce_last_change[name] = current_time
            self.__debounce_stable_time[name] = 0
        else:
            # 状态没有变化，更新稳定时间
            self.__debounce_stable_time[name] = current_time - self.__debounce_last_change[name]
        
        # 检查是否达到消抖时间
        if self.__debounce_stable_time[name] >= self.__debounce_time[name]:
            # 状态已稳定足够时间，更新消抖后的状态
            self.__debounce_state[name] = raw_value
    
    def set_motion(self, motion:MotionBase):
        """ Sets the motion object for the controller.
        :param motion: The motion object to set.
        """
        if not isinstance(motion, MotionBase):
            print("Motion is not an instance of MotionBase.")
            return
        self._motion = motion
        
    def handle_tasker_event(self, tasker:TaskerBase, state:TaskState):
        if state in self._tasker_event:
            event = self._tasker_event[state]
            if callable(event):
                event(tasker)
            
    def add_tasker(self, name:str, tasker:TaskerBase, real_time:bool = False, register_event:bool = True):
        if name in self.__taskers:
            print("Task already exists.")
            return
        
        if real_time:
            tasker.condition_update = lambda x: TaskerBase.update_condition_realtime(x, self.__update_in, self.__update_out, self.__update_axis, self.__update_tasker, self.__update_user)
        else:
            tasker.condition_update = lambda x: TaskerBase.update_condition(x, self._status.in_state, self._status.out_state, self._status.axis_state, self.tasker_state, self.user_state)
        
        self.__taskers[name] = tasker
        self.tasker_state[name] = tasker.state
        
        if register_event:
            tasker.register_event(self.handle_tasker_event)
    
    def remove_tasker(self, name:str, wait:bool = False):
        if name not in self.__taskers:
            print("Task does not exist.")
            return
        if wait:
            self.__taskers[name].wait_complete()
        del self.__taskers[name]
        del self.tasker_state[name]
    
    def clear_taskers(self):
        self.__taskers.clear()
        
    def wait_taskers(self):
        for tasker in self.__taskers.values():
            tasker.wait_complete()
            
    def abort_taskers(self):
        for tasker in self.__taskers.values():
            tasker.abort()
            
    def get_tasker(self, name:str) -> TaskerBase:
        """ Returns the tasker with the given name.
        :param name: The name of the tasker to retrieve.
        :return: The TaskerBase object if found, None otherwise.
        """
        if name not in self.__taskers:
            print(f"TaskerBase {name} does not exist.")
            return None
        return self.__taskers[name]
    
    def get_all_taskers(self) -> dict[str, TaskerBase]:
        """ Returns a dictionary of all taskers.
        :return: A dictionary of TaskerBase objects.
        """
        return self.__taskers
            
    def reset_taskers(self):
        for tasker in self.__taskers.values():
            if tasker.state != TaskState.IDLE and tasker.state != TaskState.RUNNING:
                tasker.reset()
            
    def start(self):
        if self.__run_thread is not None and self.__run_thread.is_alive():
            # print("Thread is already running.")
            return
        self.__run_thread = threading.Thread(target=self.__watch_io)
        # self.__run_thread.daemon = True
        self.__run_thread.start()
        
    def stop(self):
        self.wait_taskers()
        if self.__run_thread is None:
            # print("Thread is not running.")
            return
        if self.__run_thread.is_alive():
            self._stop_thread = True
            self._sleep_thread.set()
            self.__run_thread.join()
        self.__run_thread = None
        
    def is_running(self) -> bool:
        """ Check if the controller is currently running. """
        return self.__run_thread is not None and self.__run_thread.is_alive()
    
    def update_state(self):
        try:
            # 首先更新所有消抖状态
            for name in self._status.in_table.keys():
                self.__update_debounce(name)
            
            # 然后更新普通IO状态
            for name in self._status.in_table.keys():
                # 如果有消抖配置，使用消抖后的状态，否则使用原始状态
                if name in self.__debounce_time:
                    self._status.in_state[name] = self.__debounce_state[name]
                else:
                    self._status.in_state[name] = self.__update_in(name)
                    
            for name in self._status.out_table.keys():
                self._status.out_state[name] = self.__update_out(name)
            for name in self._status.axis_table.keys():
                self._status.axis_state[name] = self.__update_axis(name)
            for name in self.__taskers.keys():
                self.tasker_state[name] = self.__update_tasker(name)
        except Exception as e:
            print(f"Error updating state: {e}")
    
    def update_watch(self):
        for name, value in self.watch_state.items():
            if not self.watch_enable.get(name, False):
                continue
            try:
                ioname, expected_value = value
                if self._status.in_state[ioname] == expected_value:
                    if name in self.watch_execute:
                        execute = self.watch_execute[name]
                        if callable(execute):
                            execute(self)
            except Exception as e:
                print(f"Error executing watch for {name}: {e}")
                            
    def update_tasker(self):
        for tasker in self.__taskers.values():
            if self._run_code == 0 and tasker.state == TaskState.IDLE:
                if tasker.can_start():
                    tasker.start()
    
    def __del__(self):
        self.stop()
        
    def __watch_io(self):
        if self._motion is None:
            print("Motion not initialized.")
            return
        
        for tasker in self.__taskers.values():
            tasker.set_motion(self._motion)
            tasker.set_user_state(self.user_state)
        
        self._run_code = 0
        self._stop_thread = False
        while self._stop_thread == False:
            self.update_state()
            self.update_watch()
            self.update_tasker()
            self._sleep_thread.wait(self.__scan_interval)
    
    def __update_in(self, name:str):
        if self._motion is None:
            return -1
        if name not in self._status.in_table:
            return -2
        
        return self._motion.get_input(self._status.in_table[name])
    
    def __update_out(self, name:str):
        if self._motion is None:
            return -1
        if name not in self._status.out_table:
            return -2
        
        return self._motion.get_output(self._status.out_table[name])
    
    def __update_axis(self, name:str):
        if self._motion is None:
            return -1
        if name not in self._status.axis_table:
            return -2
        
        axis = self._motion.get_axis(self._status.axis_table[name])
        if axis is None:
            return -3
        
        if name not in self._status.axis_state:
            self._status.axis_state[name] = AxisStatus()
        
        axis_status = self._status.axis_state[name]
        axis_status.dpos = axis.get_dpos()
        axis_status.mpos = axis.get_mpos()
        axis_status.idle = axis.idle()
        axis_status.enabled = axis.is_enabled()
        axis_status.homed = axis.is_homed()
        axis_status.velocity = axis.get_velocity()
        return axis_status
    
    def __update_tasker(self, name:str):
        if name not in self.tasker_state:
            return -2
        return self.__taskers[name].state
    
    def __update_user(self, name:str):
        if name not in self.user_state:
            return -2
        return self.user_state[name]
        
if __name__ == "__main__":
    import time
    import queue
    from Task import Action
    
    controller = Controller()
    controller._status.in_table = {
        "相机1触发": 1,
        "排料1触发": 2,
        "相机2触发": 3,
        "排料2触发": 4,
        "翻转触发": 5,
        "急停": 6,
        "启动": 7,
        "停止": 8,
    }
    
    controller._status.axis_table = {
        "轴1": 1,
        "轴2": 2,
        "轴3": 3,
    }
    
    def Camera1Trigger(ctrl:Controller):
        print("Camera 1 Triggered!")
        ctrl.motion.set_input(1, 0)
    
    controller.set_watch_state("相机1触发", 1)
    controller.set_watch_execute("相机1触发", Camera1Trigger)
    
    def action1_trigger(tasker:TaskerBase, userdata:dict):
        print("Executing Action 1")
        tasker.motion.set_output("output1", 1)
        tasker.user_state["task1_action1"] = 1  # Set user state for task1 to trigger
        
        if userdata is not None:
            funIdx = userdata.get('todo', None)
            if funIdx is not None:
                funName = userdata['list'][funIdx]
                userdata[funName]()
                userdata['todo'] = (funIdx + 1) % len(userdata['list'])
        return userdata
        
    # action1 = Action(name="Action 1", executor=action1_trigger, condition=TaskConditionItem(in_state={"相机1触发": 1}))
    action1 = Action(name="Action 1", executor=action1_trigger)
    
    def action2_trigger(tasker:TaskerBase, userdata:dict):
        print("Executing Action 2")
        tasker.motion.set_output("output2", 1)
        
        if userdata is not None:
            funIdx = userdata.get('todo', None)
            if funIdx is not None:
                funName = userdata['list'][funIdx]
                userdata[funName]()
                
        return userdata
        
    action2 = Action(name="Action 2", executor=action2_trigger, delay_before=1, condition=TaskConditionItem(user_state={"task2_action2": 1}))
    
    def action3_trigger(tasker:TaskerBase):
        print("Executing Action 3")
        tasker.motion.set_output("output3", 1)
        
    action3 = Action(name="Action 3", executor=action3_trigger)
    
    def action4_trigger(tasker:TaskerBase):
        print("Executing Action 4")
        if tasker.current_action.data is not None and isinstance(tasker.current_action.data, queue.Queue):
            result = tasker.current_action.data.get()
            print(f"Action 4 Result: {result}")
        tasker.motion.set_output("output4", 1)
        tasker.user_state["task2_action2"] = 1  # Set user state for task2 to trigger
        
    result_queue = queue.Queue()
    action4 = Action(name="Action 4", executor=action4_trigger, delay_before=1, data=result_queue)
    
    task1 = TaskerBase("推料1")
    task1.set_actions([action1, action2])
    task1.condition.start = TaskConditionItem(in_state={"排料1触发": 1, "相机1触发": 1})
    task1.set_userdata({"todo":0, 'list':['fun1','fun2'],'fun1':lambda :print('todo1'), 'fun2':lambda :print('todo2')})  # Initialize user state for task1
    
    task2 = TaskerBase("推料2")
    task2.set_actions([action3, action4])
    task2.condition.start = TaskConditionItem(in_state={"排料1触发": 1}, tasker_state={task1.id: TaskState.RUNNING})
    
    motion = VirtualMotion(controller._status)
    
    axis1 = motion.get_axis(1)
    axis2 = motion.get_axis(2)
    axis3 = motion.get_axis(3)
    axis1.init(max_velocity=100, max_acceleration=50, max_deceleration=50, position=0)
    axis2.init(max_velocity=100, max_acceleration=50, max_deceleration=50, position=0)
    axis3.init(max_velocity=100, max_acceleration=50, max_deceleration=50, position=0)
    
    controller.set_motion(motion)
    controller.add_tasker(task1.id, task1)
    controller.add_tasker(task2.id, task2)
    
    controller.start()
    time.sleep(1)
    motion.in_state[2] = 1
    time.sleep(1)
    motion.in_state[1] = 1
    time.sleep(1)
    motion.in_state[3] = 1
    time.sleep(1)
    result_queue.put(True)
    controller.stop()
    print(task1.__dict__)
    print(task2.__dict__)
