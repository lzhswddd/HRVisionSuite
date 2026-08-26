from typing import Union
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon,QIntValidator
from PySide6.QtWidgets import QButtonGroup, QLabel,QBoxLayout,QWidget,QHBoxLayout


from qfluentwidgets import (ExpandSettingCard,qconfig,ConfigItem ,FluentIconBase,LineEdit,CaptionLabel
)

class IpTextEdit(QWidget):
    textChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.boxes = []
        
        # 创建4个输入框
        layout = QHBoxLayout(self)
        for _ in range(4):
            edit = LineEdit(self)
            edit.setFixedWidth(60)
            edit.setValidator(QIntValidator(0, 255))
            edit.textChanged.connect(self._on_text_changed)
            layout.addWidget(edit)
            self.boxes.append(edit)
        
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

    def _on_text_changed(self, text):
        # 自动跳转焦点
        sender = self.sender()
        if len(text) == 3 and sender != self.boxes[-1]:
            index = self.boxes.index(sender)
            self.boxes[index + 1].setFocus()
        
        # 发射完整IP
        self.textChanged.emit(self.ip())
    
    def ip(self):
        return ".".join(edit.text() for edit in self.boxes)
    
    def setValue(self,ip):
        ip_list = ip.split(".")
        for i in range(4):
            self.boxes[i].setText(ip_list[i])
    
class IpSettingCard(ExpandSettingCard):
    ipChanged = Signal(str)

    def __init__(self, configItem:ConfigItem, icon: Union[str, QIcon, FluentIconBase], title, content=None, ip=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.ip = ip or ""
        self.configItem = configItem
        self.configName = configItem.name
        self.choiceLabel = CaptionLabel(self)
        self.choiceLabel.setObjectName("choiceLabel")
        self.ipTextEdit = LineEdit(self)
        self.ipTextEdit.setClearButtonEnabled(True)
        self.ipTextEdit.setFixedWidth(200)
        self.choiceLabel.setText(self.ip)
        self.addWidget(self.choiceLabel)
        
        self.viewLayout.setSpacing(19)
        self.viewLayout.setContentsMargins(48, 18, 0, 18)

        # self.viewLayout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.viewLayout.addWidget(self.ipTextEdit)

        self._adjustViewSize()
        self.setValue(qconfig.get(self.configItem))
        configItem.valueChanged.connect(self.setValue)

        self.ipTextEdit.textChanged.connect(self._onIpChanged)

    def _onIpChanged(self, ip):
        if(ip == self.choiceLabel.text()):
            return
        
        qconfig.set(self.configItem,ip)
        self.choiceLabel.setText(ip)
        # self.choiceLabel.adjustSize()
        self.ipChanged.emit(ip)

    def setValue(self, value):
        self.ipTextEdit.setText(value)
