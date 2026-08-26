from hrfluentwidgets import HrCompactSpinBox, HrCompactDoubleSpinBox
from .NumEdit import NumPad
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtWidgets import QDialog, QLineEdit
from qfluentwidgets import LineEdit

class HrTorchCompactSpinBox(HrCompactSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def mousePressEvent(self, event):
        numpad = NumPad()
        numpad.setValue(self.value())
        global_pos = self.mapToGlobal(QPoint(0, 0))
        rect=QRect(global_pos.x(), global_pos.y(), self.width(), self.height())
        numpad.setPosition(rect)

        if numpad.exec() == QDialog.Accepted:
            print("输入的值:", numpad.getValueStr())
        
class HrTorchCompactDoubleSpinBox(LineEdit):
    valueChanged = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = 0.0
        self._maximum = 100.0
        self._value = 0.0
        self._prefix = ""
        self._suffix = ""
        self._decimal = 2
        self._numpadbtnWidth = 40
        self._numpadbtnHeight = 40
        self.textChanged.connect(self.onTextChanged)
        
    def onTextChanged(self, text:str):
        if self._prefix and text.startswith(self._prefix):
            text = text[len(self._prefix):]
        if self._suffix and text.endswith(self._suffix):
            text = text[:-len(self._suffix)]
        try:
            value = float(text)
            if value == self._value:
                return
            if value < self._minimum or value > self._maximum:
                self.setText(f"{self._prefix}{self._value:.{self._decimal}f}{self._suffix}")
                return
            self._value = value
            self.valueChanged.emit(self._value)
        except ValueError:
            self.setText(f"{self._prefix}{self._value:.{self._decimal}f}{self._suffix}")
        
    def setMinimum(self, value: float):
        self._minimum = value
    
    def minimum(self) -> float:
        return self._minimum
    
    def setMaximum(self, value: float):
        self._maximum = value
        
    def maximum(self) -> float:
        return self._maximum
    
    def setValue(self, value: float):
        if value < self._minimum or value > self._maximum:
            # raise ValueError("Value out of range")
            return
        self.setText(f"{self._prefix}{value:.{self._decimal}f}{self._suffix}")
        
    def value(self) -> float:
        return self._value
    
    def setRange(self, minimum: float, maximum: float):
        self._minimum = minimum
        self._maximum = maximum
        if self._value < self._minimum:
            self.setValue(self._minimum)
        elif self._value > self._maximum:
            self.setValue(self._maximum)
    
    def setPrefix(self, prefix: str):
        self._prefix = prefix
        self.setText(f"{self._prefix}{self._value:.{self._decimal}f}{self._suffix}")
        
    def prefix(self) -> str:
        return self._prefix
    
    def setSuffix(self, suffix: str):
        self._suffix = suffix
        self.setText(f"{self._prefix}{self._value:.{self._decimal}f}{self._suffix}")
        
    def suffix(self) -> str:
        return self._suffix
    
    def setDecimals(self, decimals: int):
        self._decimal = decimals
        self.setText(f"{self._prefix}{self._value:.{self._decimal}f}{self._suffix}")
        
    def decimals(self) -> int:
        return self._decimal
        
    def setSingleStep(self, step: float):
        # This method is not implemented in this example
        pass
    
    def singleStep(self) -> float:
        # This method is not implemented in this example
        return 0.1
        
    def setNumpadButtonWidth(self, width: int):
        self._numpadbtnWidth = width
        
    def numpadButtonWidth(self) -> int:
        return self._numpadbtnWidth
    
    def setNumpadButtonHeight(self, height: int):
        self._numpadbtnHeight = height
        
    def numpadButtonHeight(self) -> int:
        return self._numpadbtnHeight
        
    def mousePressEvent(self, event):
        numpad = NumPad()
        numpad.setAllButtonHeight(self._numpadbtnHeight)
        numpad.setAllButtonWidth(self._numpadbtnWidth)
        numpad.setValue(self.value())
        numpad.setMinNum(self._minimum)
        numpad.setMaxNum(self._maximum)
        numpad.setDecimals(self._decimal)
            
        global_pos = self.mapToGlobal(QPoint(0, 0))
        rect=QRect(global_pos.x(), global_pos.y(), self.width(), self.height())
        numpad.setPosition(rect)

        if numpad.exec() == QDialog.Accepted:
            self.setValue(numpad.getValueFloat())