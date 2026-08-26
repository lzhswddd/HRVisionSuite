import math
from PySide6.QtWidgets import QGraphicsView, QGraphicsPixmapItem, QGraphicsScene, QFrame
from PySide6.QtGui import QPainter, QImage, QCursor, QTransform, QPaintEvent, QPixmap, QTouchEvent, QColor
from PySide6.QtCore import Qt,QPoint,QPointF, QRectF
from PySide6.QtSvg import QSvgRenderer
from qfluentwidgets import ToolTip, ToolTipPosition
from .._rc import resource
        
class NoImageViewBase:
    def __init__(self, parent=None):
        super().__init__(parent)
        self.noImageRenderer = QSvgRenderer(":/resource/images/noImage.svg")
        self.noImageRenderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        
    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, QGraphicsPixmapItem):
                    if item.pixmap().isNull():
                        painter = QPainter(self.viewport())
                        rect = self.rect()
                        painter.fillRect(rect, QColor.fromString("#323232"))
                        self.noImageRenderer.render(painter, rect)
                        painter.end()
                        break
        
class AutoFitViewBase:
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def showEvent(self, event):
        if self.scene() is not None:
            self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().showEvent(event)
    
    def resizeEvent(self, event):
        if self.scene() is not None:
            self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)
        
class GraphicsView(NoImageViewBase, AutoFitViewBase, QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.maxScale = 10000
        self.minScale = 0.0001
        self.movePos = QPoint(0,0)
        self.rightButtonPressed = False
        self.lastMousePos = QPoint(0,0)

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setMouseTracking(True)

        self.setStyleSheet("QGraphicsView{background:rgb(50,50,50); border:0px;border-radius:3px;}")

    def scaleUp(self):
        setp = 1.05
        factor = pow(setp, 1.0)
        t = self.transform()
        if(t.m11()==0):
            if(abs(t.m21())>self.maxScale):
                return
        else:
            if(abs(t.m11())>self.maxScale):
                return
        self.scale(factor, factor)

    def scaleDown(self):
        setp = 1.05
        factor = pow(setp, -1.0)
        t = self.transform()
        if(t.m11()==0):
            if(abs(t.m21())<self.minScale):
                return
        else:
            if(abs(t.m11())<self.minScale):
                return
        self.scale(factor, factor)

    def wheelEvent(self, event):
        delta = event.angleDelta()
        if delta.y() == 0:
            event.ignore()
            return

        d = delta.y()/abs(delta.y())

        if delta.y() > 0:
            self.scaleUp()
        else:
            self.scaleDown()
        
        self.movePos = self.mapToScene(event.position().toPoint())
        if(d>0):
            self.centerOn(self.movePos)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightButtonPressed = True
            self.lastMousePos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)  

    def mouseMoveEvent(self, event):
        if(self.rightButtonPressed):
            delta = event.pos() - self.lastMousePos
            self.lastMousePos = event.pos()

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()

        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if(event.button() == Qt.MouseButton.RightButton):
            self.rightButtonPressed = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
class DisplayCrossBase:
    def __init__(self, parent=None):
        super().__init__(parent)

        self._drawCross = False  # Whether to draw a crosshair
        self._crossColor = Qt.GlobalColor.magenta  # Color of the crosshair
        
    def isDrawCross(self) -> bool:
        return self._drawCross
    
    def setDrawCross(self, draw: bool):
        if self._drawCross == draw:
            return
        self._drawCross = draw
        self.update()  # Update the view to reflect the change
        
    def drawCrossColor(self, color: Qt.GlobalColor):
        if self._crossColor == color:
            return
        self._crossColor = color
        self.update()  # Update the view to reflect the change

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if isinstance(self, QGraphicsView):
            painter = QPainter(self.viewport())
        else:
            painter = QPainter(self)
        if self._drawCross:
            rect = self.rect()
            painter.setPen(self._crossColor)
            painter.drawLine(QPointF(rect.width() / 2, 0), QPointF(rect.width() / 2, rect.height()))
            painter.drawLine(QPointF(0, rect.height() / 2), QPointF(rect.width(), rect.height() / 2))
        painter.end()
           
class DropImageBase:
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    scene = self.scene()
                    if scene:
                        if getattr(scene, 'setImage', None):
                            scene.setImage(QImage(url.toLocalFile()))
                            break
            event.accept()
        else:
            event.ignore()

class MagnifierWidget(DisplayCrossBase, QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)   
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)     
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)    

        self.setDrawCross(True)  # Enable crosshair drawing

        self._crossSubPixel = False  # Whether to draw crosshair at sub-pixel level
        self._scene: QGraphicsScene = None
        self.zoomFactor = 1.0  # Default magnification factor
        self.center = QPointF(0, 0)
        self.transform = QTransform()
        
        
    def setCrossSubPixel(self, subpixel: bool):
        self._crossSubPixel = subpixel

    def setZoomFactor(self, factor: float):
        if factor > 0:
            self.zoomFactor = factor
        
    def scene(self) -> QGraphicsScene:
        return self._scene
        
    def setScene(self, scene:QGraphicsScene):
        if self._scene != scene:
            self._scene = scene
            
    def centerOn(self, point:QPointF):
        self.center = QPointF(point)
        if self._scene is not None:
            self.update()
            
    def setTransform(self, transform:QTransform):
        self.transform = transform
        self.transform.scale(self.zoomFactor, self.zoomFactor)
            
    def paintEvent(self, event):
        if self._scene is not None and not self.center.isNull():
            painter = QPainter(self)
            # painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
            rect = self.rect()
            target = QRectF(0, 0, rect.width(), rect.height())
            source = self.transform.inverted()[0].mapRect(target)
            if self._crossSubPixel:
                source.moveCenter(self.center)  # Adjust for pixel centering
            else:
                source.moveCenter(QPointF(math.floor(self.center.x()) + 0.5, math.floor(self.center.y()) + 0.5))
            self._scene.render(painter, target, source, Qt.AspectRatioMode.KeepAspectRatio)
            painter.setPen(self._crossColor)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))  # Draw a border around the magnifier
            painter.end()
        super().paintEvent(event)
      
class DisplayPixelBase:
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.toolTip = ToolTip('', parent=self)
        self.toolTip.setDuration(0)  # Set tooltip to stay until manually closed
        self.toolTip.adjustPos(widget=self, position=ToolTipPosition.BOTTOM_RIGHT)
        self.toolTip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.magnifierView = MagnifierWidget(self)
        self.magnifierView.setZoomFactor(4.0)  # Set magnification factor to 4x
        self.magnifierView.setGeometry(0,0,120,120)  # Set maximum size for the magnifier view
        
        self._showMagnifier = False  # Whether to show the magnifier view
        self._pixelTimerId = None
        self._displayFps = 30  # Frames per second for the magnifier update
    
    def setShowMagnifier(self, show: bool):
        if self._showMagnifier == show:
            return
        self._showMagnifier = show
        
    def isShowMagnifier(self) -> bool:
        return self._showMagnifier
    
    def setDisplayFps(self, fps: int):
        if fps > 0:
            self._displayFps = fps
    
    def getDisplayFps(self) -> int:
        return self._displayFps

    def setZoomFactor(self, factor: float):
        if self.magnifierView:
            self.magnifierView.setZoomFactor(factor)
        
    def __showToolTip(self, pos, globalPosition):
        if not self.scene():
            return
        scene:QGraphicsScene = self.scene()
        scenePos = self.mapToScene(pos)
        items = scene.items(scenePos)
        pixItem:QGraphicsPixmapItem = None
        for item in items:
            if isinstance(item, QGraphicsPixmapItem):
                pixItem = item
                break
        if pixItem:
            result = pixItem.mapFromScene(scenePos)
            image = pixItem.pixmap().toImage()
            
            if self._showMagnifier:
                if self.magnifierView.scene() != self.scene():
                    self.magnifierView.setScene(self.scene())
                self.magnifierView.setTransform(self.transform())
            
            imagePos = QPointF(min(max(0, result.x() - 0.5), image.width() - 1),
                            min(max(0, result.y() - 0.5), image.height() - 1))
            rgb = image.pixelColor(imagePos.toPoint())
            displayPos = imagePos.toPoint()
            text = f"Pos:({displayPos.x()}, {displayPos.y()})\nRGB({rgb.red()}, {rgb.green()}, {rgb.blue()})"
            self.toolTip.setText(text)
            self.toolTip.move(globalPosition)
            
            if self._showMagnifier:
                self.magnifierView.setGeometry(QRectF(globalPosition.x() + 12, globalPosition.y() - self.magnifierView.height(), self.magnifierView.width(), self.magnifierView.height()).toRect())
                self.magnifierView.centerOn(result)
            if not self.toolTip.isVisible():
                self.toolTip.show()
                if self._showMagnifier:
                    self.magnifierView.show()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control and self.underMouse():
            if self.scene() is not None:
                if  self._pixelTimerId is None:
                    self._pixelTimerId = self.startTimer(1000//self._displayFps)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            if self._pixelTimerId:
                self.killTimer(self._pixelTimerId)
                self._pixelTimerId = None
            if self.toolTip.isVisible():
                self.toolTip.hide()
                self.magnifierView.hide()
        super().keyReleaseEvent(event)

    def leaveEvent(self, event):
        if self.toolTip.isVisible():
            self.toolTip.hide()
            self.magnifierView.hide()
        if self._pixelTimerId:
            self.killTimer(self._pixelTimerId)
            self._pixelTimerId = None
        super().leaveEvent(event)
        
    def timerEvent(self, event):
        if event.timerId() == self._pixelTimerId:
            if self.hasFocus() and self.scene() is not None:
                global_pos = QCursor.pos()  # 获取鼠标的全局位置
                view_pos = self.mapFromGlobal(global_pos)  # 转换为视图坐标
                self.__showToolTip(view_pos, global_pos)
        super().timerEvent(event)

class TorchBase:
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.grabGesture(Qt.GestureType.PinchGesture)

        self._last_scale_factor = 1.0

    def event(self, event):
        # 处理触摸事件
        if event.type() == QTouchEvent.Type.TouchBegin:
            event.accept()
            return True
        elif event.type() == QTouchEvent.Type.TouchUpdate:
            self.handle_touch_event(event)
            event.accept()
            return True
        elif event.type() == QTouchEvent.Type.TouchEnd:
            event.accept()
            return True
        return super().event(event)
    
    def handle_touch_event(self, event: QTouchEvent):
        points = event.touchPoints()
        if len(points) == 2:
            # 两个手指进行缩放
            p1, p2 = points[0], points[1]
            last_distance = (p1.lastScenePos() - p2.lastScenePos()).manhattanLength()
            current_distance = (p1.scenePos() - p2.scenePos()).manhattanLength()
            if last_distance == 0:
                return
            scale_factor = current_distance / last_distance
            self.scale(scale_factor, scale_factor)
        elif len(points) == 1:
            # 单指拖动
            p1 = points[0]
            delta = p1.scenePos() - p1.lastScenePos()
            self.translate(-delta.x(), -delta.y())

class DropUrlGraphicsView(DropImageBase, GraphicsView):
    """ A graphics view that accepts image files dropped onto it. """
    
class DisplayPixelGraphicsView(DisplayPixelBase, GraphicsView):
    """ A graphics view that displays pixel information on mouse hover. """
    
class DisplayCrossGraphicsView(DisplayCrossBase, GraphicsView):
    """ A graphics view that can display a crosshair for visual reference. """

class TorchGraphicsView(TorchBase, GraphicsView):
    """ A graphics view that can display a torch for visual reference. """

class InterfaceView(DropImageBase, DisplayCrossBase, DisplayPixelBase, GraphicsView):
    """ A graphics view that combines image dropping, crosshair display, and pixel information. """