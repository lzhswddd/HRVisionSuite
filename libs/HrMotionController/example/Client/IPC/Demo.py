import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller import MotionClient, AxisClient, IPC_Client

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
    
    client = IPC_Client('127.0.0.1', 8888, scan_timeout=0.1) 
    if client.wait_for_connection():
        print("Connected to Motion Server.")
        
        def on_data_changed(key, value):
            print(f"Data changed: {key} = {value}")
            
        client.data_change_handler = on_data_changed
        
        print(client.read_data("D001"))
        client.write_data("D001", 'reset')
        print(client.read_data("D001"))
        client.write_data("D001", 321)
        
        sys.exit(app.exec())
    
        

   