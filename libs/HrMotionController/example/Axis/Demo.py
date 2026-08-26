
import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller import VirtualMotion
from hrmotioncontroller.components.widget.Axis import AxisControlWidget, AxisSettingConfig
import qfluentwidgets
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt, QTimer

def init_setting(setting_cfg:AxisSettingConfig):
    value = {
        1: "X轴",
        2: "Y轴",
        3: "Z轴"
    }
    setting_cfg.set(setting_cfg.axis_name.key, value)
    value = {
        "X轴": -1000.0,
        "Y轴": -1000.0,
        "Z轴": -1000.0
    }
    setting_cfg.set(setting_cfg.min_position.key, value)
    value = {
        "X轴": 1000.0,
        "Y轴": 1000.0,
        "Z轴": 1000.0
    }
    setting_cfg.set(setting_cfg.max_position.key, value)
    value = {
        "X轴": 0.1,
        "Y轴": 0.1,
        "Z轴": 0.1
    }
    setting_cfg.set(setting_cfg.single_step.key, value)
    value = {
        "X轴": 2,
        "Y轴": 2,
        "Z轴": 2
    }
    setting_cfg.set(setting_cfg.decimal.key, value)
    value = {
        "X轴": "mm",
        "Y轴": "mm",
        "Z轴": "mm"
    }
    setting_cfg.set(setting_cfg.distance_unit.key, value)
    
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)
    
    setting_cfg = AxisSettingConfig()
    setting_cfg.load("../utils/config/axis_setting.json")
    
    init_setting(setting_cfg)
    
    widget = AxisControlWidget()

    if qfluentwidgets.isDarkTheme():
        widget.setStyleSheet("AxisControlWidget{background: rgb(32, 32, 32)}")
    else:
        widget.setStyleSheet("AxisControlWidget{background: rgb(242,242,242)}")
        
    names = setting_cfg.axis_name.value
    motion = VirtualMotion(axis_numbers=[1, 2, 3])
    
    for i, name in names.items():
        axis = motion.get_axis(i)
        axis.init(max_velocity=1000, acceleration=500, deceleration=500)
        widget.addAxis(name, axis, setting_cfg, isTorch=True)

    widget.show()
    
    # widget.axisEnable.connect(lambda enable: axis.enable() if enable else axis.disable())
    # widget.axisCancel.connect(lambda: axis.stop())
    # widget.axisAbsMove.connect(lambda p, v: axis.move_absolute(p, v))
    # widget.axisRelMove.connect(lambda p, v: axis.move_relative(p, v))
    
    sys.exit(app.exec())
