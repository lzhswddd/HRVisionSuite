import sys
import os

sys.path.insert(0, os.getcwd())

from hrmotioncontroller import TaskerList, TaskState, Action, TaskConditionItem, Controller, TaskerFlow, TaskerBase
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
        
        # def Camera1Trigger(ctrl:Controller):
        #     print("Camera 1 Triggered!")
        #     ctrl.motion.set_input(1, 0)
        
        # self.controller.set_watch_state_by_ioname("相机1触发", 1)
        # self.controller.set_watch_execute("相机1触发", Camera1Trigger)
        
        def action1_trigger():
            print("Executing Action 1")
            return 2
        action1 = Action(name="Action 1", executor=action1_trigger)
        
        def action2_trigger():
            print("Executing Action 2")
        action2 = Action(name="Action 2", executor=action2_trigger)
        
        def action3_trigger():
            print("Executing Action 3")
        action3 = Action(name="Action 3", executor=action3_trigger)
        
        def action4_trigger(tasker:TaskerBase):
            print("Executing Action 4")
            tasker.user_next_action = action5
            
        action4 = Action(name="Action 4", executor=action4_trigger)
        
        def action5_trigger():
            print("Executing Action 5")
            return 1
        action5 = Action(name="Action 5", executor=action5_trigger)
        
        def action6_trigger():
            print("Executing Action 6")
        action6 = Action(name="Action 6", executor=action6_trigger)
        
        def action7_trigger():
            print("Executing Action 7")
        action7 = Action(name="Action 7", executor=action7_trigger)
        
        def action8_trigger():
            print("Executing Action 8")
        action8 = Action(name="Action 8", executor=action8_trigger)
        
        
        self.task1 = TaskerFlow("推料1")
        self.task1.set_actions([
            action1, # Action 1
            action2, # Action 2
            action3, # Action 3
            action4, # Action 4
            action5, # Action 5
            action6, # Action 6
            action7, # Action 7
            action8, # Action 8
        ])
        self.task1.set_output_connection(action1, [action2, action3, action4])
        self.task1.set_output_connection(action2, [action5])
        self.task1.set_output_connection(action5, [action6, action7, action8])
        self.task1.set_start_action(action1)
        
        self.task1.condition.start = TaskConditionItem(in_state={"排料1触发": 1, "相机1触发": 1},user_state={"test": True})
        
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
        self.testlist = []
        self.controller.user_callback["test"] = lambda: len(self.testlist) > 0

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
        print("Inputs set, waiting for task execution...")
        time.sleep(1)
        dev.testlist.append("test item")
    async_run(fun1)
    
    app.exec()
    
    dev.controller.stop()
    print(dev.task1.__dict__)
    