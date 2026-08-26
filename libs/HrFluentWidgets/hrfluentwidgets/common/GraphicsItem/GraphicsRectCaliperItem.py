import math
from PySide6.QtCore import Qt,QRectF,QPointF,Signal,QObject
from PySide6.QtGui import QBrush,QColor,QPainterPath,QPolygonF,QTransform
from PySide6.QtWidgets import QGraphicsRectItem,QStyle,QGraphicsItem
import numpy as np
from .GraphicsRectItem import GraphicsRectItem, RectItemData
from .GraphicsRotatedRectItem import RotatedRectItemData, GraphicsRotatedRectItem
from .CaliperBase import CaliperBase, CaliperItemData
        
class CaliperRectItemData(RectItemData, CaliperItemData):
    def __init__(self, id="None",depend="None",rect=QRectF(0,0,0,0),penColor=Qt.GlobalColor.green,type = "GraphicsCaliperRectItem",**kwargs):
        """
        Initialize the CaliperRectItem with optional parameters.\n
        :param id: The ID of the item.
        :param depend: The dependency of the item.
        :param rect: The rectangle of the item.
        :param penColor: The pen color of the item.
        :param type: The type of the item.
        :param kwargs: Optional parameters for the caliper item.\n
            - caliperWidth: The width of the calipers.
            - caliperHeight: The height of the calipers.
            - caliperGap: The gap between the calipers.
            - caliperColor: The color of the calipers.
            - calipers: A dictionary to store caliper items.
        """
        RectItemData.__init__(self,id,depend,rect,penColor,type)
        CaliperItemData.__init__(self, **kwargs)
          
class CaliperRotatedRectItemData(CaliperRectItemData):
    def __init__(self, id="None",depend="None",rect=QRectF(0,0,0,0),rotation=0.0, pos=QPointF(0,0),penColor=Qt.GlobalColor.green,type = "GraphicsCaliperRotatedRectItem",**kwargs):
        super().__init__(id,depend,rect,penColor,type, **kwargs)
        self.rotation = rotation  # 添加旋转角度属性
        self.pos = pos

    def calipers_polygon(self)->dict:
        center = self.rect.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.rotation)
        transform.translate(-self.pos.x(), -self.pos.y())
        new_calipers = {}
        for key, caliper_list in self.calipers.items():
            new_calipers[key] = []
            for caliper in caliper_list:
                # 计算旋转后的四个顶点
                points = transform.map(QPolygonF(caliper))
                new_calipers[key].append(points)
        return new_calipers
            
    def polygon(self)->QPolygonF:
        center = self.rect.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(self.rotation)
        transform.translate(-center.x(), -center.y())
        return transform.map(QPolygonF(self.rect))
    
class CaliperRectBase(CaliperBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calipers["top"] = []
        self.calipers["bottom"] = []
        self.calipers["left"] = []
        self.calipers["right"] = []
        
    def updateCalipers(self, rect: QRectF):
        self.calipers["top"] = []
        self.calipers["bottom"] = []
        self.calipers["left"] = []
        self.calipers["right"] = []
        
        if self.caliperWidth <= 0 or self.caliperHeight <= 0 or self.caliperGap <= 0:
            return
        
        width = abs(rect.width())
        height = abs(rect.height())
        
        v_num = int((width - self.caliperOffset1 - self.caliperOffset2) / (self.caliperWidth + self.caliperGap))
        h_num = int((height - self.caliperOffset1 - self.caliperOffset2) / (self.caliperWidth + self.caliperGap))
        
        for i in range(v_num):
            # 计算中心点坐标
            x = rect.left() + (i + 0.5) * (self.caliperWidth + self.caliperGap) + self.caliperOffset1
            
            self.calipers["top"].append(QRectF(
                x, 
                rect.top() - self.caliperHeight / 2, 
                self.caliperWidth, 
                self.caliperHeight))
            self.calipers["bottom"].append(QRectF(
                x,
                rect.bottom() - self.caliperHeight / 2, 
                self.caliperWidth, 
                self.caliperHeight))
            
        for i in range(h_num):
            # 计算中心点坐标（兼容负值rect）
            y = rect.top() + (i + 0.5) * (self.caliperWidth + self.caliperGap) + self.caliperOffset1
            
            self.calipers["left"].append(QRectF(
                rect.left() - self.caliperHeight / 2, 
                y, 
                self.caliperHeight, 
                self.caliperWidth))
            self.calipers["right"].append(QRectF(
                rect.right() - self.caliperHeight / 2, 
                y, 
                self.caliperHeight, 
                self.caliperWidth))
     
class GraphicsCaliperRectItem(GraphicsRectItem, CaliperRectBase):
    def __init__(self,parent=None, **kwargs):
        """
        Initialize the GraphicsRectCaliperItem with optional parameters.\n
        :param parent: The parent item.
        :param kwargs: Optional parameters for the caliper item.\n
            - caliperWidth: The width of the calipers.
            - caliperHeight: The height of the calipers.
            - caliperGap: The gap between the calipers.
        :type parent: GraphicsRectItem
        """        
        GraphicsRectItem.__init__(self, parent)
        CaliperRectBase.__init__(self, **kwargs)
        
    def updateCalipers(self):
        rect = super().boundingRect().adjusted(
            self.handleSize.x(),
            self.handleSize.y(), 
            -self.handleSize.x(), 
            -self.handleSize.y())
        CaliperRectBase.updateCalipers(self, rect)
        
    def boundingRect(self):
        return GraphicsCaliperRectItem.shape(self).boundingRect()
    
    def shape(self):
        path = super().shape()
        for caliperlist in self.calipers.values():
            for caliper in caliperlist:
                path.addRect(caliper)
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
        self.setBrush(QBrush(self.brushColor))
        self.setPen(pen)
        
        self.updateCalipers()
        
        for caliperlist in self.calipers.values():
            for caliper in caliperlist:
                painter.drawRect(caliper)
                
        painter.restore()
        
class GraphicsCaliperRotatedRectItem(GraphicsRotatedRectItem, CaliperRectBase):
    """
    GraphicsCaliperRotatedRectItem is a graphics item that represents a rotated rectangle with calipers.
    It inherits from GraphicsCaliperRectItem and adds functionality for handling rotated rectangles.
    """
    
    def __init__(self,parent=None, **kwargs):
        """
        Initialize the GraphicsRectCaliperItem with optional parameters.\n
        :param parent: The parent item.
        :param kwargs: Optional parameters for the caliper item.\n
            - caliperWidth: The width of the calipers.
            - caliperHeight: The height of the calipers.
            - caliperGap: The gap between the calipers.
        :type parent: GraphicsRectItem
        """        
        GraphicsRotatedRectItem.__init__(self, parent)
        CaliperRectBase.__init__(self, **kwargs)
        
    def updateCalipers(self):
        rect = super().boundingRect().adjusted(
            self.handleSize.x(),
            self.handleSize.y(), 
            -4*self.handleSize.x(), 
            -self.handleSize.y())
        CaliperRectBase.updateCalipers(self, rect)
       
    def boundingRect(self):
        return GraphicsCaliperRotatedRectItem.shape(self).boundingRect()
    
    def shape(self):
        path = super().shape()
        for caliperlist in self.calipers.values():
            for caliper in caliperlist:
                path.addRect(caliper)
        return path
    
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        if self.state != 2 and self.isSelected():
            return
        
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
        
        pen.setColor(self.caliperColor)
        pen.setStyle(self.lineStyle)
        painter.setPen(pen)
        self.setBrush(QBrush(self.brushColor))
        self.setPen(pen)
        
        self.updateCalipers()
        for caliperlist in self.calipers.values():
            for caliper in caliperlist:
                painter.drawRect(caliper)
                
        painter.restore()