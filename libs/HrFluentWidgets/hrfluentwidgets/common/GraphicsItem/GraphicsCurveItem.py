from copy import deepcopy
from PySide6.QtCore import Qt,QPointF,Signal,QObject,QRectF
from PySide6.QtGui import QBrush,QColor,QPolygonF,QPen,QPainter, QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem,QStyle,QGraphicsItem,QGraphicsSceneMouseEvent,QStyleOptionGraphicsItem

import weakref

class CurveItemData:
    def __init__(self,id= "None",depend="None",polygon=QPolygonF(),pos=QPointF(), penColor=Qt.GlobalColor.green,type = "GraphicsCurveItem"):
        self.id = id
        self.depend = depend
        self.type = type
        self.polygon = polygon
        self.pos:QPointF = pos
        self.penColor:QColor = penColor

class GraphicsBezierCurveItem(QObject,QGraphicsPathItem):
    itemPosChanged = Signal(QPointF)
    itemSizeChanged = Signal(QPainterPath)

    def __init__(self,parent=None):
        QGraphicsPathItem.__init__(self,parent)
        QObject.__init__(self, None)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)
        self.setBrush(QBrush(QColor(255, 0, 0, 127)))

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
        self.control_items = QPolygonF()  # 控制点多边形
        
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
        
    def setPolygon(self, polygon:QPolygonF):
        """设置贝塞尔曲线的控制点多边形"""
        self.control_items = polygon
        self.updatePath()
        
    def polygon(self) -> QPolygonF:
        """获取贝塞尔曲线的控制点多边形"""
        return self.control_items
        
    def updatePath(self):
        """根据控制点更新贝塞尔曲线"""
        if len(self.control_items) == 2:
            path = QPainterPath()
            path.moveTo(self.control_items[0])
            path.lineTo(self.control_items[1])
            self.setPath(path)
        elif len(self.control_items) == 3:
            path = QPainterPath()
            path.moveTo(self.control_items[0])  # 起点
            path.quadTo(self.control_items[2], self.control_items[1])  # 二次贝塞尔曲线
            self.setPath(path)
        elif len(self.control_items) == 4:
            path = QPainterPath()
            path.moveTo(self.control_items[0])  # 起点
            path.cubicTo(self.control_items[2], 
                        self.control_items[3], 
                        self.control_items[1])  # 三次贝塞尔曲线
            self.setPath(path)
    
    def boundingRect(self):
        return self.shape().boundingRect()
    
    def shape(self):
        path = super().shape()
        for i,point in enumerate(self.control_items):
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
                    self.control_items.clear()
                    self.control_items.append(self.mapFromScene(event.scenePos()))  # 起点
                    self.control_items.append(self.mapFromScene(event.scenePos()+QPointF(1,1)))  # 终点
                    self.updatePath()
                    self.handleIndex = 1
                    self.state = 1
                    return
                case 1:
                    if self.handleIndex == 1:
                        self.control_items.append(self.mapFromScene(event.scenePos()))
                        self.handleIndex = 2
                        return
                    elif self.handleIndex == 2:
                        self.control_items.append(self.mapFromScene(event.scenePos()))
                        self.handleIndex = 3
                        return
                    else:
                        if self.handleRects[2].contains(self.mapFromScene(event.scenePos())):
                            self.control_items.removeLast()  # 删除最后一个控制点
                        self.updatePath()
                        self.itemSizeChanged.emit(self.path())
                        self.setData(Qt.UserRole+1,True)
                        self.handleIndex = None
                        self.state = 2
                        return
                case 2:
                    for handle, handleRect in self.handleRects.items():
                        if handleRect.contains(self.mapFromScene(event.scenePos())):
                            self.handleIndex = handle
                            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.handleIndex is not None :
            self.control_items[self.handleIndex] = self.mapFromScene(event.scenePos())
            self.updatePath()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.state == 2:
            self.itemSizeChanged.emit(self.path())
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