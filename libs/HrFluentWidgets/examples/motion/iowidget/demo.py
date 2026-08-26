import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import (setTheme,Theme, FluentIcon as FIF, NavigationItemPosition)
from hrfluentwidgets import SettingInterface, AoiWindow, HrIcon


if __name__ == "__main__":
    from hrmotioncontroller.components.widget import IoWatchWidget, IoOptionWidget
    from hrmotioncontroller import VirtualMotion, MotionStatus
    
    app = QApplication(sys.argv)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    setTheme(Theme.DARK)
    
    stauts = MotionStatus()
    stauts.load_input_config(r'input_ioconfig.xlsx')
    stauts.load_output_config(r'output_ioconfig.xlsx')
    
    motion = VirtualMotion(status=stauts)
    
    window = AoiWindow()
    setting = SettingInterface()
    setting.setObjectName("settingInterface")
    
    setting.setMotion(motion)
    setting.setInputConfig(stauts.get_input_info())
    setting.setOutputConfig(stauts.get_output_info())
    setting.setIoWatchWidget(IoWatchWidget)
    setting.setIoOptionWidget(IoOptionWidget)
    
    window.setWindowIcon(HrIcon.HRICON.icon())  
    window.addSubInterface(setting, FIF.SETTING, '设置',Role= 2,position=NavigationItemPosition.BOTTOM)
    
    window.show()
    sys.exit(app.exec())