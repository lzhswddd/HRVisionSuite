from PySide6.QtCore import Qt,QRectF,QPointF,Signal,QObject
from PySide6.QtGui import QBrush,QColor
from PySide6.QtWidgets import QGraphicsRectItem,QStyle,QGraphicsItem
import weakref

class RectItemData:
    def __init__(self,id= "None",depend="None",rect=QRectF(0,0,0,0),penColor=Qt.GlobalColor.green,type = "GraphicsRectItem"):
        self.id = id
        self.depend = depend
        self.type = type
        self.rect:QRectF = rect
        self.penColor:QColor = penColor

class GraphicsRectItem(QObject,QGraphicsRectItem):
    itemPosChanged = Signal(QPointF)
    itemSizeChanged = Signal(QRectF)

    def __init__(self,parent=None):
        QGraphicsRectItem.__init__(self,parent)
        QObject.__init__(self, None)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)

        self.penColor:QColor = QColor(Qt.GlobalColor.green)
        self.brushColor = Qt.GlobalColor.transparent
        self.lineStyle = Qt.PenStyle.SolidLine
        self.handleColor = Qt.GlobalColor.blue

        self.setData(Qt.UserRole+1,False)
        self.handleRects = {}
        self.handleSize = QPointF(10, 10)
        self.handleIndex = None
        self.state = 0

        self.id = "None"
        self.depend = "None" 
        self._self_ref = weakref.ref(self)  
        
        self.base_width = 2.0
        self.base_handle_size = 10.0
         
    def __del__(self):
        if self._self_ref() is None:  # 检查对象是否仍然存在
            return
        self.deleteLater()
    
    def setId(self,id):
        self.id = id
    
    def setDepend(self,depend):
        self.depend = depend

    def setPenColor(self,color:QColor):
        self.penColor = color
        
    def boundingRect(self):
        return GraphicsRectItem.shape(self).boundingRect()
    
    def shape(self):
        path = super().shape()
        self.handleRects["top-left"] = QRectF(self.rect().topLeft()- self.handleSize, self.rect().topLeft() + self.handleSize)
        self.handleRects["top-right"] = QRectF(self.rect().topRight() - self.handleSize, self.rect().topRight() + self.handleSize)
        self.handleRects["bottom-left"] = QRectF(self.rect().bottomLeft() - self.handleSize, self.rect().bottomLeft() + self.handleSize)
        self.handleRects["bottom-right"] = QRectF(self.rect().bottomRight() - self.handleSize, self.rect().bottomRight() + self.handleSize)
        for handleRect in self.handleRects.values():
            path.addRect(handleRect)
        return path
    
    def paint(self, painter, option, widget=None):
        painter.save()
        transform = painter.transform()
        scale_factor = max(abs(transform.m11()), abs(transform.m22()))
    
        # 设置基础线宽为2像素，根据缩放因子调整实际线宽
        base_width = self.base_width
        pen_width = base_width / scale_factor if scale_factor != 0 else base_width
        # 设置基础手柄大小为10像素，根据缩放因子调整实际手柄大小
        base_handle_size = self.base_handle_size
        handle_size = base_handle_size / scale_factor if scale_factor!= 0 else base_handle_size
        self.handleSize = QPointF(handle_size, handle_size)
    
        # 创建新画笔并应用设置
        pen = painter.pen()
        pen.setWidthF(pen_width)

        if self.isSelected():
            pen.setColor(self.handleColor)
            painter.setPen(pen)
            for item in self.handleRects.values():
                painter.drawRect(item)

        pen.setColor(self.penColor)
        pen.setStyle(self.lineStyle)
        self.setBrush(QBrush(self.brushColor))
        self.setPen(pen)

        # 取消选中状态
        option.state &= ~QStyle.State_Selected  # 使用 QStyle 的枚举值
        super().paint(painter, option, widget)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            match self.state:
                # 初始化创建状态
                case 0:
                    self.setRect(QRectF(self.mapFromScene(event.scenePos()),self.mapFromScene(event.scenePos())+QPointF(1,1)))
                    self.handleIndex = "bottom-right"
                    # 创建完成进入编辑状态
                    self.state = 1
                    return
                case 1:
                    self.itemSizeChanged.emit(self.rect())
                    self.setData(Qt.UserRole+1,True)
                    self.handleIndex = None
                    self.state = 2
                    return
                case 2:
                    if self.isSelected():
                        for handle, handleRect in self.handleRects.items():
                            if handleRect.contains(self.mapFromScene(event.scenePos())):
                                self.handleIndex = handle
                                return
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.handleIndex :
            r = self.rect()
            if self.handleIndex == "top-left":
                r.setTopLeft(self.mapFromScene(event.scenePos()))
            elif self.handleIndex == "top-right":
                r.setTopRight(self.mapFromScene(event.scenePos()))
            elif self.handleIndex == "bottom-left":
                r.setBottomLeft(self.mapFromScene(event.scenePos()))
            elif self.handleIndex == "bottom-right":
                r.setBottomRight(self.mapFromScene(event.scenePos()))
            self.setRect(r)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.state == 2:
            self.itemSizeChanged.emit(self.rect())
            self.handleIndex = None
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self.brushColor = QColor(self.penColor).darker()
        self.brushColor.setAlpha(200)
        return super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.brushColor = Qt.GlobalColor.transparent
        return super().hoverLeaveEvent(event)
    
    def hoverMoveEvent(self, event):
        # if self.isSelected():
        #     for handle,handleRect in self.handleRects.items():
        #         if handleRect.contains(self.mapFromScene(event.scenePos())):
        #             if handle == "top-left" or handle == "bottom-right":
        #                 if self.rect().top()<self.rect().bottom() and self.rect().left()<self.rect().right():
        #                     self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        #                 else:
        #                     self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        #             elif handle == "top-right" or handle == "bottom-left":
        #                 if self.rect().top()<self.rect().bottom() and self.rect().left()<self.rect().right():
        #                     self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        #                 else:
        #                     self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        #             return super().hoverMoveEvent(event)
        #     self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().hoverMoveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.itemPosChanged.emit(value)
        return super().itemChange(change, value)
