import sys
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
import pandas as pd
from qfluentwidgets import ToggleButton,FlowLayout,isDarkTheme
from ...thirdparty import zaux as ZAUX

class IoOptionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IoOptionWidget")
        self.ioList:list[ToggleButton] = []
        if isDarkTheme():
            self.setStyleSheet("IoOptionWidget {background: rgb(32,32,32);}")
        else:
            self.setStyleSheet("IoOptionWidget {background: rgb(255,255,255);}")
    
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
            btn = ToggleButton(name, self)
            btn.setCheckable(True)
            btn.setToolTip(f"IO端口: {io}")
            btn.setProperty("io", io)  # 设置自定义属性，用于存储IO端口信息
            btn.toggled.connect(self.onbtnClicked)  # 连接按钮点击事件
            self.ioList.append(btn)

    def loadIoConfig(self, file_path):
        # 读取Excel文件并提取'Name'和'IO'列
        df = pd.read_excel(file_path)
        
        names = df['Name']
        ios = df['IO']

        self.ioList.clear()

        # 创建UI元素并添加到布局中
        for name, io in zip(names, ios):
            btn = ToggleButton(name, self)
            btn.setCheckable(True)
            btn.setToolTip(f"IO端口: {io}")  # 设置工具提示
            btn.setProperty("io", io)  # 设置自定义属性，用于存储IO端口信息
            btn.toggled.connect(self.onbtnClicked)  # 连接按钮点击事件
            self.ioList.append(btn)

    def initWidget(self):
        self.layout_ = FlowLayout(self)
        self.layout_.setSpacing(6)
        self.layout_.setContentsMargins(30, 30, 30, 30)
        self.layout_.setAlignment(Qt.AlignVCenter)
        for ioWidget in self.ioList:
            self.layout_.addWidget(ioWidget)
        self.resize(500,800)

        self.startTimer(500)

    def updateIoStatus(self):
        for btn in self.ioList:
            io = btn.property("io")  # 获取自定义属性中的IO端口信息
            ret,value = ZAUX.ZAux_Direct_GetOp(io)  # 调用ZAUX库中的函数获取IO状态
            if ret == 0:
                btn.setChecked(True if value.value == 1 else False)  # 设置按钮为未选中状态

    def timerEvent(self, event):
        self.updateIoStatus()  # 定时器事件触发时更新IO状态
        return super().timerEvent(event)
    
    def onbtnClicked(self,toogle):
        btn = self.sender()  # 获取发送信号的按钮对象
        io = btn.property("io")  # 获取自定义属性中的IO端口信息
        # print(f"Button clicked for IO {toogle}")
        if toogle:
            ZAUX.ZAux_Direct_SetOp(io,1)  # 调用ZAUX库中的函数设置IO状态为1
        else:
            ZAUX.ZAux_Direct_SetOp(io,0)  # 调用ZAUX库中的函数设置IO状态为0


