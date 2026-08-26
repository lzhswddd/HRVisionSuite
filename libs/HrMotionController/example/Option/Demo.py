
import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
import qfluentwidgets
import hrfluentwidgets
from hrmotioncontroller.components.widget import AxisSettingConfig, PositionValidator, PositionConfigWidget
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)
    
    setting_cfg = AxisSettingConfig()
    setting_cfg.load("config/axis_setting.json")
    
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
    
    window = PositionConfigWidget(setting_cfg)
    
    for i in range(1, 50):
        validator = PositionValidator(setting_cfg)
        item = qfluentwidgets.ConfigItem("Motion", f"Position{i}", validator.correct(None), validator)
        hrfluentwidgets.param_cfg.addParam(item)
        window.addPosition(item.name, item.key)

    hrfluentwidgets.param_cfg.load("config/param.json")
    if qfluentwidgets.isDarkTheme():
        window.setStyleSheet("PositionConfigWidget{background: rgb(32, 32, 32)}")
    else:
        window.setStyleSheet("PositionConfigWidget{background: rgb(242,242,242)}")
    
    window.show()  
    app.exec()