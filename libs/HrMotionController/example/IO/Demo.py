import sys
import os

sys.path.append(os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller import VirtualMotion, VirtualAxis, MotionStatus
from hrmotioncontroller.components.widget.IO import IoWatchWidget, IoOptionWidget

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    motionStatus = MotionStatus()
    motionStatus.load_input_config(r"..\utils\input_ioconfig.xlsx")
    motionStatus.load_output_config(r"..\utils\output_ioconfig.xlsx")
    
    motion = VirtualMotion(motionStatus)
    
    in_window = IoWatchWidget()
    in_window.setMotion(motion)
    in_window.setIoConfig(*motionStatus.get_input_info())
    in_window.initWidget()
    in_window.setWindowTitle("IoWatchWidget Demo")
    in_window.resize(800, 600)
    in_window.show()
    
    out_window = IoOptionWidget()
    out_window.setMotion(motion)
    out_window.setIoConfig(*motionStatus.get_output_info())
    out_window.initWidget()
    out_window.setWindowTitle("IoOptionWidget Demo")
    out_window.resize(800, 600)
    out_window.show()
    
    app.exec()
    
    