from PySide6.QtCore import Qt,QPointF,QLineF
from PySide6.QtGui import QPolygonF, QTransform
from .CaliperBase import CaliperBase, CaliperItemData
from .GraphicsLineItem import GraphicsLineItem, LineItemData
        
class CaliperLineItemData(LineItemData, CaliperItemData):
    def __init__(self, id= "None",depend="None",line=QLineF(), pos=QPointF(), penColor=Qt.GlobalColor.green,type = "GraphicsLineItem",**kwargs):
        LineItemData.__init__(self, id, depend, line, pos, penColor, type)
        CaliperItemData.__init__(self, **kwargs)
        
    def calipers_polygon(self):
        newpos = self.line.p1()
        p1 = self.pos
        transform = QTransform()
        transform.translate(newpos.x()-p1.x(), newpos.y()-p1.y())
        new_calipers = {}
        for key, caliper_list in self.calipers.items():
            new_calipers[key] = []
            for caliper in caliper_list:
                # 计算旋转后的四个顶点
                points = transform.map(QPolygonF(caliper))
                new_calipers[key].append(points)
        return new_calipers
        
          
class CaliperLineBase(CaliperBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calipers["line"] = []
        
    def updateCalipers(self, line: QLineF):
        self.calipers["line"] = []
        
        if self.caliperWidth <= 0 or self.caliperHeight <= 0 or self.caliperGap <= 0:
            return
        
        length = line.length()
        
        num = int((length - self.caliperOffset1 - self.caliperOffset2 - self.caliperGap) / (self.caliperWidth + self.caliperGap))
        
        for i in range(num):
            # 计算每个卡尺的中心位置
            center_ratio = (self.caliperOffset1 + self.caliperGap + i * (self.caliperWidth + self.caliperGap) + self.caliperWidth / 2) / length
            center_point = line.pointAt(center_ratio)

            # 创建卡尺的多边形
            caliper_polygon = QPolygonF([
                center_point + QPointF(-self.caliperWidth / 2, -self.caliperHeight / 2),
                center_point + QPointF(self.caliperWidth / 2, -self.caliperHeight / 2),
                center_point + QPointF(self.caliperWidth / 2, self.caliperHeight / 2),
                center_point + QPointF(-self.caliperWidth / 2, self.caliperHeight / 2),
                center_point + QPointF(-self.caliperWidth / 2, -self.caliperHeight / 2)
            ])
            # 获取直线的角度
            angle = line.angle()

            # 创建旋转变换，使卡尺与直线垂直
            transform = QTransform()
            transform.translate(center_point.x(), center_point.y())
            transform.rotate(-angle)
            transform.translate(-center_point.x(), -center_point.y())

            # 应用旋转变换到卡尺多边形
            caliper_polygon = transform.map(caliper_polygon)

            # 将卡尺添加到字典中
            self.calipers["line"].append(caliper_polygon)
     
class GraphicsCaliperLineItem(GraphicsLineItem, CaliperLineBase):
    def __init__(self,parent=None, **kwargs):
        GraphicsLineItem.__init__(self, parent)
        CaliperLineBase.__init__(self, **kwargs)
        
    def updateCalipers(self):
        line = super().line()
        CaliperLineBase.updateCalipers(self, line)
        
    def boundingRect(self):
        return self.shape().boundingRect()
    
    def shape(self):
        path = GraphicsLineItem.shape(self)
        center = self.line().center()
        angle = self.line().angle()
        width = self.line().length()
        height = self.caliperHeight
        # 计算旋转矩形的四个顶点
        rotated_rect_polygon = [
            QPointF(center.x() - width / 2, center.y() - height / 2),
            QPointF(center.x() + width / 2, center.y() - height / 2),
            QPointF(center.x() + width / 2, center.y() + height / 2),
            QPointF(center.x() - width / 2, center.y() + height / 2)
        ]
        # 创建旋转变换
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(-angle)
        transform.translate(-center.x(), -center.y())
        # 应用旋转变换到多边形
        rotated_rect_polygon = transform.map(QPolygonF(rotated_rect_polygon))
        path.addPolygon(rotated_rect_polygon)
        return path
    
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        if self.state != 2 and self.isSelected():
            return
        
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
        
        pen.setColor(self.caliperColor)
        pen.setStyle(self.lineStyle)
        painter.setPen(pen)
        self.setPen(pen)
        
        self.updateCalipers()
        
        for caliperlist in self.calipers.values():
            for caliper in caliperlist:
                painter.drawPolygon(caliper)
                
        painter.restore()