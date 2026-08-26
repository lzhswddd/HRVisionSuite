from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush,QPainter
from PySide6.QtWidgets import QGraphicsPathItem,QGraphicsItem,QStyleOptionGraphicsItem


class GraphicsCrossItem(QGraphicsPathItem):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        
        self.penColor = Qt.GlobalColor.green
        self.brushColor = Qt.GlobalColor.transparent
        self.lineStyle = Qt.PenStyle.SolidLine
        self.crossSize = 12
        self.base_width = 2.5

    def paint(self, painter:QPainter, option:QStyleOptionGraphicsItem, widget=None):
        painter.save()
        transform = painter.transform()
        scale_factor = max(abs(transform.m11()), abs(transform.m22()))

        # 设置基础线宽为2像素，根据缩放因子调整实际线宽
        base_width = self.base_width
        pen_width = base_width / scale_factor if scale_factor != 0 else base_width
        # 设置基础手柄大小为10像素，根据缩放因子调整实际手柄大小

        line_length = self.crossSize / scale_factor if scale_factor!= 0 else self.crossSize

        # 创建新画笔并应用设置
        pen = painter.pen()
        pen.setWidthF(pen_width)
        pen.setColor(self.penColor)
        pen.setStyle(self.lineStyle)
        painter.setPen(pen)
        painter.drawLine(-line_length, 0, line_length, 0)
        painter.drawLine(0, -line_length, 0, line_length)
        painter.restore()

        
