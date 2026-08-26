import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller import MotionClient, AxisClient

from hrmotioncontroller import MotionStatus
from hrmotioncontroller.components.widget.IO import IoWatchWidgetClient, IoOptionWidgetClient

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

from hrmotioncontroller.components.widget.Axis import AxisControlWidget, AxisSettingConfig
import qfluentwidgets
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt, QTimer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)
    
    client = MotionClient('127.0.0.1', 8888, scan_timeout=0.1) 
    if client.wait_for_connection() and client.wait_for_initialization():
        print("Connected to Motion Server.")
        
        # in_window = IoWatchWidgetClient()
        # in_window.setMotion(client)
        # in_window.setIoConfig(*client.motion_status.get_input_info())
        # in_window.initWidget()
        # in_window.setWindowTitle("IoWatchWidget Demo")
        # in_window.resize(800, 600)
        # in_window.show()
        
        # out_window = IoOptionWidgetClient()
        # out_window.setMotion(client)
        # out_window.setIoConfig(*client.motion_status.get_output_info())
        # out_window.initWidget()
        # out_window.setWindowTitle("IoOptionWidget Demo")
        # out_window.resize(800, 600)
        # out_window.show()

        setting_cfg = AxisSettingConfig()
        setting_cfg.load("../utils/config/axis_setting.json")
        
        widget = AxisControlWidget()

        if qfluentwidgets.isDarkTheme():
            widget.setStyleSheet("AxisControlWidget{background: rgb(32, 32, 32)}")
        else:
            widget.setStyleSheet("AxisControlWidget{background: rgb(242,242,242)}")
            
        names = setting_cfg.axis_name.value
        
        for i, name in names.items():
            axis = client.get_axis(name)
            # axis.init(max_velocity=1000, acceleration=500, deceleration=500)
            widget.addAxis(name, axis, setting_cfg)

        widget.show()
        
        # widget.axisEnable.connect(lambda enable: axis.enable() if enable else axis.disable())
        # widget.axisCancel.connect(lambda: axis.stop())
        # widget.axisAbsMove.connect(lambda p, v: axis.move_absolute(p, v))
        # widget.axisRelMove.connect(lambda p, v: axis.move_relative(p, v))
        
        sys.exit(app.exec())
    
        

   