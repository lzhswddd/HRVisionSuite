from enum import Enum, Flag, auto
import threading
import time
from datetime import datetime
from typing import Callable, Sequence, Union
from abc import abstractmethod
import uuid
from .Motion import MotionBase
import inspect

class ActionBase:
    def __init__(self, name:str = "", condition:'TaskConditionItem' = None, data:object = None, delay_before=0, delay_after=0):
        """ 
        ActionBase constructor
        :param name: Name of the action
        :param condition: Condition for the action
        :param data: Data for the action
        :param delay_before: Delay before executing the action
        :param delay_after: Delay after executing the action
        """
        self.__abort = False
        self._id = uuid.uuid4().hex
        self.name = name
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.condition = condition
        self._data = data

    @property
    def id(self) -> str:
        """
        Get the unique identifier for the action
        :return: Unique identifier string
        """
        return self._id
        
    @property 
    def data(self):
        return self._data
        
    def reset(self):
        self.__abort = False
        
    def is_abort(self) -> bool:
        """
        Check if the action is aborted
        :return: True if aborted, False otherwise
        """
        return self.__abort
        
    def abort(self):
        """
        Abort the action
        """
        self.__abort = True

    @abstractmethod
    def run(self, tasker:'TaskerBase', userdata:object) -> object:
        """
        Run the action
        :param args: Arguments for the action
        :param kwargs: Keyword arguments for the action
        :return: True if successful, False otherwise
        """
        raise NotImplementedError("ActionBase.run() must be implemented in subclass.")
    
    def __call__(self, tasker, userdata:object) -> object:
        if self.is_abort():
            raise RuntimeError(f"Action aborted.")
        
        if self.delay_before > 0:
            # Delay before action
            threading.Event().wait(self.delay_before)
        
        ret = self.run(tasker, userdata)
        
        if self.delay_after > 0:
            # Delay after action
            threading.Event().wait(self.delay_after)
            
        return ret

class Action(ActionBase):
    def __init__(self, name:str = "", executor:Callable=None, condition:'TaskConditionItem' = None, data:object = None, delay_before=0, delay_after=0):
        super().__init__(name, condition, data, delay_before, delay_after)
        """ Action constructor
        :param name: Name of the action
        :param executor: Executor function for the action
        :param condition: Condition for the action
        :param data: Data for the action
        :param delay_before: Delay before executing the action
        :param delay_after: Delay after executing the action
        """
        if executor is None:
            self.need_userdata = False
            self.need_tasker = False
        else:
            sig = inspect.signature(executor)
            if len(sig.parameters) == 2:
                self.need_userdata = True
                self.need_tasker = True
            elif len(sig.parameters) == 1:
                self.need_userdata = False
                self.need_tasker = True
            else:
                self.need_userdata = False
                self.need_tasker = False
        self.executor = executor
    
    def rigster_executor(self, executor:Callable):
        """
        Register an executor function for the action
        :param executor: Executor function
        """
        if executor is None:
            self.need_userdata = False
            self.need_tasker = False
        else:
            sig = inspect.signature(executor)
            if len(sig.parameters) == 2:
                self.need_userdata = True
                self.need_tasker = True
            elif len(sig.parameters) == 1:
                self.need_userdata = False
                self.need_tasker = True
            else:
                self.need_userdata = False
                self.need_tasker = False
        self.executor = executor
        
    def unregister_executor(self):
        """
        Unregister the executor function for the action
        """
        self.executor = None
    
    def run(self, tasker:'TaskerBase', userdata:object) -> object:
        if self.executor is not None:
            if not self.need_userdata:
                # If the executor does not need userdata, call it with only tasker
                if self.need_tasker:
                    ret = self.executor(tasker)
                else:
                    ret = self.executor()
            else: 
                if self.need_tasker:
                    ret = self.executor(tasker, userdata)
                else:
                    ret = self.executor(userdata)
            
        return ret
   
class TaskState(Flag):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    STOPPED = auto()
    TIMEOUT = auto()

class TaskConditionItem:
    def __init__(self, in_state=None, out_state=None, axis_state=None, tasker_state=None, user_state=None):
        """
        TaskConditionItem constructor
        :param kwargs: Dictionary containing the initial state of the item
        :type kwargs: dict
        :description: This class is used to represent the conditions for starting, stopping, pausing, resuming, and constraints of a task.
        :example:
        >>> item = TaskConditionItem(in_state={"start": 1}, out_state={"stop": 0}, tasker_state={"running": 1}, user_state={"user1": 1})
        >>> print(item.in_state)  # Output: {'start': 1}
        >>> print(item.out_state)  # Output: {'stop': 0}
        >>> print(item.tasker_state)  # Output: {'running': 1}
        >>> print(item.user_state)  # Output: {'user1': 1}
        """
        self.in_state:dict = in_state if in_state is not None else {}
        self.out_state:dict = out_state if out_state is not None else {}
        self.axis_state:dict = axis_state if axis_state is not None else {}
        self.tasker_state:dict = tasker_state if tasker_state is not None else {}
        self.user_state:dict = user_state if user_state is not None else {}
        
    def is_empty(self):
        return len(self.in_state) == 0 and len(self.out_state) == 0 and len(self.axis_state) == 0 and len(self.tasker_state) == 0 and len(self.user_state) == 0
        
    def __eq__(self, other):
        if not isinstance(other, TaskConditionItem):
            return False
        flag1 = self.in_state == other.in_state
        flag2 = self.out_state == other.out_state
        flag3 = self.axis_state == other.axis_state
        
        flag4 = True
        for key in self.tasker_state.keys():
            if key not in other.tasker_state:
                flag4 = False
                break
            if not (self.tasker_state[key] & other.tasker_state[key]):
                flag4 = False
                break
                
        flag5 = self.user_state == other.user_state
        return (flag1 and flag2 and flag3 and flag4 and flag5)

    def check(self, in_state:dict, out_state:dict={}, axis_state:dict={}, tasker_state:dict={}, user_state:dict={}) -> bool:
        """
        Check if the current state matches the condition item
        :param in_state: Input state dictionary
        :param out_state: Output state dictionary
        :param axis_state: Axis state dictionary
        :param tasker_state: Tasker state dictionary
        :param user_state: User state dictionary
        :return: True if the condition matches, False otherwise
        """
        for key in self.in_state.keys():
            if key not in in_state or in_state[key] != self.in_state[key]:
                return False
        for key in self.out_state.keys():
            if key not in out_state or out_state[key] != self.out_state[key]:
                return False
        for key in self.axis_state.keys():
            if key not in axis_state or axis_state[key] != self.axis_state[key]:
                return False
        for key in self.tasker_state.keys():
            if key not in tasker_state or tasker_state[key] != self.tasker_state[key]:
                return False
        for key in self.user_state.keys():
            if key not in user_state or user_state[key] != self.user_state[key]:
                return False
        return True

class TaskCondition:
    def __init__(self):
        self.start = TaskConditionItem()
        self.stop = TaskConditionItem()
        self.pause = TaskConditionItem()
        self.resume = TaskConditionItem()
        self.constraints = TaskConditionItem()

class TaskerBase:
    class Type(Enum):
        Once = 0
        Loop = 1
        
    def __init__(self, name:str = "",
                 type:Type = Type.Once, 
                 delay_before=0, delay_after=0, 
                 execute_interval=0, 
                 timeout=0, 
                 scan_interval=0.03,
                 userdata=None):
        self.state = TaskState.IDLE
        self.information = []
        self.error_messages = []
        self.condition = TaskCondition()
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.execute_interval = execute_interval
        self.timeout = timeout
        self.scan_interval = scan_interval
        self.name = name
        self.type = type
        self.id = uuid.uuid4().hex

        self._current_action:ActionBase = None
        self._prev_action:ActionBase = None
        self._user_next_action:ActionBase = None
        self._user_start_action:Union[str, ActionBase] = None
        self._run_thread:threading.Thread = None
        
        self.condition_update:Callable[[Sequence[TaskConditionItem]], Sequence[TaskConditionItem]] = None
        
        self.start_time:datetime = None
        self.end_time:datetime = None
        
        self._count_time = 0
        self._allow_resume = False
        self._thread_wait = threading.Event()
        self._time_wait = threading.Event()
        
        self._userdata = userdata
        self._tempdata = None
        
        self._motion = None
        self._userstate = {}
        
        self.statechanged_event:list[Callable] = []
        
    def set_type(self, type:Type):
        """
        Set the type of the task
        :param type: Type of the task
        """
        if not isinstance(type, TaskerBase.Type):
            raise TypeError("Type must be an instance of Tasker.Type.")
        self.type = type
        
    def set_user_state(self, user_state:dict[str,int]):
        """
        Set the user state for the task
        :param user_state: User state dictionary
        """
        self._userstate = user_state
    
    def get_user_state(self) -> dict[str,int]:
        """
        Get the user state for the task
        :return: User state dictionary
        """
        return self._userstate
    
    @abstractmethod
    def find_action(self, action_name:str) -> ActionBase:
        """
        Find an action by name
        :param action_name: Name of the action
        :return: ActionBase object if found, None otherwise
        """
        raise NotImplementedError("TaskerBase.find_action() must be implemented in subclass.")
    
    @abstractmethod
    def have_action(self, action:ActionBase) -> bool:
        """
        Check if the task has a specific action
        :param action: ActionBase object to check
        :return: True if the action exists, False otherwise
        """
        raise NotImplementedError("TaskerBase.have_action() must be implemented in subclass.")
    
    @abstractmethod
    def get_all_actions(self) -> Sequence[ActionBase]:
        """
        Get the actions for the task
        :return: List of ActionBase objects
        """
        raise NotImplementedError("TaskerBase.get_all_actions() must be implemented in subclass.")
    
    @abstractmethod
    def start_current_action(self, start_action:Union[str, ActionBase]) -> ActionBase:
        """
        Set the start action for the task
        :return: None
        """
        raise NotImplementedError("TaskerBase.start_current_action() must be implemented in subclass.")

    @abstractmethod
    def run_init(self):
        """
        Initialize the task before running
        :return: None
        """
        raise NotImplementedError("TaskerBase.run_init() must be implemented in subclass.")
    
    @abstractmethod
    def prev(self) -> ActionBase:
        """
        Get the previous action for the task
        :return: Previous action for the task
        """
        raise NotImplementedError("TaskerBase.prev() must be implemented in subclass.")
    
    @abstractmethod
    def next(self, ret) -> ActionBase:
        """
        Move to the next action in the task
        :param ret: Result of the current action
        :return: Next action for the task
        """
        raise NotImplementedError("TaskerBase.next() must be implemented in subclass.")
    
    @property
    def motion(self) -> MotionBase:
        """
        Get the motion object for the task
        :return: Motion object
        """
        return self._motion
    
    @property
    def user_state(self) -> dict[str,int]:
        """
        Get the user state for the task
        :return: User state dictionary
        """
        return self._userstate
    
    @property
    def userdata(self) -> object:
        """
        Get the user data for the task
        :return: User data for the task
        """
        return self._userdata
    
    @property
    def current_action(self) -> ActionBase:
        """
        Get the current action for the task
        :return: Current action for the task
        """
        return self._current_action
    
    @property
    def user_start_action(self) -> Union[str, ActionBase]:
        """
        Get the start action for the task
        :return: Start action for the task
        """
        return self._user_start_action   
    
    @user_start_action.setter
    def user_start_action(self, action:Union[str, ActionBase]):
        self._user_start_action = action
        
    @property
    def user_next_action(self) -> ActionBase:
        """
        Get the next action for the task
        :return: Next action for the task
        """
        return self._user_next_action
    
    @user_next_action.setter
    def user_next_action(self, action:Union[str, ActionBase]):
        """
        Set the next action for the task
        :param action: ActionBase object for the next action
        """
        if isinstance(action, ActionBase):
            if self.have_action(action) is False:
                raise ValueError("Next action must be one of the task's actions.")
            self._user_next_action = action
        elif isinstance(action, str):
            action_obj = self.find_action(action)
            if action_obj is None:
                raise ValueError(f"Action '{action}' not found in task actions.")
            self._user_next_action = action_obj
        
    def set_motion(self, motion:MotionBase):
        """
        Set the motion object for the task
        :param motion: Motion object
        """
        self._motion = motion
        
    def get_motion(self) -> MotionBase:
        """
        Get the motion object for the task
        :return: Motion object
        """
        return self._motion
        
    def set_userdata(self, data:object):
        """
        Set the arguments for the task
        :param data: Arguments for the task
        """
        self._userdata = data
    
    def get_userdata(self) -> object:
        """
        Get the arguments for the task
        :return: Arguments for the task
        """
        return self._userdata
        
    def get_current_action(self) -> ActionBase:
        """
        Get the current action
        :return: Current action
        """
        return self._current_action

    def reset(self):
        if self.state == TaskState.RUNNING:
            raise RuntimeError("Task is running, cannot reset.")
        if self._run_thread is not None and self._run_thread.is_alive():
            raise RuntimeError("Task thread is running, cannot reset.")
        self._run_thread = None
        
        self.set_state(TaskState.IDLE)
        for action in self.get_all_actions():
            action.reset()
        
    def start(self, start_action:Union[str, ActionBase] = None):
        if self.state != TaskState.IDLE:
            return
        
        if self._run_thread is not None and self._run_thread.is_alive():
            return
        
        if start_action is not None:
            self.start_action = start_action
        
        self._run_thread = threading.Thread(target=self.__runmain)
        self._run_thread.start()
      
    def stop(self):
        if self.state == TaskState.IDLE:
            return
        
        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " User Controlled Stop.")
        self.set_state(TaskState.STOPPED)
            
    def pause(self):
        if self.state != TaskState.RUNNING:
            return
        
        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " User Controlled Pause.")
        self.set_state(TaskState.PAUSED)
        
    def resume(self):
        if self.state != TaskState.PAUSED:
            return
        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " User Controlled Resume.")
        self._allow_resume = True
        self._thread_wait.set()
        
    def abort(self):
        if self.state == TaskState.IDLE:
            return
        if self._run_thread is not None and self._run_thread.is_alive():
            self.set_state(TaskState.STOPPED)
            for action in self.get_all_actions():
                action.abort()
        
    def wait_complete(self):
        if self._run_thread is None:
            return
        if self._run_thread is not None and self._run_thread.is_alive():
            self._run_thread.join()
        self._run_thread = None
        
    def allow(self, watch_table:Sequence[TaskConditionItem], watch_state:TaskState, default_value:bool = False):
        def wapper(io_states:Sequence[TaskConditionItem]):
            if self.condition is None:
                raise RuntimeError("Task condition is not set.")
            
            if self.state != watch_state:
                return [False] * len(watch_table)
            
            if io_states is None:
                return [default_value] * len(watch_table)
                
            watch_states = []
            if len(io_states) >= len(watch_table):
                for i in range(len(watch_table)):
                    if(io_states[i].is_empty() and watch_table[i].is_empty()):
                        watch_states.append(default_value)
                    elif io_states[i] == watch_table[i]:
                        watch_states.append(True)
                    else:
                        watch_states.append(False)
            else:
                raise RuntimeError("Watch table and IO states length mismatch.")

            return watch_states
        return wapper
        
    def can_start(self) -> bool:
        return self.__allow_start(self.condition_update([self.condition.start, self.condition.constraints]))
    
    def set_state(self, state:TaskState):
        """
        Set the state of the task
        :param state: TaskState to set
        """
        if not isinstance(state, TaskState):
            raise TypeError("State must be an instance of TaskState.")
        
        if self.state == state:
            return
        
        self.state = state
        for callback in self.statechanged_event:
            if callable(callback):
                try:
                    callback(self, state)
                except Exception as e:
                    self.error_messages.append(f"State change callback error: {str(e)}")
    
    def register_event(self, callback:Callable):
        """
        Register a callback for state change events
        :param callback: Callback function to register
        """
        if not callable(callback):
            raise TypeError("Callback must be a callable function.")
        self.statechanged_event.append(callback)
        
    def unregister_event(self, callback:Callable):
        """
        Unregister a callback for state change events
        :param callback: Callback function to unregister
        """
        if not callable(callback):
            raise TypeError("Callback must be a callable function.")
        if callback in self.statechanged_event:
            self.statechanged_event.remove(callback)
        
    def execute(self, start_action:Union[str, ActionBase] = None) -> object:
        """
        Execute an action
        :param action: ActionBase object to execute
        :param userdata: User data for the action
        :return: Result of the action execution
        """
        if self.state != TaskState.IDLE:
            return
        
        if start_action is not None:
            self.start_action = start_action
            
        self.__runmain()
    
    @staticmethod
    def update_condition(conditions:Sequence[TaskConditionItem], in_state:dict[str,int]=None, out_state:dict[str,int]=None, axis_state:dict[str,int]=None, tasker_state:dict[str,int]=None, user_state:dict[str,int]=None)->Sequence[TaskConditionItem]:
        """
        Update the conditions based on the in_state and out_state
        :param in_state: Dictionary containing the input state
        :param out_state: Dictionary containing the output state
        :param conditions: List of TaskConditionItem to update
        :return: Updated list of TaskConditionItem
        """
        updated_conditions = []
        for item_condition in conditions:
            updated_condition = TaskConditionItem()
            if in_state is not None:
                for key in item_condition.in_state.keys():
                    if key in in_state:
                        updated_condition.in_state[key] = in_state[key]
            if out_state is not None:
                for key in item_condition.out_state.keys():
                    if key in out_state:
                        updated_condition.out_state[key] = out_state[key]
            if axis_state is not None:
                for key in item_condition.axis_state.keys():
                    if key in axis_state:
                        updated_condition.axis_state[key] = axis_state[key]
            if tasker_state is not None:
                for key in item_condition.tasker_state.keys():
                    if key in tasker_state:
                        updated_condition.tasker_state[key] = tasker_state[key]
            if user_state is not None:
                for key in item_condition.user_state.keys():
                    if key in user_state:
                        updated_condition.user_state[key] = user_state[key]
            updated_conditions.append(updated_condition)
        return updated_conditions
    
    @staticmethod
    def update_condition_realtime(conditions:Sequence[TaskConditionItem], get_in_state:Callable[[str], int]=None, get_out_state:Callable[[str], int]=None, get_axis_state:Callable[[str], int]=None, get_tasker_state:Callable[[str], int]=None, get_user_state:Callable[[str], int]=None)->Sequence[TaskConditionItem]:
        """
        Update the conditions based on the in_state and out_state
        :param get_in_state: Function to get the input state
        :param get_out_state: Function to get the output state
        :param conditions: List of TaskConditionItem to update
        :return: Updated list of TaskConditionItem
        """
        updated_conditions = []
        for condition in conditions:
            updated_condition = TaskConditionItem()
            if get_in_state is not None:
                for key in condition.in_state.keys():
                    updated_condition.in_state[key] = get_in_state(key)
            if get_in_state is not None:   
                for key in condition.out_state.keys():
                    updated_condition.out_state[key] = get_out_state(key)
            if get_axis_state is not None:
                for key in condition.axis_state.keys():
                    updated_condition.axis_state[key] = get_axis_state(key)
            if get_tasker_state is not None:
                for key in condition.tasker_state.keys():
                    updated_condition.tasker_state[key] = get_tasker_state(key)
            if get_user_state is not None:
                for key in condition.user_state.keys():
                    updated_condition.user_state[key] = get_user_state(key)
            updated_conditions.append(updated_condition)
        return updated_conditions
    
    def __allow_start(self, io_states:Sequence[TaskConditionItem]) -> bool:
        res = self.allow([self.condition.start, self.condition.constraints], TaskState.IDLE, True)(io_states)
        return all(res)
    
    def __allow_stop(self, io_state:TaskConditionItem) -> bool:
        return self.allow([self.condition.stop], TaskState.RUNNING, False)([io_state])[0]
    
    def __allow_pause(self, io_state:TaskConditionItem) -> bool:
        return self.allow([self.condition.pause], TaskState.RUNNING, False)([io_state])[0]
    
    def __allow_resume(self, io_state:TaskConditionItem) -> bool:
        return self.allow([self.condition.resume], TaskState.PAUSED, False)([io_state])[0]
    
    def __del__(self):
        if self._run_thread is not None and self._run_thread.is_alive():
            self.abort()
            self._run_thread.join()
        
    def __run(self):
        try:
            start_time = time.time()
            
            if self.timeout > 0:
                # Check for timeout
                def check_timeout(count_time:float):
                    if self._time_wait.is_set():
                        self._time_wait.clear()
                    self._time_wait.wait(count_time)
                    if self.state == TaskState.RUNNING:
                        self.set_state(TaskState.TIMEOUT)
                        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Task timeout.")
                th = threading.Thread(target=check_timeout, args=(self.timeout - self._count_time,))
                th.daemon = True
                th.start()
                
            rundata = None
            if self._tempdata is not None:
                rundata = self._tempdata
            else:
                rundata = self._userdata
                
            while self.state == TaskState.RUNNING:
                if self._current_action is not None:
                    if self._current_action.condition is not None:
                        if self.condition_update([self._current_action.condition])[0] == self._current_action.condition:
                            can_run = True
                        else:
                            can_run = False
                            self._thread_wait.wait(self.scan_interval)
                    else:
                        can_run = True
                    if can_run:
                        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Running action: " + str(self._current_action))
                        result = self._current_action(self, rundata)
                        # Next action
                        next_action = self.next(result)
                        if next_action is None:
                            if self.delay_after > 0:
                                # Delay after action
                                self._thread_wait.wait(self.delay_after)
                            self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Task completed.")
                            if self.type == TaskerBase.Type.Once:
                                self.set_state(TaskState.COMPLETED)
                            elif self.type == TaskerBase.Type.Loop:
                                self.set_state(TaskState.IDLE)
                            break
                else:
                    self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " No action to run.")
                    self.set_state(TaskState.FAILED)
                    break
                
                # Check for other conditions
                if self.condition_update is not None:
                    condition_states = self.condition_update([self.condition.stop, self.condition.pause])
                else:
                    condition_states = [None, None]
                
                if self.state == TaskState.RUNNING:
                    # Check for stop condition
                    allow_stop = self.__allow_stop(condition_states[0])
                    if allow_stop:
                        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Task stopped.")
                        self.set_state(TaskState.STOPPED)
                        break
                
                if self.state == TaskState.RUNNING:
                    # Check for pause condition
                    allow_pause = self.__allow_pause(condition_states[1])
                    if allow_pause:
                        self._tempdata = rundata
                        self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Task paused.")
                        self._count_time = time.time() - start_time
                        self.set_state(TaskState.PAUSED)
                        break
                
                if self.state == TaskState.RUNNING:
                    self._current_action = next_action
                    if self.execute_interval > 0:
                        # Delay next action
                        threading.Event().wait(self.execute_interval)
        except Exception as e:
            self.error_messages.append(f"Action Name '{self.current_action.name}' Error: " + str(e))
            self.set_state(TaskState.FAILED)
        finally:
            if self.timeout > 0:
                # Clear timeout event
                self._time_wait.set()
        
    def __run_init(self):
        self._count_time = 0
        self._allow_resume = False
        self.information = []
        self.error_messages = []
        self._tempdata = None
        self.set_state(TaskState.RUNNING)
        self.run_init()
        self._current_action = self.start_current_action(self._user_start_action)
        if self._user_start_action is not None:
            self._user_start_action = None  # Clear start action after use
        
    def __runmain(self):
        self.start_time = datetime.now()

        self.__run_init()
        
        if self.delay_before > 0:
            # Delay start
            threading.Event().wait(self.delay_before)
            
        while True:
            if self.state == TaskState.RUNNING:
                self.__run()
            # Wait for resume
            while self.state == TaskState.PAUSED:
                self._thread_wait.wait(self.scan_interval)
                allow_resume = self.__allow_resume(self.condition_update([self.condition.resume])[0])
                if allow_resume or self._allow_resume:
                    self._allow_resume = False
                    self.set_state(TaskState.RUNNING)
                    self.information.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " Task resumed.")
                    break
            if self.state != TaskState.RUNNING:
                break
            
        self.end_time = datetime.now()
       
class TaskerList(TaskerBase):
    def __init__(self, name:str = "",
                 type:TaskerBase.Type = TaskerBase.Type.Once, 
                 delay_before=0, delay_after=0, 
                 execute_interval=0, 
                 timeout=0, 
                 scan_interval=0.03,
                 userdata=None):
        super().__init__(name, type, delay_before, delay_after, execute_interval, timeout, scan_interval, userdata)
        
        self._actions:list[ActionBase] = []
        self._current_action_index = -1
        
    def find_action(self, action_name:str) -> ActionBase:
        """
        Find an action by name
        :param action_name: Name of the action
        :return: ActionBase object if found, None otherwise
        """
        if not isinstance(action_name, str):
            raise TypeError("Action name must be a string.")
        
        for action in self._actions:
            if action.name == action_name:
                return action
        return None
    
    def have_action(self, action:ActionBase) -> bool:
        """
        Check if the task has a specific action
        :param action: ActionBase object to check
        :return: True if the action exists, False otherwise
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        return action in self._actions
    
    def get_all_actions(self) -> Sequence[ActionBase]:
        """
        Get the actions for the task
        :return: List of ActionBase objects
        """
        return self._actions
    
    def start_current_action(self, start_action:Union[str, ActionBase]):
        if len(self._actions) > 0:
            if start_action is not None:
                if isinstance(start_action, str):
                    for action in self._actions:
                        if action.name == start_action:
                            self._current_action_index = self._actions.index(action)
                            break
                    else:
                        raise ValueError("Start action not found in actions list.")
                elif isinstance(start_action, ActionBase):
                    if start_action in self._actions:
                        self._current_action_index = self._actions.index(start_action)
                    else:
                        raise ValueError("Start action not found in actions list.")   
            return self._actions[self._current_action_index]
        else:
            return None
        
    def run_init(self):
        self._current_action_index = 0
        
    def prev(self, _) -> ActionBase:
        """
        Get the previous action for the task
        :return: Previous action for the task
        """
        if self._current_action_index > 0:
            self._current_action_index -= 1
            return self._actions[self._current_action_index]
        return None
    
    def next(self, _) -> ActionBase:
        """
        Move to the next action in the task
        :return: Next action for the task
        """
        if self._user_next_action is not None:
            self._current_action_index = self._actions.index(self._user_next_action)
            self._user_next_action = None
            return self._actions[self._current_action_index]
        if self._current_action_index < len(self._actions) - 1:
            self._current_action_index += 1
            return self._actions[self._current_action_index]
        return None

    @property
    def current_action_index(self) -> int:
        return self._current_action_index

    def get_prev_action(self) -> ActionBase:
        """
        Get the previous action
        :return: Previous action
        """
        if self._current_action_index > 0:
            return self._actions[self._current_action_index - 1]
        return None

    def get_next_action(self) -> ActionBase:
        """
        Get the next action
        :return: Next action
        """
        if  self._current_action_index >= 0 and self._current_action_index < len(self._actions) - 1:
            return self._actions[self._current_action_index + 1]
        return None

    def add_action(self, action:ActionBase):
        """
        Add an action to the task
        :param action: ActionBase object to add
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        self._actions.append(action)

    def remove_action(self, action:ActionBase):
        """
        Remove an action from the task
        :param action: ActionBase object to remove
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        if action in self._actions:
            self._actions.remove(action)

    def set_actions(self, actions:Sequence[ActionBase]):
        """
        Set the actions for the task
        :param actions: List of ActionBase objects
        """
        if not isinstance(actions, list):
            raise TypeError("Actions must be a list of ActionBase objects.")
        self._actions = actions
        self._current_action_index = -1
        self._current_action = None
        
    def get_actions(self) -> Sequence[ActionBase]:
        """
        Get the actions for the task
        :return: List of ActionBase objects
        """
        return self._actions

class TaskerFlow(TaskerBase):
    def __init__(self, name:str = "",
                 type:TaskerBase.Type = TaskerBase.Type.Once, 
                 delay_before=0, delay_after=0, 
                 execute_interval=0, 
                 timeout=0, 
                 scan_interval=0.03,
                 userdata=None):
        super().__init__(name, type, delay_before, delay_after, execute_interval, timeout, scan_interval, userdata)
        
        self._start_action:ActionBase = None
        self._actions:dict[str, ActionBase] = []
        self._input_connections:dict[str, list[str]] = {}
        self._output_connections:dict[str, list[str]] = {}
    
    def set_start_action(self, action:ActionBase):
        """
        Set the start action for the task
        :param action: ActionBase object to set as start action
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        self._start_action = action
            
    def find_action(self, action_name:str) -> ActionBase:
        """
        Find an action by name
        :param action_name: Name of the action
        :return: ActionBase object if found, None otherwise
        """
        if not isinstance(action_name, str):
            raise TypeError("Action name must be a string.")
        
        return self._actions.get(action_name, None)

    def have_action(self, action:ActionBase) -> bool:
        """
        Check if the task has a specific action
        :param action: ActionBase object to check
        :return: True if the action exists, False otherwise
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        return action.id in self._actions
    
    def get_all_actions(self) -> Sequence[ActionBase]:
        """
        Get the actions for the task
        :return: List of ActionBase objects
        """
        return list(self._actions.values())
    
    def start_current_action(self, start_action:Union[str, ActionBase]):
        if start_action is not None:
            if isinstance(start_action, str):
                if start_action in self._actions:
                    return self._actions[start_action]
                else:
                    raise ValueError("Start action not found in actions list.")
            elif isinstance(start_action, ActionBase):
                if start_action.id in self._actions:
                    return start_action
                else:
                    raise ValueError("Start action not found in actions list.")
            else:
                raise TypeError("Start action must be a string or ActionBase instance.")
        else:
            return self._start_action

    def run_init(self):
        pass
    
    def prev(self, index) -> ActionBase:
        if self.current_action is None:
            return None
        if index is None:
            index = 0
        if self.current_action.id in self._input_connections:
            connections = self._input_connections[self.current_action.id]
            if 0 <= index < len(connections):
                return self._actions[connections[index]]
            
    def next(self, index) -> ActionBase:
        if self.current_action is None:
            return None
        if index is None:
            index = 0
        if self._user_next_action is not None:
            next_action = self._user_next_action
            self._user_next_action = None
            return next_action
        if self.current_action.id in self._output_connections:
            connections = self._output_connections[self.current_action.id]
            if 0 <= index < len(connections):
                return self._actions[connections[index]]
        return None
    
    def add_action(self, action:ActionBase):
        """
        Add an action to the task
        :param action: ActionBase object to add
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        self._actions[action.id] = action
        
    def remove_action(self, action:ActionBase):
        """
        Remove an action from the task
        :param action: ActionBase object to remove
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        if action.id in self._actions:
            del self._actions[action.id]
        
    def set_actions(self, actions:Sequence[ActionBase]):
        """
        Set the actions for the task
        :param actions: List of ActionBase objects
        """
        if not isinstance(actions, list):
            raise TypeError("Actions must be a list of ActionBase objects.")
        self._actions = {action.id: action for action in actions}
        
    def get_actions(self) -> Sequence[ActionBase]:
        """
        Get the actions for the task
        :return: List of ActionBase objects
        """
        return list(self._actions.values())
    
    def add_input_connection(self, action:ActionBase, input_action:ActionBase):
        """
        Add an input connection to an action
        :param action: ActionBase object to connect to
        :param input_action: ActionBase object to connect from
        """
        if not isinstance(action, ActionBase) or not isinstance(input_action, ActionBase):
            raise TypeError("Both action and input_action must be instances of ActionBase.")
        
        if action.id not in self._input_connections:
            self._input_connections[action.id] = []
        self._input_connections[action.id].append(input_action.id)
        
    def set_input_connection(self, action:ActionBase, input_actions:Sequence[ActionBase]):
        """
        Set input connections for an action
        :param action: ActionBase object to connect to
        :param input_actions: List of ActionBase objects to connect from
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        
        self._input_connections[action.id] = [input_action.id for input_action in input_actions if isinstance(input_action, ActionBase)]
        
    def add_output_connection(self, action:ActionBase, output_action:ActionBase):
        """
        Add an output connection from an action
        :param action: ActionBase object to connect from
        :param output_action: ActionBase object to connect to
        """
        if not isinstance(action, ActionBase) or not isinstance(output_action, ActionBase):
            raise TypeError("Both action and output_action must be instances of ActionBase.")
        
        if action.id not in self._output_connections:
            self._output_connections[action.id] = []
        self._output_connections[action.id].append(output_action.id)
        
    def set_output_connection(self, action:ActionBase, output_actions:Sequence[ActionBase]):
        """
        Set output connections for an action
        :param action: ActionBase object to connect from
        :param output_actions: List of ActionBase objects to connect to
        """
        if not isinstance(action, ActionBase):
            raise TypeError("Action must be an instance of ActionBase.")
        
        self._output_connections[action.id] = [output_action.id for output_action in output_actions if isinstance(output_action, ActionBase)]

if __name__ == "__main__":
    task = TaskerList()
    task.delay_before = 1
    task.timeout = 1
    task._actions = [Action(executor=lambda: print("Action 1")), Action(executor=lambda: print("Action 2"))]
    
    task.condition.start = TaskConditionItem(in_state={"start": 1})
    task.condition.stop = TaskConditionItem(in_state={"stop": 1})
    # task.condition.pause = {"pause": 1}
    # task.condition.resume = {"resume": 1}
    in_state = {"start": 1, "stop": 0, "pause": 0, "resume": 0}
    out_state = {"start": 0, "stop": 0, "pause": 0, "resume": 0}
    
    task.condition_update = lambda x: TaskerBase.update_condition_realtime(
        lambda key: in_state.get(key, 0),
        lambda key: out_state.get(key, 0),
        lambda : {},
        lambda : {},
        x
    )
    
    print(task.can_start())
    
    task.start()
    # task.abort()
    time.sleep(1)
    task.wait_complete()
    
    print(task.__dict__)
    