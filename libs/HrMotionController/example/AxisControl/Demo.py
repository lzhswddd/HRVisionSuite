
import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy

import qfluentwidgets
import hrfluentwidgets
from hrmotioncontroller.components.widget import (
    AxisControlWidget,
    AxisSettingConfig, 
    PositionConfigWidget,
    PositionValidator)
from hrmotioncontroller import VirtualMotion, MotionBase
    
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
    value = {
        "X轴": 0,
        "Y轴": 0,
        "Z轴": -1
    }
    setting_cfg.set(setting_cfg.group.key, value)
    
class AxisInterface(QWidget):
    def __init__(self, axis_setting_cfg:AxisSettingConfig, parent=None):
        super().__init__(parent)
        
        self.axis_setting_cfg = axis_setting_cfg
        
        self.positionWidget = PositionConfigWidget(axis_setting_cfg, hrfluentwidgets.param_cfg)
        self.axisControl = AxisControlWidget()
        
        self.hlayout = QHBoxLayout(self)
        self.hlayout.addWidget(self.axisControl, stretch=0)
        self.hlayout.addWidget(self.positionWidget, stretch=2)
        # self.hlayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
    def setMotion(self, motion:MotionBase):
        all_axis = motion.get_all_axis()
        self.axis_infos = []
        for i, axis in all_axis.items():
            name = self.axis_setting_cfg.get(self.axis_setting_cfg.axis_name.key).get(i, f"轴{i}")
            self.axisControl.addAxis(name, axis, self.axis_setting_cfg, isTorch=True)   
            
    def addPosition(self, group, name, **kwargs):
        self.positionWidget.addPosition(group, name, **kwargs)
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)
    
    setting_cfg = AxisSettingConfig()
    setting_cfg.load("config/axis_setting.json")
    
    init_setting(setting_cfg)
    
    window = AxisInterface(setting_cfg)
    
    motion = VirtualMotion(axis_numbers=[1, 2, 3])
    for i in motion.axis_numbers:
        axis = motion.get_axis(i)
        axis.init(
            pulse_equivalent=setting_cfg.pulse_equivalent.value.get(i, 1),
            acceleration=setting_cfg.acceleration.value.get(i, 100.0),
            deceleration=setting_cfg.deceleration.value.get(i, 100.0),
            max_velocity=setting_cfg.max_velocity.value.get(i, 1000.0),
        )
        axis.set_velocity(100)
        
    
    window.setMotion(motion)
    
    validator = PositionValidator(setting_cfg, [0])
    for i in range(1, 50):
        item = qfluentwidgets.ConfigItem("Motion", f"Position{i}", validator.correct(None), validator)
        hrfluentwidgets.param_cfg.addParam(item)
        window.addPosition("Motion", f"Motion.Position{i}", isTorch=True)
        
    hrfluentwidgets.param_cfg.load("config/param.json")
    if qfluentwidgets.isDarkTheme():
        window.setStyleSheet("AxisInterface{background: rgb(32, 32, 32)}")
    else:
        window.setStyleSheet("AxisInterface{background: rgb(242,242,242)}")
    
    window.show()  
    app.exec()