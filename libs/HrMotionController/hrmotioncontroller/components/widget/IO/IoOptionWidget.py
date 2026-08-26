import sys
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from qfluentwidgets import ToggleButton,FlowLayout,isDarkTheme
from ....common import MotionBase, MotionStatus

class IoOptionWidget(QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setWindowTitle("IoOptionWidget")
        self.ioList:list[ToggleButton] = []
        if isDarkTheme():
            self.setStyleSheet("IoOptionWidget {background: rgb(32,32,32);}")
        else:
            self.setStyleSheet("IoOptionWidget {background: rgb(255,255,255);}")
        self.motion:MotionBase = kwargs.get("motion", None)  # 获取传入的运动控制对象
    
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
            btn.setMaximumSize(200,50)
            btn.setMinimumSize(200,50)

    def setMotion(self, motion: MotionBase):
        """
        设置运动控制对象
        :param motion: 运动控制对象
        """
        self.motion = motion

    def setMotionStatus(self, status: MotionStatus):
        self.setIoConfig(*status.get_output_info())
        
    def initWidget(self):
        self.layout_ = FlowLayout(self)
        self.layout_.setSpacing(6)
        self.layout_.setContentsMargins(30, 30, 30, 30)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        for ioWidget in self.ioList:
            self.layout_.addWidget(ioWidget)
        self.resize(500,800)

        self.startTimer(500)

    def updateIoStatus(self):
        try:
            for btn in self.ioList:
                io = btn.property("io")  # 获取自定义属性中的IO端口信息
                if self.motion is not None and self.motion.is_connected():
                    value = self.motion.get_output(io)
                    btn.blockSignals(True)  # 阻止信号发射，避免触发按钮点击事件
                    btn.setChecked(True if value == 1 else False)  # 设置按钮为未选中状态
                    btn.blockSignals(False)  # 恢复信号发射
        except Exception as e:
            print(f"Error updating IO status: {e}", file=sys.stderr)

    def timerEvent(self, event):
        if self.isVisible():
            self.updateIoStatus()  # 定时器事件触发时更新IO状态
        return super().timerEvent(event)
    
    def onbtnClicked(self,toogle):
        btn = self.sender()  # 获取发送信号的按钮对象
        io = btn.property("io")  # 获取自定义属性中的IO端口信息
        # print(f"Button clicked for IO {toogle}")
        try:
            if toogle:
                if self.motion is not None and self.motion.is_connected():
                    self.motion.set_output(io, 1)
            else:
                if self.motion is not None and self.motion.is_connected():
                    self.motion.set_output(io, 0)
        except Exception as e:
            print(f"Error setting IO status: {e}", file=sys.stderr)

class IoOptionWidgetClient(IoOptionWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        
    def updateIoStatus(self):
        try:
            for btn in self.ioList:
                name = btn.text()  # 获取按钮文本作为IO端口信息
                if self.motion is not None and self.motion.is_connected():
                    value = self.motion.get_output(name)
                    btn.blockSignals(True)  # 阻止信号发射，避免触发按钮点击事件
                    btn.setChecked(True if value == 1 else False)  # 设置按钮为未选中状态
                    btn.blockSignals(False)
        except Exception as e:
            print(f"Error updating IO status: {e}", file=sys.stderr)
            
    def onbtnClicked(self, toogle):
        btn = self.sender()  # 获取发送信号的按钮对象
        name = btn.text()
        try:
            if toogle:
                if self.motion is not None and self.motion.is_connected():
                    self.motion.set_output(name, 1)
            else:
                if self.motion is not None and self.motion.is_connected():
                    self.motion.set_output(name, 0)
        except Exception as e:
            print(f"Error setting IO status: {e}", file=sys.stderr)
