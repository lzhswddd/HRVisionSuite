
from PySide6.QtCore import Qt, Signal,QRectF
from PySide6.QtGui import QWheelEvent, QPainter, QColor, QPainterPath, QMouseEvent, QPixmap
from PySide6.QtWidgets import QWidget, QSlider
from qfluentwidgets import Slider, themeColor, isDarkTheme
from qfluentwidgets.components.widgets.slider import SliderHandle 
from qfluentwidgets.common.overload import singledispatchmethod

class ColorSliderHandle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.NoPen)
        if isDarkTheme():
            painter.setBrush(QColor(69, 69, 69))
        else:
            painter.setBrush(QColor(255, 255, 255))

        # Draw outer circle
        path = QPainterPath()
        path.addEllipse(QRectF(self.rect()).center(), 10, 10)

        innerPath = QPainterPath()
        innerPath.addEllipse(QRectF(self.rect()).center(), 5, 5)
        path = path.subtracted(innerPath).simplified()

        painter.setClipPath(path)
        painter.drawPath(path)

        painter.setPen(QColor(0, 0, 0, 48))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(self.rect()))

class ColorSlider(QSlider):
    colorChanged = Signal(object)

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._color = color or themeColor()
        self._handle = ColorSliderHandle(self)
        self._pressedPos = None

        self.setRange(0, 255)
        self.setSingleStep(1)
        self.setFixedHeight(20)

        self.valueChanged.connect(self._adjustHandlePos)
        self.valueChanged.connect(self.onValueChanged)

    def setColor(self, color):
        self._color = color
        self.update()

    def color(self):
        return self._color

    def mousePressEvent(self, event:QMouseEvent):
        self._pressedPos = event.pos()
        self.setValue(self._posToValue(event.pos()))

    def mouseMoveEvent(self, event:QMouseEvent):
        self.setValue(self._posToValue(event.pos()))
        self._pressedPos = event.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 4, self.width(), 12), 6, 6)
        painter.setClipPath(path)

        self._drawGroove(painter)

    def onValueChanged(self, value):
        pass

    def _adjustHandlePos(self):
        total = max(self.maximum() - self.minimum(), 1)
        delta = (self.value() - self.minimum()) * (self.width() - self._handle.width()) / total
        self._handle.move(delta, 0)

    def _posToValue(self, pos):
        pd = self._handle.width()
        gs = max(self.width() - pd, 1)
        v = pos.x() / float(gs) * (self.maximum() - self.minimum()) + self.minimum()
        return max(self.minimum(), min(round(v), self.maximum()))

    def _drawGroove(self, painter:QPainter):
        painter.setBrush(self._color)
        painter.drawRect(self.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjustHandlePos()

    def createTitledBackground(self):
        pixmap = QPixmap(8, 8)
        pixmap.fill(QColor(248, 248, 248))
        painter = QPainter(pixmap)

        color = QColor(121, 121, 121)
        painter.fillRect(4, 0, 4, 4, color)
        painter.fillRect(0, 4, 4, 4, color)
        painter.end()
        return pixmap

class HrSlider(Slider):
    @singledispatchmethod
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @__init__.register
    def _(self, orientation: Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def wheelEvent(self, event:QWheelEvent):
        if not self.hasFocus():
            event.ignore()
            return
        return super().wheelEvent(event)
    
class RangeSlider(Slider):
    rangeStartChanged = Signal(int)
    rangeEndChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rangeStart = self.minimum()
        self._rangeEnd = self.maximum()

        self._init()

    def __init__(self,orientation:Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        self._rangeStart = self.minimum()
        self._rangeEnd = self.maximum()

        self._init()

    def setRangeStart(self,start):
        start = max(min(start,self.rangeEnd()-1),self.minimum())
        if start == self.rangeStart():
            return
        self._rangeStart = start
        self._adjustHandlePos()
        self.update()

        self.rangeStartChanged.emit(start)

    def rangeStart(self):
        return self._rangeStart

    def setRangeEnd(self,end):
        end = min(max(end,self.rangeStart()+1),self.maximum())
        if end == self.rangeEnd():
            return
        self._rangeEnd = end
        self._adjustHandlePos()
        self.update()

        self.rangeEndChanged.emit(end)

    def rangeEnd(self):
        return self._rangeEnd
    
    def setRange(self,start,end):
        if end<=start:
            return
        
        super().setRange(start,end)
    
    def mousePressEvent(self, e):
        pressedPos = e.pos()
        value = self._moveClosestHandle(pressedPos)
        self.clicked.emit(value)
    
    def mouseMoveEvent(self, e):
        pressedPos = e.pos()
        value = self._moveClosestHandle(pressedPos)
        self.sliderMoved.emit(value)
    
    def _drawHorizonGroove(self, painter):
        w = self.width()
        r = self.handle.width()/2

        painter.drawRoundedRect(QRectF(r,r-2,w-r*2,4),2,2)
        if (self.maximum()-self.minimum()) == 0:
            return
        
        painter.setBrush(themeColor())
        x = self._startHandle.geometry().center().x()
        aw = (self.rangeEnd()-self.rangeStart())/(float)(self.maximum()-self.minimum())*(w-r*2)
        painter.drawRoundedRect(QRectF(x,r-2,aw,4),2,2)

    def _drawVerticalGroove(self, painter):
        h = self.height()
        r = self.handle.width()/2

        painter.drawRoundedRect(QRectF(r-2,r,4,h-2*r),2,2)

        if (self.maximum()-self.minimum()) == 0:
            return
        
        painter.setBrush(themeColor())
        y = self._startHandle.geometry().center().y()
        ah = (self.rangeEnd()-self.rangeStart())/(float)(self.maximum()-self.minimum())*(h-2*r)
        painter.drawRoundedRect(QRectF(r-2,y,4,ah),2,2)

    
    def _adjustHandlePos(self):
        total = max(self.maximum()-self.minimum(),1)
        startPos = 1.0 *(self.rangeStart()-self.minimum())/total*self.grooveLength
        endPos = 1.0 *(self.rangeEnd()-self.minimum())/total*self.grooveLength

        if(self.orientation()==Qt.Orientation.Vertical):
            self._startHandle.move(0,startPos)
            self._endHandle.move(0,endPos)
        else:
            self._startHandle.move(startPos,0)
            self._endHandle.move(endPos,0)

    def _moveClosestHandle(self, pos):
        value = self._posToValue(pos)

        if abs(value-self.rangeStart())<=abs(value-self.rangeEnd()):
            self.setRangeStart(value)
        else:
            self.setRangeEnd(value)
        return value
    
    def _init(self):
        self._startHandle = self.handle
        self._endHandle = SliderHandle(self)

        self._endHandle.pressed.connect(self.sliderPressed)
        self._endHandle.released.connect(self.sliderReleased)