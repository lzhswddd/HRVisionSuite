import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout
from qfluentwidgets import (NavigationItemPosition, MessageBox, setTheme, Theme, MSFluentWindow,
                            NavigationAvatarWidget, qrouter, SubtitleLabel, setFont)
from qfluentwidgets import FluentIcon as FIF

class AoiWindow(MSFluentWindow):
    """ Main window """
    #检测界面
    #工单编辑界面
    #设置界面
    #标定界面
    #数据界面
    #离线测试界面
    #退出重新登录
    def __init__(self,Role:int = 0):
        super().__init__()
        self.role = Role
        self.widgetAndRoleList = {}

    def setRole(self,Role:int):
        self.role = Role
        self.updateShowStatus()

    def addSubInterface(self, interface, icon, text, Role:int=0,selectedIcon=None, position=NavigationItemPosition.TOP, isTransparent=False):
        if not interface.objectName():
            raise ValueError("The object name of `interface` can't be empty string.")
        
        ret = super().addSubInterface(interface, icon, text, selectedIcon, position, isTransparent)
        self.widgetAndRoleList[interface.objectName()] = [ret, Role]

        return ret

        # if Role >self.role:
        #     ret.setHidden(True)
        # return ret  
    
    def updateShowStatus(self):
        for item in self.widgetAndRoleList.values():
            if item[1] > self.role:
                item[0].setHidden(True)
            else:
                item[0].setHidden(False)