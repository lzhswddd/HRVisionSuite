import sys
import os

sys.path.insert(0, os.getcwd())

from hrmotioncontroller import TaskerList, TaskState, Action, TaskConditionItem, Controller
from hrmotioncontroller import VirtualMotion, VirtualAxis
from hrmotioncontroller.components.widget import TaskerWatchWidget
import time
import queue

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

class MainController:
    def __init__(self):
        self.controller = Controller()
        
        def handle_event(tasker:TaskerList):
            print(f"TaskerList Event: {tasker.id}, State: {tasker.state}, {tasker.error_messages}")
            
        self.controller.register_tasker_event(TaskState.COMPLETED, handle_event)
        self.controller.register_tasker_event(TaskState.FAILED, handle_event)
        
        self.controller._status.in_table = {
            "相机1触发": 1,
            "排料1触发": 2,
            "相机2触发": 3,
            "排料2触发": 4,
            "翻转触发": 5,
            "急停": 6,
            "启动": 7,
            "停止": 8,
        }
        
        self.controller._status.axis_table = {
            "轴1": 1,
            "轴2": 2,
            "轴3": 3,
        }
        
        def Camera1Trigger(ctrl:Controller):
            print("Camera 1 Triggered!")
            ctrl.motion.set_input(1, 0)
        
        self.controller.set_watch_state_by_ioname("相机1触发", 1)
        self.controller.set_watch_execute("相机1触发", Camera1Trigger)
        
        def action1_trigger(tasker:TaskerList, userdata:dict):
            print("Executing Action 1")
            tasker.motion.set_output("output1", 1)
            tasker.user_state["task1_action1"] = 1  # Set user state for task1 to trigger
            
            if userdata is not None:
                funIdx = userdata.get('todo', None)
                if funIdx is not None:
                    funName = userdata['list'][funIdx]
                    userdata[funName]()
                    userdata['todo'] = (funIdx + 1) % len(userdata['list'])
            
        # action1 = Action(name="Action 1", executor=action1_trigger, condition=TaskConditionItem(in_state={"相机1触发": 1}))
        action1 = Action(name="Action 1", executor=action1_trigger)
        
        def action2_trigger(tasker:TaskerList, userdata:dict):
            print("Executing Action 2")
            tasker.motion.set_output("output2", 1)
            
            if userdata is not None:
                funIdx = userdata.get('todo', None)
                if funIdx is not None:
                    funName = userdata['list'][funIdx]
                    userdata[funName]()
        action2 = Action(name="Action 2", executor=action2_trigger, delay_before=1, condition=TaskConditionItem(user_state={"task2_action2": 1}))
        
        def action3_trigger(tasker:TaskerList):
            print("Executing Action 3")
            tasker.motion.set_output("output3", 1)
        action3 = Action(name="Action 3", executor=action3_trigger)
        
        def action4_trigger(tasker:TaskerList):
            print("Executing Action 4")
            if tasker.current_action.data is not None and isinstance(tasker.current_action.data, queue.Queue):
                result = tasker.current_action.data.get()
                print(f"Action 4 Result: {result}")
            tasker.motion.set_output("output4", 1)
            tasker.user_state["task2_action2"] = 1  # Set user state for task2 to trigger
            # raise RuntimeError("Simulated failure in Action 4")
            
        self.result_queue = queue.Queue()
        action4 = Action(name="Action 4", executor=action4_trigger, delay_before=1, data=self.result_queue)
        
        self.task1 = TaskerList("推料1")
        self.task1.set_actions([action1, action2])
        self.task1.condition.start = TaskConditionItem(in_state={"排料1触发": 1, "相机1触发": 1})
        self.task1.set_userdata({"todo":0, 'list':['fun1','fun2'],'fun1':lambda :print('todo1'), 'fun2':lambda :print('todo2')})  # Initialize user state for task1
        
        self.task2 = TaskerList("推料2")
        self.task2.set_actions([action3, action4])
        self.task2.start_action = action3
        self.task2.condition.start = TaskConditionItem(in_state={"排料1触发": 1}, tasker_state={self.task1.id: TaskState.RUNNING})
        
        self.motion = VirtualMotion(self.controller._status, axis_numbers=[1,2,3])
        
        axis1 = self.motion.get_axis(1)
        axis2 = self.motion.get_axis(2)
        axis3 = self.motion.get_axis(3)
        axis1.init(max_velocity=100, acceleration=50, deceleration=50)
        axis2.init(max_velocity=100, acceleration=50, deceleration=50)
        axis3.init(max_velocity=100, acceleration=50, deceleration=50)
        axis1.enable()
        axis2.enable()
        axis3.enable()
        
        self.controller.set_motion(self.motion)
        self.controller.add_tasker(self.task1.id, self.task1)
        self.controller.add_tasker(self.task2.id, self.task2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    main_window = TaskerWatchWidget()
    
    dev = MainController()
    
    main_window.setController(dev.controller)
    main_window.initWidget()
    main_window.setWindowTitle("HrMotionController Demo")
    main_window.resize(800, 600)
    main_window.show()
    
    dev.controller.start()
    dev.controller.scan_interval = 0.1
    from HRVision.utils.tools import async_run
    
    def fun1():
        time.sleep(1)
        dev.motion.set_input(2, 1)
        time.sleep(1)
        dev.motion.set_input(1, 1)
        time.sleep(1)
        dev.motion.set_input(3, 1)
        time.sleep(1)
        dev.result_queue.put(True)
    async_run(fun1)
    
    app.exec()
    
    dev.controller.stop()
    print(dev.task1.__dict__)
    print(dev.task2.__dict__)
    