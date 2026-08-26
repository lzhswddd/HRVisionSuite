
import qfluentwidgets
from PySide6.QtCore import Qt, QRectF, QPointF, QEvent
from PySide6.QtGui import QWheelEvent

class HrSpinBox(qfluentwidgets.SpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccelerated(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def wheelEvent(self, event:QWheelEvent):
        if not self.hasFocus():
            event.ignore()
            return
        return super().wheelEvent(event)
    
class HrDoubleSpinBox(qfluentwidgets.DoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccelerated(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def wheelEvent(self, event:QWheelEvent):
        if not self.hasFocus():
            event.ignore()
            return
        return super().wheelEvent(event)

class HrCompactSpinBox(qfluentwidgets.CompactSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccelerated(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.spinFlyout.installEventFilter(self)
        
    def wheelEvent(self, event:QWheelEvent):
        if not self.hasFocus():
            event.ignore()
            return
        return super().wheelEvent(event)
    
    def eventFilter(self, obj, event:QEvent):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
            self.spinFlyout.setVisible(False)
            return True  # 拦截事件
        return super().eventFilter(obj, event)
    
class HrCompactDoubleSpinBox(qfluentwidgets.CompactDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccelerated(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.spinFlyout.installEventFilter(self)
        
    def wheelEvent(self, event:QWheelEvent):
        if not self.hasFocus():
            event.ignore()
            return
        return super().wheelEvent(event)
    
    def eventFilter(self, obj, event:QEvent):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
            self.spinFlyout.setVisible(False)
            return True  # 拦截事件
        return super().eventFilter(obj, event)
