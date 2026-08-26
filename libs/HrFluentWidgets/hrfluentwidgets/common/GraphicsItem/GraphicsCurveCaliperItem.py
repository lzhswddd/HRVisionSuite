from PySide6.QtCore import Qt,QPointF,QLineF
from PySide6.QtGui import QPolygonF, QTransform, QPainterPath
from .CaliperBase import CaliperBase, CaliperItemData
from .GraphicsCurveItem import GraphicsBezierCurveItem, CurveItemData
        
class CaliperCurveItemData(CurveItemData, CaliperItemData):
    def __init__(self, id= "None",depend="None",polygon=QPolygonF(),pos=QPointF(), penColor=Qt.GlobalColor.green,type = "GraphicsCurveItem",**kwargs):
        CurveItemData.__init__(self, id, depend, polygon, pos, penColor, type)
        CaliperItemData.__init__(self, **kwargs)
        
    def calipers_polygon(self):
        new_pos = self.polygon.boundingRect().center()
        p1 = self.pos
        transform = QTransform()
        transform.translate(new_pos.x() - p1.x(), new_pos.y() - p1.y())
        new_calipers = {}
        for key, caliper_list in self.calipers.items():
            new_calipers[key] = []
            for caliper in caliper_list:
                # 计算旋转后的四个顶点
                points = transform.map(QPolygonF(caliper))
                new_calipers[key].append(points)
        return new_calipers
        
          
class CaliperCurveBase(CaliperBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calipers["curve"] = []
        
    @staticmethod
    def getAngleAtPercent(path: QPainterPath, percent: float) -> float:
        """
        获取 QPainterPath 上某个百分比位置的角度
        :param path: QPainterPath 对象
        :param percent: 路径上的百分比位置 (0.0 到 1.0)
        :return: 角度 (以度为单位)
        """
        if percent < 0.0 or percent > 1.0:
            raise ValueError("Percent must be between 0.0 and 1.0")

        # 获取当前点和相邻点
        current_point = path.pointAtPercent(percent)
        next_point = path.pointAtPercent(min(percent + 0.01, 1.0))  # 防止超出路径范围

        # 使用 QLineF 计算角度
        line = QLineF(current_point, next_point)
        return line.angle()
        
    def updateCalipers(self, path: QPainterPath):
        self.calipers["curve"] = []
        
        if self.caliperWidth <= 0 or self.caliperHeight <= 0 or self.caliperGap <= 0:
            return
        
        length = path.length()
        
        num = int((length - self.caliperOffset1 - self.caliperOffset2 - self.caliperGap) / (self.caliperWidth + self.caliperGap))
        
        for i in range(num):
            # 计算每个卡尺的中心位置
            center_ratio = (self.caliperOffset1 + self.caliperGap + i * (self.caliperWidth + self.caliperGap) + self.caliperWidth / 2) / length
            center_point = path.pointAtPercent(center_ratio)

            # 创建卡尺的多边形
            caliper_polygon = QPolygonF([
                center_point + QPointF(-self.caliperWidth / 2, -self.caliperHeight / 2),
                center_point + QPointF(self.caliperWidth / 2, -self.caliperHeight / 2),
                center_point + QPointF(self.caliperWidth / 2, self.caliperHeight / 2),
                center_point + QPointF(-self.caliperWidth / 2, self.caliperHeight / 2),
                center_point + QPointF(-self.caliperWidth / 2, -self.caliperHeight / 2)
            ])
            # 获取直线的角度
            angle = CaliperCurveBase.getAngleAtPercent(path, center_ratio)

            # 创建旋转变换，使卡尺与直线垂直
            transform = QTransform()
            transform.translate(center_point.x(), center_point.y())
            transform.rotate(-angle)
            transform.translate(-center_point.x(), -center_point.y())

            # 应用旋转变换到卡尺多边形
            caliper_polygon = transform.map(caliper_polygon)

            # 将卡尺添加到字典中
            self.calipers["curve"].append(caliper_polygon)
     
class GraphicsCaliperCurveItem(GraphicsBezierCurveItem, CaliperCurveBase):
    def __init__(self,parent=None, **kwargs):
        GraphicsBezierCurveItem.__init__(self, parent)
        CaliperCurveBase.__init__(self, **kwargs)
        
    def updateCalipers(self):
        CaliperCurveBase.updateCalipers(self, self.path())
        
    def boundingRect(self):
        path = GraphicsBezierCurveItem.shape(self)
        for caliper_polygon in self.calipers["curve"]:
            path.addPolygon(caliper_polygon)
        return path
    
    def shape(self):
        return GraphicsBezierCurveItem.shape(self)
    
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