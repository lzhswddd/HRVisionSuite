from pathlib import Path
import sys
# from thirdparty import *
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
import pandas as pd
from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import (SimpleCardWidget,CaptionLabel,DotInfoBadge,
                            InfoLevel,FlowLayout,isDarkTheme,ToolTipFilter,ToolTipPosition)
from ...thirdparty import zaux as ZAUX

class IoLed(SimpleCardWidget):
    def __init__(self, name, io:int, parent=None):
        super().__init__(parent)
        self.name = name
        self.io = io

        # Create UI elements
        self.setObjectName(self.name)
        layout = QHBoxLayout(self)
        self.status = DotInfoBadge.info()
        self.label = CaptionLabel(self.name, self)

        self.status.setFixedSize(30,30)
        self.setMaximumSize(150,50)
        self.setMinimumSize(150,50)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Add elements to layout
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        layout.addWidget(self.status,0,Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label,1,Qt.AlignmentFlag.AlignLeft)
        self.label.setToolTip("IO端口:{}".format(self.io))
        self.label.installEventFilter(ToolTipFilter(self.label, 500,ToolTipPosition.BOTTOM_RIGHT))

    def setIoStatus(self, status):
        if status == 0:
            self.status.setLevel(InfoLevel.INFOAMTION)
        elif status == 1:
            self.status.setLevel(InfoLevel.SUCCESS)
        else:
            self.status.setLevel(InfoLevel.INFOAMTION)

    def getIoNum(self):
        return self.io
    
class IoWatchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IoWatchWidget")
        self.ioList:list[IoLed] = []
        if isDarkTheme():
            self.setStyleSheet("IoWatchWidget {background: rgb(32,32,32);}")
        else:
            self.setStyleSheet("IoWatchWidget {background: rgb(255,255,255);}")
               
    def setIoConfig(self, names, ios):
        """
        设置IO配置，接收名称和IO端口列表
        :param names: IO名称列表
        :param ios: IO端口列表
        """
        for btn in self.ioList:
            self.layout_.removeWidget(btn)  # 从布局中移除旧的按钮
            
        self.ioList.clear()
        for name, io in zip(names, ios):
            ioWidget = IoLed(name, int(io), self)
            self.ioList.append(ioWidget)

    def loadIoConfig(self,file_path):
        df = pd.read_excel(file_path)

        #Extract 'Name' and 'IO' columns
        names = df['Name']
        ios = df['IO']

        self.ioList.clear()
        #Create UI elements dynamically
        for name, io in zip(names, ios):
            ioWidget = IoLed(name, int(io), self)
            self.ioList.append(ioWidget)

    def initWidget(self):
        # rows = len(self.ioList) // cols
        self.layout_ = FlowLayout(self)
        self.layout_.setSpacing(6)
        self.layout_.setContentsMargins(30, 30, 30, 30)
        self.layout_.setAlignment(Qt.AlignVCenter)
        for ioWidget in self.ioList:
            self.layout_.addWidget(ioWidget)
        self.resize(500,800)

        self.startTimer(500)

    def updateIoStatus(self):
        for ioWidget in self.ioList:
           ret,value = ZAUX.ZAux_Direct_GetIn(ioWidget.getIoNum())
           if ret == 0:
                ioWidget.setIoStatus(value.value)

    def timerEvent(self, event):
        self.updateIoStatus()
        return super().timerEvent(event)


