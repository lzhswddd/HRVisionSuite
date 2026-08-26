from pathlib import Path
import subprocess
import threading
from enum import Enum

class TrainWatcher:
    class Status(Enum):
        IDLE = "Idle"
        STARTING = "Starting"
        RUNNING = "Running"
        COMPLETED = "Completed"
        FAILED = "Failed"
        
    def __init__(self):
        self.batch = 0
        self.batchs = 0
        self.epoch = 0
        self.epochs = 0
        self.process = None
        self.start_time = None
        self.end_time = None
        self.thread = None
        self.args = None
        self.__status = self.Status.IDLE
        self.result_weight_path = None
        self.error_message = None

        self.callbacks = {
            'on_error': [],
            'on_program_start': [],
            'on_program_end': [],
            'on_model_load': [],
            'on_train_start': [],
            'on_train_end': [],
            'on_train_epoch_start': [],
            'on_train_batch_start': [],
            'on_train_batch_end': [],
            'on_train_epoch_end': [],
            'on_pretrain_routine_start': [],
            'on_pretrain_routine_end': []
        }

        self.script_path = None
        self.exe_path = None
        self.working_directory = None

    def __del__(self):
        self.stop()

    def _parse_progress(self, line):
        pass
                        
    def add_callback(self, event, callback):
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            print(f"Event '{event}' not recognized. Available events: {list(self.callbacks.keys())}")

    def remove_callback(self, event, callback):
        if event in self.callbacks:
            if callback in self.callbacks[event]:
                self.callbacks[event].remove(callback)
            else:
                print(f"Callback not found for event '{event}'.")
    
    @property
    def status(self):
        return self.__status
    
    @status.setter
    def status(self, value):
        if isinstance(value, self.Status):
            self.__status = value
        else:
            raise ValueError(f"Status must be an instance of Status Enum, got {type(value)}")
            
    def read_output(self):
        for line in self.process.stdout:
            decoded_line = line.decode("utf-8").strip()
            self._parse_progress(decoded_line)
        self.process = None
        self.thread = None
            
    def start(self, script_path, exe_path=None, working_directory=None, **kwargs):
        try:
            if exe_path is None:
                exe_path = 'python'
            if working_directory is None:
                working_directory = Path(script_path).parent
            if self.process is not None:
                print("A training process is already running.")
                return
            if self.thread is not None and self.thread.is_alive():
                print("A training watcher thread is already running.")
                return
            self.error_message = None
            
            args = []
            for key, value in kwargs.items():
                args.append(f"--{key}")
                if value is not None:
                    args.append(str(value))
                    
            self.args = kwargs
            self.script_path = script_path
            self.exe_path = exe_path
            self.working_directory = working_directory
            # 使用 subprocess 执行脚本并实时获取输出
            self.process = subprocess.Popen(
                [exe_path, script_path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=working_directory
            )
            # 开一个线程异步读取输出
            self.thread = threading.Thread(target=self.read_output)
            self.thread.start()
            
            self.__status = self.Status.STARTING
        except Exception as e:
            print(f"An error occurred: {e}")
            
    def stop(self):
        if self.__status == self.Status.RUNNING or self.__status == self.Status.STARTING:
            if self.process:
                self.process.terminate()
                self.process = None
            if self.thread:
                self.thread.join()
                self.thread = None
        self.__status = self.Status.IDLE
        
    def wait(self):
        if self.__status == self.Status.RUNNING or self.__status == self.Status.STARTING:
            if self.process:
                self.process.wait()
                self.process = None
            if self.thread:
                self.thread.join()
                self.thread = None

    def progress(self):
        if self.epochs > 0 and self.batchs > 0:
            total_batches = self.epochs * self.batchs
            completed_batches = (self.epoch - 1) * self.batchs + self.batch
            return completed_batches / total_batches * 100
        return 0

    def is_finished(self):
        return self.__status in (self.Status.COMPLETED, self.Status.FAILED)
    
    def restart(self):
        self.stop()
        self.start(self.script_path, 
                    exe_path=self.exe_path, 
                    working_directory=self.working_directory, 
                    **self.args)
     
TrainWatcherManager = {}
    
def GetTrainWatcherList() -> list:
    """
    获取所有支持的 TrainWatcher 类型列表
    :return: 支持的 TrainWatcher 类型列表
    """
    return list(TrainWatcherManager.keys())
    
def GenerateTrainWatcher(type: str) -> TrainWatcher:
    if type in TrainWatcherManager:
        return TrainWatcherManager[type]()
    else:
        raise ValueError(f"Unsupported TrainWatcher type: {type}. Supported types: {list(TrainWatcherManager.keys())}")
    
if __name__ == "__main__":
    # 替换为你要执行的脚本路径
    script_path = "AITrain.py"
    watcher = GenerateTrainWatcher('Ultralytics')
    watcher.add_callback('on_train_start', lambda x: print("Training started."))
    watcher.add_callback('on_train_end', lambda x: print("Training ended."))
    watcher.add_callback('on_train_epoch_start', lambda x: print(f"Epoch {x.epoch} / {x.epochs} started."))
    watcher.add_callback('on_train_batch_start', lambda x: print(f"Batch {x.batch} / {x.batchs} started."))
    watcher.add_callback('on_train_batch_end', lambda x: print(f"Batch {x.batch} / {x.batchs} ended."))
    watcher.add_callback('on_train_epoch_end', lambda x: print(f"Epoch {x.epoch} / {x.epochs} ended."))
    watcher.add_callback('on_pretrain_routine_start', lambda x: print("Pre-training routine started."))
    watcher.add_callback('on_pretrain_routine_end', lambda x: print("Pre-training routine ended."))
    
    watcher.start(script_path, 
                  model='yolo', 
                  weights='yolov8n.pt', 
                  data=r'D:\Python\yolov5_export\data\popian1.yaml', 
                  epochs=20, 
                  batch_size=8, 
                  workers=4)
    watcher.wait()
    