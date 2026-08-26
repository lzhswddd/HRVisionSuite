import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrmotioncontroller import (
    MotionServer, VirtualMotion, MotionBase,
    MotionStatus, AxisStatus, 
    Controller
    )

from hrmotioncontroller.components.widget import (
    AxisControlWidget,
    AxisSettingConfig, 
    PositionValidator,
    PositionConfigWidget,
    PositionSelectWidget,
    IoWatchWidgetClient, 
    IoOptionWidgetClient
    )

from hrmotioncontroller.components.widget.Axis import (
    AxisControlWidget, AxisSettingConfig
    )

import qfluentwidgets
import hrfluentwidgets

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt, QTimer

def init_setting(setting_cfg:AxisSettingConfig):
    value = {
        1: "X轴",
        2: "Y轴",
        3: "Z轴",
        # 4: "θ轴",
        # 5: "Y1轴",
        # 6: "Y2轴"
    }
    setting_cfg.set(setting_cfg.axis_name.key, value)
    value = {}
    for v in setting_cfg.axis_name.value.values():
        value[v] = -1000
    setting_cfg.set(setting_cfg.min_position.key, value)
    value = {}
    for v in setting_cfg.axis_name.value.values():
        value[v] = 1000
    setting_cfg.set(setting_cfg.max_position.key, value)
    value = {}
    for v in setting_cfg.axis_name.value.values():
        value[v] = 0.1
    setting_cfg.set(setting_cfg.single_step.key, value)
    value = {}
    for v in setting_cfg.axis_name.value.values():
        value[v] = 2
    setting_cfg.set(setting_cfg.decimal.key, value)
    value = {}
    for v in setting_cfg.axis_name.value.values():
        value[v] = 'mm'
    setting_cfg.set(setting_cfg.distance_unit.key, value)

class AxisInterface(QWidget):
    def __init__(self, group:str, positionKey:str, axis_setting_cfg:AxisSettingConfig, parent=None):
        super().__init__(parent)
        
        self.axis_setting_cfg = axis_setting_cfg
        
        self.positionWidget = PositionConfigWidget(axis_setting_cfg)
        self.axisControl = AxisControlWidget()
        self.positionSelectWidget = PositionSelectWidget(group, positionKey, axis_setting_cfg)
        
        self.hlayout = QHBoxLayout(self)
        self.hlayout.addWidget(self.axisControl, stretch=0)
        self.hlayout.addWidget(self.positionWidget, stretch=2)
        self.hlayout.addWidget(self.positionSelectWidget, stretch=0)
        # self.hlayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
    def setMotion(self, motion:MotionBase):
        all_axis = motion.get_all_axis()
        self.axis_infos = {}
        for i, axis in all_axis.items():
            name = self.axis_setting_cfg.get(self.axis_setting_cfg.axis_name.key).get(i, f"轴{i}")
            self.axisControl.addAxis(name, axis, self.axis_setting_cfg, canOptionAxis=True) 
  
        def move(positions):
            if positions is None:
                return
            try:
                for key, value in positions.items():
                    motion.get_axis(self.axis_setting_cfg.getAxisID(key)).move_absolute(value)
            except Exception as e:
                qfluentwidgets.InfoBar.error(
                    "错误", "移动点位失败:" + str(e),
                    parent=self.window())
        self.positionSelectWidget.moveTo.connect(move)
            
    def addPosition(self, group, name):
        self.positionWidget.addPosition(group, name)
 
def main():
    setting_cfg = AxisSettingConfig()
    setting_cfg.load("../utils/config/axis_setting.json")
    
    init_setting(setting_cfg)

    status = MotionStatus()
    status.load_input_config(r"..\utils\input_ioconfig.xlsx")
    status.load_output_config(r"..\utils\output_ioconfig.xlsx")
    
    names = list(setting_cfg.axis_name.value.values())
    motion = VirtualMotion(status, axis_numbers=setting_cfg.axis_name.value.keys())
    for key, axis in motion.get_all_axis().items():
        axis.init(
            pulse_equivalent=setting_cfg.pulse_equivalent.value.get(key, 1),
            max_velocity=setting_cfg.max_velocity.value.get(key, 1000.0),
            acceleration= setting_cfg.acceleration.value.get(key, 100.0),
            deceleration=setting_cfg.deceleration.value.get(key, 100.0)
        )
        axis.set_velocity(100)
        status.axis_table[names[key - 1]] = key
        status.axis_state[names[key - 1]] = AxisStatus()
    
    server = MotionServer('127.0.0.1', 8888, motion=motion, status=status) 
    server.start_controller()
    server.start()
    
    for i in range(50):
        server.dataMap[f'D{str(i).zfill(3)}'] = 0
    from HRVision.utils.tools import delay_execute
    def on_data_map_change(key, value):
        print(f"DataMap Change: {key} = {value}")
        delay_execute(lambda: server.write_data(key, value), 1)
        server.write_data(key, value)
        
    server.datamap_write_handle = on_data_map_change
    
    print("Motion Server started. Listening for connections...")
    
    app = QApplication(sys.argv)
    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)
    
    
    positionlist = []
    for i in range(1, 50):  
        validator = PositionValidator(setting_cfg)
        item = qfluentwidgets.ConfigItem("Motion", f"点位{i}", validator.correct(None), validator)
        hrfluentwidgets.param_cfg.addParam(item)
        positionlist.append(item.name)
        
    positionItem = qfluentwidgets.OptionsConfigItem(
        'Motion', '点位列表', 
        positionlist[0], qfluentwidgets.OptionsValidator(positionlist)
    )
    hrfluentwidgets.param_cfg.addParam(positionItem)
        
    window = AxisInterface(positionItem.group, positionItem.key, setting_cfg)
    window.setMotion(motion)
    
    for i in range(1, 50):
        window.addPosition(f"点位{i}", f"Motion.点位{i}")
        
    hrfluentwidgets.param_cfg.load("../utils/config/param.json")
    
    if qfluentwidgets.isDarkTheme():
        window.setStyleSheet("AxisInterface{background: rgb(32, 32, 32)}")
    else:
        window.setStyleSheet("AxisInterface{background: rgb(242,242,242)}")
    
    window.show()
    app.exec()
    
    # # Keep the script running to allow the server to accept connections
    # try:
    #     while True:
    #         pass
    # except KeyboardInterrupt:
    #     print("Server stopped by user.")
    
    server.stop_controller()
    server.stop()
    
if __name__ == "__main__":
    main()
