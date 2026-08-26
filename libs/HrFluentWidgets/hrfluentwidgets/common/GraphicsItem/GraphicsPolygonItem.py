from PySide6.QtCore import Qt,QPointF,Signal,QObject,QRectF
from PySide6.QtGui import QBrush,QColor,QPolygonF,QPen,QPainter
from PySide6.QtWidgets import QGraphicsPolygonItem,QStyle,QGraphicsItem,QGraphicsSceneMouseEvent,QStyleOptionGraphicsItem
import weakref

class PolygonItemData:
    def __init__(self,id= "None",depend="None",polygon=QPolygonF(),is_closed:bool=True,penColor=Qt.GlobalColor.green,type = "GraphicsPolygonItem"):
        self.id = id
        self.depend = depend
        self.type = type
        self.polygon:QPolygonF = polygon
        self.is_closed = is_closed  # 是否闭合多边形
        self.penColor:QColor = penColor

class GraphicsPolygonItem(QObject,QGraphicsPolygonItem):
    itemPosChanged = Signal(QPointF)
    itemSizeChanged = Signal(QPolygonF)

    def __init__(self,parent=None,**kwargs):
        QGraphicsPolygonItem.__init__(self,parent)
        QObject.__init__(self, None)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)
        self.setBrush(QBrush(QColor(255, 0, 0, 127)))
        self.setFillRule(Qt.FillRule.WindingFill)

        self.penColor = Qt.GlobalColor.green
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
        self.is_closed = kwargs.get('is_closed', True)  # 是否闭合多边形
        
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
        
    def setClosed(self, is_closed: bool):
        self.is_closed = is_closed
        
    def boundingRect(self):
        return self.shape().boundingRect()
    
    def shape(self):
        path = super().shape()
        for i,point in enumerate(self.polygon()):
            self.handleRects[i] = QRectF(point - self.handleSize, point + self.handleSize)
            path.addRect(self.handleRects[i])
        return path
    
    def paint(self, painter:QPainter, option:QStyleOptionGraphicsItem, widget=None):
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

    def mousePressEvent(self, event:QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            match self.state:
                # 初始化创建状态
                case 0:
                    self.setPolygon(QPolygonF([self.mapFromScene(event.scenePos()),self.mapFromScene(event.scenePos()+QPointF(1,1))]))
                    self.handleIndex = len(self.polygon())-1
                    self.state = 1
                    return
                case 1:
                    if self.handleRects[0].contains(self.mapFromScene(event.scenePos())):
                        pol = self.polygon()
                        pol.removeLast()
                        self.setPolygon(pol)
                        del self.handleRects[self.handleIndex]  # 删除最后一个手柄
                        self.itemSizeChanged.emit(self.polygon())
                        self.setData(Qt.UserRole+1,True)
                        self.handleIndex = None
                        self.state = 2
                        return
                    else:
                        pol = self.polygon()
                        pol.append(self.mapFromScene(event.scenePos()))
                        self.setPolygon(pol)
                        self.handleIndex = len(self.polygon())-1
                        return
                case 2:
                    for handle, handleRect in self.handleRects.items():
                        if handleRect.contains(self.mapFromScene(event.scenePos())):
                            self.handleIndex = handle
                            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.handleIndex is not None :
            pol = self.polygon()
            pol[self.handleIndex] = self.mapFromScene(event.scenePos())
            self.setPolygon(pol)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.state == 2:
            self.itemSizeChanged.emit(self.polygon())
            self.handleIndex = None
        super().mouseReleaseEvent(event)
    
    def hoverEnterEvent(self, event):
        self.brushColor = QColor(self.penColor).darker()
        self.brushColor.setAlpha(200)
        return super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.brushColor = Qt.GlobalColor.transparent
        return super().hoverLeaveEvent(event)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.itemPosChanged.emit(value)
        return super().itemChange(change, value)