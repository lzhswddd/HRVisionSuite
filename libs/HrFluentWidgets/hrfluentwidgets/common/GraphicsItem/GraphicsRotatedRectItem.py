import math
import numpy as np
from .GraphicsRectItem import GraphicsRectItem, RectItemData
from PySide6.QtCore import Qt,QRectF,QPointF,Signal,QObject,QLineF
from PySide6.QtGui import QBrush,QColor,QPainterPath,QTransform,QPolygonF
from PySide6.QtWidgets import QGraphicsRectItem,QStyle,QGraphicsItem

class RotatedRectItemData(RectItemData):
    def __init__(self, id="None", depend="None", rect=QRectF(0, 0, 0, 0), rotation=0.0, penColor=Qt.GlobalColor.green, type="GraphicsRotatedRectItem"):
        super().__init__(id, depend, rect, penColor, type)
        self.rotation = rotation  # 添加旋转角度属性
        
    def polygon(self):
        center = self.rect.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.rotation)
        transform.translate(-center.x(), -center.y())
        return transform.map(QPolygonF(self.rect))
    
class GraphicsRotatedRectItem(GraphicsRectItem):
    itemRotatedChanged = Signal(float)
    def __init__(self, parent=None, **kwargs):
        """
        Initialize the GraphicsRotateRectItem with optional parameters.
        :param parent: The parent item.
        :type parent: GraphicsRectItem
        """
        super().__init__(parent)
        
    def boundingRect(self):
        return GraphicsRotatedRectItem.shape(self).boundingRect()
        
    def shape(self):
        path = QGraphicsRectItem.shape(self)
        self.handleRects["top"] = QRectF(self.rect().topLeft() + QPointF(self.rect().width()/2 - self.handleSize.x(), -self.handleSize.y()),
                                         self.rect().topLeft() + QPointF(self.rect().width()/2 + self.handleSize.x(), self.handleSize.y()))
        self.handleRects["left"] = QRectF(self.rect().topLeft() + QPointF(-self.handleSize.x(), self.rect().height()/2 - self.handleSize.y()),
                                            self.rect().topLeft() + QPointF(self.handleSize.x(), self.rect().height()/2 + self.handleSize.y()))
        self.handleRects["right"] = QRectF(self.rect().topRight() + QPointF(-self.handleSize.x(), self.rect().height()/2 - self.handleSize.y()),
                                            self.rect().topRight() + QPointF(self.handleSize.x(), self.rect().height()/2 + self.handleSize.y()))
        self.handleRects["bottom"] = QRectF(self.rect().bottomLeft() + QPointF(self.rect().width()/2 - self.handleSize.x(), -self.handleSize.y()),
                                            self.rect().bottomLeft() + QPointF(self.rect().width()/2 + self.handleSize.x(), self.handleSize.y()))
        self.handleRects["arrow"] = QRectF(
            (self.rect().topRight().x() + self.rect().bottomRight().x()) / 2 + self.handleSize.x(),
            (self.rect().topRight().y() + self.rect().bottomRight().y()) / 2 - self.handleSize.y(),
            self.handleSize.x() * 3,
            self.handleSize.y() * 2
        )
        for handleRect in self.handleRects.values():
            path.addRect(handleRect)
        return path
    
    def paint(self, painter, option, widget=None):
        painter.save()
        transform = painter.transform()
        
        # 计算缩放因子
        scale_x = math.sqrt(transform.m11()**2 + transform.m12()**2)  # x 轴缩放因子
        scale_y = math.sqrt(transform.m21()**2 + transform.m22()**2)  # y 轴缩放因子

        scale_factor = max(scale_x, scale_y)
        
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
            for key in self.handleRects.keys():
                if key != "arrow":
                    painter.drawRect(self.handleRects[key])

            # Draw arrow at the right center of the rectangle
            arrowPoint = self.handleRects["right"].center()
            arrow = QPainterPath()
            arrow.moveTo(arrowPoint-QPointF(handle_size, 0))
            arrow.lineTo(arrowPoint+QPointF(4 * handle_size, 0)+QPointF(-handle_size * 0.6, 0))
            arrow.lineTo(arrowPoint+QPointF(4 * handle_size, 0)+QPointF(-handle_size, handle_size * 0.6))
            arrow.lineTo(arrowPoint+QPointF(4 * handle_size, 0))
            arrow.lineTo(arrowPoint+QPointF(4 * handle_size, 0)+QPointF(-handle_size, -handle_size * 0.6))
            arrow.lineTo(arrowPoint+QPointF(4 * handle_size, 0)+QPointF(-handle_size * 0.6, 0))
            painter.drawPath(arrow)
            
        pen.setColor(self.penColor)
        pen.setStyle(self.lineStyle)
        self.setBrush(QBrush(self.brushColor))
        self.setPen(pen)

        # 取消选中状态
        option.state &= ~QStyle.State_Selected  # 使用 QStyle 的枚举值
        QGraphicsRectItem.paint(self, painter, option, widget)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            match self.state:
                # 初始化创建状态
                case 0:
                    self.setRect(QRectF(self.mapFromScene(event.scenePos()),self.mapFromScene(event.scenePos())+QPointF(1,1)))
                    self.handleIndex = "right-arrow"  # 设置为箭头状态
                    # 创建完成进入编辑状态
                    self.state = 1
                    return
                case 1:
                    if self.handleRects["right"].contains(self.mapFromScene(event.scenePos())):
                        self.handleIndex = "bottom"
                        return
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
            if self.handleIndex == "top":
                pos = self.mapFromScene(event.scenePos())
                diff = pos.y() - r.top()
                r.setTop(pos.y())
                r.setBottom(r.bottom() - diff)
            elif self.handleIndex == "left":
                pos = self.mapFromScene(event.scenePos())
                diff = pos.x() - r.left()
                r.setLeft(pos.x())
                r.setRight(r.right() - diff)
            elif self.handleIndex == "right":
                pos = self.mapFromScene(event.scenePos())
                diff = pos.x() - r.right()
                r.setLeft(r.left() - diff)
                r.setRight(pos.x())
            elif self.handleIndex == "bottom":
                pos = self.mapFromScene(event.scenePos())
                diff = pos.y() - r.bottom()
                r.setTop(r.top() - diff)
                r.setBottom(pos.y())
            elif self.handleIndex == "arrow":
                center = self.mapToScene(self.rect().center())
                pos = event.scenePos()
                radians = np.arctan2(pos.y() - center.y(), pos.x() - center.x())
                self.setRotation(np.rad2deg(radians))
                return
            elif self.handleIndex == "right-arrow":
                pos = self.mapFromScene(event.scenePos())
                diff = pos.x() - r.right()
                r.setLeft(r.left() - diff)
                r.setRight(pos.x())
                
                center = self.mapToScene(self.rect().center())
                pos = event.scenePos()
                radians = np.arctan2(pos.y() - center.y(), pos.x() - center.x())
                self.setRotation(np.rad2deg(radians))
                
            self.setTransformOriginPoint(r.center())
            self.setRect(r)
        else:
            super().mouseMoveEvent(event)
            
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.itemPosChanged.emit(value)
        if change == QGraphicsItem.GraphicsItemChange.ItemRotationChange:
            self.itemRotatedChanged.emit(value)
        return super().itemChange(change, value)