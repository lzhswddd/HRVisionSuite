from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QGridLayout,QWidget,QDialog,QSpacerItem,QSizePolicy
from qfluentwidgets import (PushButton,PrimaryPushButton,LineEdit,ToolButton,SimpleCardWidget,CardWidget,InfoBar,InfoBarPosition,PrimaryToolButton,TransparentToolButton)
from qfluentwidgets import FluentIcon as FIF
import qfluentwidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QDoubleValidator
import sys
from PySide6.QtCore import Qt, QPoint, QRect, Signal     
class NumPad(QDialog):
    valueEntered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NumPadWidget")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        if qfluentwidgets.isDarkTheme():
            self.setStyleSheet("NumPad{background: rgb(32, 32, 32)}")
        else:
            self.setStyleSheet("NumPad{background: rgb(242,242,242)}")

        self.__initWidget__()
        self.__initConnect__()

        self.MinNum= None
        self.MaxNum= None
        self.Decimals=None

    def __initWidget__(self):
        """"""
        self.card=CardWidget(self)
        hLayout = QHBoxLayout(self)
        self.vLayout=QVBoxLayout(self.card)
        self.gLayout = QGridLayout()
        self.hLayoutLine = QHBoxLayout()
        self.lineEdit=LineEdit()
        self.leftBtn= TransparentToolButton(FIF.RETURN, self)
        self.rightBtn= TransparentToolButton(FIF.RIGHT_ARROW, self)
        self.num1Btn= PushButton("1", self)
        self.num2Btn= PushButton("2", self)
        self.num3Btn= PushButton("3", self)
        self.num4Btn= PushButton("4", self)
        self.num5Btn= PushButton("5", self)
        self.num6Btn= PushButton("6", self)
        self.num7Btn= PushButton("7", self)
        self.num8Btn= PushButton("8", self)
        self.num9Btn= PushButton("9", self)
        self.num0Btn= PushButton("0", self)
        self.backBtn= ToolButton(FIF.CANCEL, self)
        self.dotBtn= PushButton(".", self)
        self.negativeBtn= ToolButton(FIF.REMOVE, self)
        self.enterBtn= PrimaryToolButton(FIF.ACCEPT, self)
        self.cancelBtn= PrimaryToolButton(FIF.CLOSE, self) 
        self.clearBtn= ToolButton(FIF.DELETE, self)
        
        self.lineEdit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.leftBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rightBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num0Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num1Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num2Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num3Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num4Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num5Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num6Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num7Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num8Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.num9Btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.backBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dotBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.negativeBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.enterBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancelBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clearBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.negativeBtn.setFixedWidth(54)

        self.gLayout.addWidget(self.num7Btn, 0, 0)
        self.gLayout.addWidget(self.num8Btn, 0, 1)
        self.gLayout.addWidget(self.num9Btn, 0, 2)
        self.gLayout.addWidget(self.backBtn, 0, 3)
        self.gLayout.addWidget(self.num4Btn, 1, 0)
        self.gLayout.addWidget(self.num5Btn, 1, 1)
        self.gLayout.addWidget(self.num6Btn, 1, 2)
        self.gLayout.addWidget(self.clearBtn, 1, 3)
        self.gLayout.addWidget(self.num1Btn, 2, 0)
        self.gLayout.addWidget(self.num2Btn, 2, 1)
        self.gLayout.addWidget(self.num3Btn, 2, 2)
        self.gLayout.addWidget(self.enterBtn, 2, 3)
        self.gLayout.addWidget(self.negativeBtn, 3, 0)
        self.gLayout.addWidget(self.num0Btn, 3, 1)
        self.gLayout.addWidget(self.dotBtn, 3, 2)
        self.gLayout.addWidget(self.cancelBtn, 3, 3)
        self.gLayout.setContentsMargins(0,0,0,0)

        self.hLayoutLine.addWidget(self.lineEdit)
        self.hLayoutLine.addWidget(self.leftBtn)
        self.hLayoutLine.addWidget(self.rightBtn)
        self.hLayoutLine.setContentsMargins(0,0,0,0)
        self.vLayout.addLayout(self.hLayoutLine)
        self.vLayout.addLayout(self.gLayout)
        self.vLayout.setContentsMargins(6,6,6,6)
        self.vLayout.setSpacing(3)

        hLayout.addWidget(self.card)
        hLayout.setContentsMargins(0, 0, 0, 0)
        
    def __initConnect__(self):
        self.enterBtn.clicked.connect(self.onEnterBtnClicked)
        self.cancelBtn.clicked.connect(self.reject)
        self.leftBtn.clicked.connect(self.onLeftBtnClicked)
        self.rightBtn.clicked.connect(self.onRightBtnClicked)
        self.num1Btn.clicked.connect(self.onNum1BtnClicked)
        self.num2Btn.clicked.connect(self.onNum2BtnClicked)
        self.num3Btn.clicked.connect(self.onNum3BtnClicked)
        self.num4Btn.clicked.connect(self.onNum4BtnClicked)
        self.num5Btn.clicked.connect(self.onNum5BtnClicked)
        self.num6Btn.clicked.connect(self.onNum6BtnClicked)
        self.num7Btn.clicked.connect(self.onNum7BtnClicked)
        self.num8Btn.clicked.connect(self.onNum8BtnClicked)
        self.num9Btn.clicked.connect(self.onNum9BtnClicked)
        self.num0Btn.clicked.connect(self.onNum0BtnClicked)
        self.dotBtn.clicked.connect(self.onDotBtnClicked)
        self.negativeBtn.clicked.connect(self.onNegativeBtnClicked)
        self.backBtn.clicked.connect(self.onBackBtnClicked)
        self.clearBtn.clicked.connect(self.onClearBtnClicked)


    def setMinNum(self, min_num: float):
        """设置最小值"""
        self.MinNum = min_num
    
    def setMaxNum(self, max_num: float):
        """设置最大值"""
        self.MaxNum = max_num
    
    def setDecimals(self, decimals: int):
        """设置小数位数"""
        self.Decimals = decimals
    
    def setPosition(self,parentRect):
        """设置位置"""
        self.adjustSize()
        self_w=self.width()
        self_h=self.height()
        window=QApplication.topLevelWindows()[0]
        window_x=window.x()
        window_w=window.width()
        window_y= window.y()
        window_h=window.height()
        p_x= parentRect.x()
        p_y= parentRect.y()
        p_w= parentRect.width()
        p_h= parentRect.height()

        # print("self_w:", self_w, "self_h:", self_h)
        # print("window_x:", window_x, "window_w:", window_w, "window_y:", window_y, "window_h:", window_h)
        # print("p_x:", p_x, "p_y:", p_y, "p_w:", p_w, "p_h:", p_h)

        x= p_x
        y= p_y + p_h
        if p_x + p_w + self_w > window_x + window_w:
            x = window_x + window_w - self_w
        if p_y + p_h + self_h > window_y + window_h:
            y = y - self_h-p_h

        # print("x:", x, "y:", y)
        self.move(x, y)
        
    def setAllButtonWidth(self, width: int):
        """设置所有按钮的宽度"""
        for i in range(self.gLayout.rowCount()):
            for j in range(self.gLayout.columnCount()):
                item = self.gLayout.itemAtPosition(i, j)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setFixedWidth(width)

    def setAllButtonHeight(self, height: int):
        """设置所有按钮的高度"""
        for i in range(self.gLayout.rowCount()):
            for j in range(self.gLayout.columnCount()):
                item = self.gLayout.itemAtPosition(i, j)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setFixedHeight(height)

    def checkValue(self, value: str,decimals:False) -> bool:
        """检查输入值是否在指定范围内"""
        try:
            self.lineEdit.setFocus()
            if value == "":
                return True
            
            if self.Decimals is not None and "." in self.lineEdit.text() and decimals:
                if len(value.split('.')[1]) > self.Decimals:
                    InfoBar.warning("警告", f"小数点后最多只能输入{self.Decimals}位", Qt.Horizontal, isClosable=True, duration=1000, position=InfoBarPosition.TOP, parent=self.window())
                    return False

            if value[-1] == ".":
                value = value[:-1]

            num = float(value)
            # print(f"检查值: {num}, 最小值: {self.MinNum}, 最大值: {self.MaxNum}")
            if self.MinNum is not None and num < self.MinNum:
                InfoBar.warning("警告", "最小值为"+str(self.MinNum), Qt.Horizontal, isClosable=True, duration=1000, position=InfoBarPosition.TOP, parent=self.window())
                return False
            if self.MaxNum is not None and num > self.MaxNum:
                InfoBar.warning("警告", "最大值为"+str(self.MaxNum), Qt.Horizontal, isClosable=True, duration=1000, position=InfoBarPosition.TOP, parent=self.window())
                return False
            return True
        except ValueError:
            """如果转换失败，提示错误"""
            InfoBar.error("错误", "请输入有效的数字", Qt.Horizontal, isClosable=True, duration=1000, position=InfoBarPosition.TOP, parent=self.window())
            return False
    
    def onNum1BtnClicked(self):
        if self.checkValue(self.getCheckValue(1), True):
            self.lineEdit.insert("1")
        
    def onNum2BtnClicked(self):
        if self.checkValue(self.getCheckValue(2), True):
            self.lineEdit.insert("2")
 
        
    def onNum3BtnClicked(self):
        if self.checkValue(self.getCheckValue(3), True):
            self.lineEdit.insert("3")
           
        
    def onNum4BtnClicked(self):
        if self.checkValue(self.getCheckValue(4), True):
            self.lineEdit.insert("4")
           
        
    def onNum5BtnClicked(self):
        if self.checkValue(self.getCheckValue(5), True):
            self.lineEdit.insert("5")
           
        
    def onNum6BtnClicked(self):
        if self.checkValue(self.getCheckValue(6),True):
            self.lineEdit.insert("6")
           
        
    def onNum7BtnClicked(self):
        if self.checkValue(self.getCheckValue(7), True):
            self.lineEdit.insert("7")
           
        
    def onNum8BtnClicked(self):
        if self.checkValue(self.getCheckValue(8), True):
            self.lineEdit.insert("8")
           
        
    def onNum9BtnClicked(self):
        if self.checkValue(self.getCheckValue(9), True):
            self.lineEdit.insert("9")
           
        
    def onNum0BtnClicked(self):
        if self.checkValue(self.getCheckValue(0), True):
            self.lineEdit.insert("0")
           
        
    def onDotBtnClicked(self):
        if self.lineEdit.text() == "":
            self.lineEdit.insert("0.")
           
        if "." not in self.lineEdit.text():
            self.lineEdit.insert(".")
           
        
    def onNegativeBtnClicked(self):
        if "-" in self.lineEdit.text():
            temp=self.checkValue(self.lineEdit.text().lstrip("-"),False)
        else:
            temp=self.checkValue("-"+self.lineEdit.text(),False)

        if temp==False:
            return
        if not self.lineEdit.text().startswith("-"):
            self.lineEdit.setText("-" + self.lineEdit.text())
        else:
            self.lineEdit.setText(self.lineEdit.text().lstrip("-"))
    
    def onBackBtnClicked(self):
        """清除按钮点击事件"""
        if self.lineEdit.text() != "":
            self.lineEdit.backspace()

    def onClearBtnClicked(self):
        """清除按钮点击事件"""
        self.lineEdit.setText("")
    
    def onEnterBtnClicked(self):
        """确认按钮点击事件"""
        if self.checkValue(self.lineEdit.text(),True):
            self.valueEntered.emit(self.lineEdit.text())
            self.accept()
        else:
            self.reject()

    def onLeftBtnClicked(self):
        """左移按钮点击事件"""
        cursor = self.lineEdit.cursorPosition()
        if cursor > 0:
            self.lineEdit.setCursorPosition(cursor - 1)
            
    def onRightBtnClicked(self):
        """右移按钮点击事件"""
        cursor = self.lineEdit.cursorPosition()
        if cursor < len(self.lineEdit.text()):
            self.lineEdit.setCursorPosition(cursor + 1)

    def getValueStr(self) -> str:
        """获取输入的值"""
        return self.lineEdit.text()
    
    def getValueFloat(self) -> float:
        """获取输入的值，转换为浮点数"""
        try:
            return float(self.lineEdit.text())
        except ValueError:
            return 0.0
    
    def setValue(self, value: float):
        """设置输入的值"""
        self.lineEdit.setText(str(value))
        
    def showEvent(self, arg__1):
        self.lineEdit.setFocus()
        self.lineEdit.selectAll()
        return super().showEvent(arg__1)

    def getCheckValue(self,num:int) -> str:
        """获取检查值"""
        cursor_pos = self.lineEdit.cursorPosition()
        if num==0 and self.lineEdit.text()=="0":
            return "0"
        else:
            text=self.lineEdit.text()
            value = text[:cursor_pos] + str(num) + text[cursor_pos:]
            return value

if __name__ == "__main__":
    app = QApplication(sys.argv)

    wdg= QWidget()
    vlayout = QVBoxLayout(wdg)
    wdg.resize(800,600)

    numpad1= NumPad()
    btn1= PushButton("按钮1")
    line3= LineEdit()
    line4= LineEdit()
    numpad1.setMinNum(-50)
    numpad1.setMaxNum(100)
    numpad1.setDecimals(2)
    line3.setFixedWidth(80)
    line4.setFixedWidth(80)
    # numpad1.numPad.setAllButtonHeight(100)
    # numpad1.numPad.setAllButtonWidth(100)
    
    hLayout1 = QHBoxLayout()
    hLayout1.addWidget(numpad1)
    hLayout1.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    hLayout1.addWidget(btn1)
    hLayout1.setAlignment(Qt.AlignTop)

    hLayout2 = QHBoxLayout()
    hLayout2.addWidget(line3)
    hLayout2.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
    hLayout2.addWidget(line4)
    hLayout2.setAlignment(Qt.AlignBottom)

    vlayout.addLayout(hLayout1)
    vlayout.addLayout(hLayout2)


    def onBtn1Clicked():
        """按钮点击事件"""
        numpad=NumPad()

        global_pos = btn1.mapToGlobal(QPoint(0, 0))
        rect=QRect(global_pos.x(), global_pos.y(), btn1.width(), btn1.height())
        numpad.setPosition(rect)

        if numpad.exec() == QDialog.Accepted:
            print("输入的值:", numpad.getValueStr())
    btn1.clicked.connect(onBtn1Clicked)

    def onLine3Clicked():
        """LineEdit点击事件"""
        numpad=NumPad()

        global_pos = line3.mapToGlobal(QPoint(0, 0))
        rect=QRect(global_pos.x(), global_pos.y(), line3.width(), line3.height())
        numpad.setPosition(rect)

        if numpad.exec() == QDialog.Accepted:
            line3.setText(numpad.getValueStr())
    line3.mousePressEvent = lambda event: onLine3Clicked()

    def onLine4Clicked():
        """NumEdit点击事件"""
        def onValueEntered(value: str):
            """处理输入值"""
            line4.setText(value)
        numpad=NumPad()
        numpad.valueEntered.connect(onValueEntered)
        global_pos = line4.mapToGlobal(QPoint(0, 0))
        rect=QRect(global_pos.x(), global_pos.y(), line4.width(), line4.height())
        numpad.setPosition(rect)
        numpad.setValue(float(line4.text()) if line4.text() else 0)
        if numpad.exec() == QDialog.Accepted:
            print("输入的值:", numpad.getValueStr())
    line4.mousePressEvent = lambda event: onLine4Clicked()

    wdg.show()
    sys.exit(app.exec())