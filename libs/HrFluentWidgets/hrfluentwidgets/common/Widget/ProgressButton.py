from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor, QIcon
from PySide6.QtCore import Qt
import qfluentwidgets
from qfluentwidgets.common.overload import singledispatchmethod
from enum import Enum

class ProgressPushButton(qfluentwidgets.PrimaryPushButton):
    class State(Enum):
        Normal = 0
        Loading = 1
        Running = 2
    
    @singledispatchmethod
    def __init__(self, parent:QWidget=None):
        super().__init__(parent)
        self.init()

    @__init__.register
    def _(self, text:str, parent:QWidget=None):
        super().__init__(text, parent)
        self.init()

    @__init__.register
    def _(self, icon:QIcon, text:str, parent:QWidget=None):
        super().__init__(icon, text, parent)
        self.init()

    def init(self):        
        self.progressRing = qfluentwidgets.ProgressRing(self)
        self.loadingRing = qfluentwidgets.IndeterminateProgressRing(self, False)

        self.progressRing.setRange(0, 100)
        self.loadingRing.setStrokeWidth(2)
        self.progressRing.setStrokeWidth(2)
        self.loadingRing.setFixedSize(20, 20)
        self.progressRing.setFixedSize(20, 20)
        self.loadingRing.setCustomBarColor(QColor(255, 255, 255), QColor(0, 0, 0))
        self.progressRing.setCustomBarColor(QColor(255, 255, 255), QColor(0, 0, 0))
        self.loadingRing.setCustomBackgroundColor(QColor(255, 255, 255, 102), QColor(0, 0, 0, 50))
        self.progressRing.setCustomBackgroundColor(QColor(255, 255, 255, 102), QColor(0, 0, 0, 50))

        self.reset()
        self.setStyleSheet(self.styleSheet()+
        """
            ProgressPushButton[textVisible=false] {
                color: transparent;
            }
        """)

    def setState(self, state):
        self.state = state
        self.setProperty("textVisible", state == ProgressPushButton.State.Normal)

        self.loadingRing.setVisible(state == ProgressPushButton.State.Loading)
        self.progressRing.setVisible(state == ProgressPushButton.State.Running)

        if self.isLoading():
            self.loadingRing.start()
        else:
            self.loadingRing.stop()

        self.setStyle(QApplication.style())
        self.update()

    def setProgressValue(self, value):
        self.progressRing.setValue(value)

    def progressValue(self):
        return self.progressRing.value()

    def load(self):
        self.setState(ProgressPushButton.State.Loading)

    def run(self):
        self.setState(ProgressPushButton.State.Running)

    def reset(self):
        self.normal()
        self.setProgressValue(0)

    def normal(self):
        self.setState(ProgressPushButton.State.Normal)

    def isNormal(self):
        return self.state == ProgressPushButton.State.Normal

    def isLoading(self):
        return self.state == ProgressPushButton.State.Loading

    def isRunning(self):
        return self.state == ProgressPushButton.State.Running

    def isFinished(self):
        return self.progressValue() == self.progressRing.maximum()

    def setPause(self, isPause):
        self.progressRing.setPaused(isPause)

    def isPaused(self):
        return self.progressRing.isPaused()

    def setError(self, isError):
        self.progressRing.setError(isError)

    def isError(self):
        return self.progressRing.isError()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loadingRing.move(self.width() // 2 - 10, self.height() // 2 - 10)
        self.progressRing.move(self.width() // 2 - 10, self.height() // 2 - 10)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.isNormal():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0) if qfluentwidgets.isDarkTheme() else QColor(255, 255, 255))

        x = self.width() // 2 - 4
        y = self.height() // 2 - 4
        painter.drawRoundedRect(x, y, 8, 8, 2, 2)

    def drawIcon(self, painter, rect, state):
        if self.isNormal():
            super().drawIcon(painter, rect, state)
