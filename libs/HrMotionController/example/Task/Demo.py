import sys
import os
sys.path.append(os.getcwd())

from hrmotioncontroller import Tasker, Action, TaskConditionItem
import time

if __name__ == "__main__":
    task = Tasker()
    task.delay_before = 1
    task.timeout = 1
    task._actions = [Action(executor=lambda: print("Action 1")), Action(executor=lambda: print("Action 2"))]
    
    task.condition.start = TaskConditionItem(in_state={"start": 1})
    task.condition.stop = TaskConditionItem(in_state={"stop": 1})
    # task.condition.pause = {"pause": 1}
    # task.condition.resume = {"resume": 1}
    in_state = {"start": 1, "stop": 0, "pause": 0, "resume": 0}
    out_state = {"start": 0, "stop": 0, "pause": 0, "resume": 0}
    
    task.condition_update = lambda x: Tasker.update_condition(in_state=in_state, out_state=out_state, conditions=x)
    
    print(task.can_start())
    
    task.start()
    # task.abort()
    time.sleep(1)
    task.wait_complete()
    
    print(task.__dict__)