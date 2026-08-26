

from PySide6.QtCore import QLineF
from PySide6.QtWidgets import QGraphicsItem
from ...common.GraphicsItem import *
from abc import ABC, abstractmethod

class SupportBase(ABC):
    @abstractmethod
    def setData(self, item: QGraphicsItem, data):
        """Set data to the item."""
        pass
    
    @abstractmethod
    def getData(self, data, item: QGraphicsItem, targetItem: QGraphicsItem = None):
        """Get data from the item."""
        pass
    
    def genData(self, item: QGraphicsItem, targetItem: QGraphicsItem = None) -> object:
        """Get data from the item."""
        pass
    
    def connectSignals(self, item, itemChaged):
        """Connect signals to the item."""
        pass

class LineItemSupport(SupportBase):
    def setData(self, item: GraphicsLineItem, data: LineItemData):
        if data.id is not None:
            item.setId(data.id)
        if data.depend is not None:
            item.setDepend(data.depend)
        if data.penColor is not None:
            item.setPenColor(data.penColor)
        if data.line is not None:
            item.setLine(data.line)

    def getData(self, data: LineItemData, item: GraphicsLineItem, targetItem: QGraphicsItem = None):
        data.id = item.id
        data.depend = item.depend
        data.penColor = item.penColor
        if targetItem:
            p1 = targetItem.mapFromItem(item, item.line().p1())
            p2 = targetItem.mapFromItem(item, item.line().p2())
            data.line = QLineF(p1, p2)
        else:
            data.line = item.line()
        data.pos = item.line().p1()  # Assuming pos is the start point of the line
        
    def genData(self, item: GraphicsLineItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = LineItemData()
        self.getData(data, item, targetItem)
        return data
    
    def connectSignals(self, item: GraphicsLineItem, itemChaged):
        """Connect signals to the item."""
        item.itemPosChanged.connect(itemChaged)
        item.itemSizeChanged.connect(itemChaged)

class CurveItemSupport(SupportBase):
    def setData(self, item: GraphicsBezierCurveItem, data: CurveItemData):
        if data.id is not None:
            item.setId(data.id)
        if data.depend is not None:
            item.setDepend(data.depend)
        if data.penColor is not None:
            item.setPenColor(data.penColor)
        if data.polygon is not None:
            item.setPolygon(data.polygon)

    def getData(self, data: CurveItemData, item: GraphicsBezierCurveItem, targetItem: QGraphicsItem = None):
        data.id = item.id
        data.depend = item.depend
        data.penColor = item.penColor
        if targetItem:
            data.polygon = targetItem.mapFromItem(item, item.polygon())
        else:
            data.polygon = item.polygon()
        data.pos = item.control_items.boundingRect().center()  # Assuming pos is the center of the control points polygon
        
    def genData(self, item: GraphicsBezierCurveItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CurveItemData()
        self.getData(data, item, targetItem)
        return data
    
    def connectSignals(self, item: GraphicsBezierCurveItem, itemChaged):
        """Connect signals to the item."""
        item.itemPosChanged.connect(itemChaged)
        item.itemSizeChanged.connect(itemChaged)

class PolygonItemSupport(SupportBase):
    def setData(self, item:GraphicsPolygonItem, data: PolygonItemData):
        if data.id is not None:
            item.setId(data.id)
        if data.depend is not None:
            item.setDepend(data.depend)
        if data.penColor is not None:
            item.setPenColor(data.penColor)
        if data.is_closed is not None:
            item.setClosed(data.is_closed)
        if data.polygon is not None:
            item.setPolygon(data.polygon)

    def getData(self, data: PolygonItemData, item:GraphicsPolygonItem, targetItem:QGraphicsItem = None):
        data.id = item.id
        data.depend = item.depend
        data.penColor = item.penColor
        data.is_closed = item.is_closed
        data.polygon = targetItem.mapFromItem(item, item.polygon()) if targetItem else item.polygon()
        
    def genData(self, item: QGraphicsItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = PolygonItemData()
        self.getData(data, item, targetItem)
        return data
    
    def connectSignals(self, item:GraphicsPolygonItem, itemChaged):
        """Connect signals to the item."""
        item.itemPosChanged.connect(itemChaged)
        item.itemSizeChanged.connect(itemChaged)

class RectItemSupport(SupportBase):
    def setData(self, item:GraphicsRectItem, data: RectItemData):
        if data.id is not None:
            item.setId(data.id)
        if data.depend is not None:
            item.setDepend(data.depend)
        if data.penColor is not None:
            item.setPenColor(data.penColor)
        if data.rect is not None:
            item.setRect(data.rect)
      
    def getData(self, data: RectItemData, item:GraphicsRectItem, targetItem:QGraphicsItem = None):
        data.id = item.id
        data.depend = item.depend
        data.penColor = item.penColor
        data.rect = targetItem.mapRectFromItem(item, item.rect()) if targetItem else item.rect()
        
    def genData(self, item: GraphicsRectItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = RectItemData()
        self.getData(data, item, targetItem)
        return data
          
    def connectSignals(self, item:GraphicsRectItem, itemChaged):
        """Connect signals to the item."""
        item.itemPosChanged.connect(itemChaged)
        item.itemSizeChanged.connect(itemChaged)
        
class RotatedRectItemSupport(SupportBase):
    def setData(self, item:GraphicsRotatedRectItem, data: RotatedRectItemData):
        if data.id is not None:
            item.setId(data.id)
        if data.depend is not None:
            item.setDepend(data.depend)
        if data.penColor is not None:
            item.setPenColor(data.penColor)
        if data.rect is not None:   
            item.setRect(data.rect)
        if data.rotation is not None:
            item.setRotation(data.rotation)
            item.setTransformOriginPoint(data.rect.center())
            item.setPos(0, 0)

    def getData(self, data: RotatedRectItemData, item:GraphicsRotatedRectItem, targetItem:QGraphicsItem = None):
        data.id = item.id
        data.depend = item.depend
        data.penColor = item.penColor
        data.rect = item.rect().translated(item.pos())
        data.rotation = item.rotation()
        
    def genData(self, item: GraphicsRotatedRectItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = RotatedRectItemData()
        self.getData(data, item, targetItem)
        return data
        
    
    def connectSignals(self, item:GraphicsRotatedRectItem, itemChaged):
        """Connect signals to the item."""
        item.itemPosChanged.connect(itemChaged)
        item.itemSizeChanged.connect(itemChaged)
        item.itemRotatedChanged.connect(itemChaged)    
        
class CaliperLineItemSupport(LineItemSupport):
    def setData(self, item:GraphicsCaliperLineItem, data: CaliperLineItemData):
        if isinstance(data, CaliperLineItemData):
            LineItemSupport.setData(self, item, data)
        if data.caliperWidth is not None:
            item.setCaliperWidth(data.caliperWidth)
        if data.caliperHeight is not None:
            item.setCaliperHeight(data.caliperHeight)
        if data.caliperGap is not None:
            item.setCaliperGap(data.caliperGap)
        if data.caliperOffset1 is not None:
            item.setCaliperOffset1(data.caliperOffset1)
        if data.caliperOffset2 is not None:
            item.setCaliperOffset2(data.caliperOffset2)
        if getattr(data, 'penColor', None) is not None:
            item.setCaliperColor(data.penColor)
        if data.calipers is not None:
            item.calipers = data.calipers
            
    def getData(self, data: CaliperLineItemData, item:GraphicsCaliperLineItem, targetItem:QGraphicsItem = None):
        LineItemSupport.getData(self, data, item, targetItem)
        item.updateCalipers()
        data.caliperWidth = item.caliperWidth
        data.caliperHeight = item.caliperHeight
        data.caliperGap = item.caliperGap
        data.caliperOffset1 = item.caliperOffset1
        data.caliperOffset2 = item.caliperOffset2
        data.penColor = item.caliperColor
        data.calipers = item.calipers
        
    def genData(self, item: GraphicsCaliperLineItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CaliperLineItemData()
        self.getData(data, item, targetItem)
        return data
    
class CaliperCurveItemSupport(CurveItemSupport):
    def setData(self, item:GraphicsCaliperCurveItem, data: CaliperCurveItemData):
        if isinstance(data, CaliperCurveItemData):
            CurveItemSupport.setData(self, item, data)
        if data.caliperWidth is not None:
            item.setCaliperWidth(data.caliperWidth)
        if data.caliperHeight is not None:
            item.setCaliperHeight(data.caliperHeight)
        if data.caliperGap is not None:
            item.setCaliperGap(data.caliperGap)
        if data.caliperOffset1 is not None:
            item.setCaliperOffset1(data.caliperOffset1)
        if data.caliperOffset2 is not None:
            item.setCaliperOffset2(data.caliperOffset2)
        if getattr(data, 'penColor', None) is not None:
            item.setCaliperColor(data.penColor)
        if data.calipers is not None:
            item.calipers = data.calipers
            
    def getData(self, data: CaliperCurveItemData, item:GraphicsCaliperCurveItem, targetItem:QGraphicsItem = None):
        CurveItemSupport.getData(self, data, item, targetItem)
        item.updateCalipers()
        data.caliperWidth = item.caliperWidth
        data.caliperHeight = item.caliperHeight
        data.caliperGap = item.caliperGap
        data.caliperOffset1 = item.caliperOffset1
        data.caliperOffset2 = item.caliperOffset2
        data.penColor = item.caliperColor
        data.calipers = item.calipers
        
    def genData(self, item: GraphicsCaliperCurveItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CaliperCurveItemData()
        self.getData(data, item, targetItem)
        return data
        
class CaliperRectItemSupport(RectItemSupport):
    def setData(self, item:GraphicsCaliperRectItem, data: CaliperRectItemData):
        if isinstance(data, CaliperRectItemData):
            RectItemSupport.setData(self, item, data)
        if data.caliperWidth is not None:
            item.setCaliperWidth(data.caliperWidth)
        if data.caliperHeight is not None:
            item.setCaliperHeight(data.caliperHeight)
        if data.caliperGap is not None:
            item.setCaliperGap(data.caliperGap)
        if data.caliperOffset1 is not None:
            item.setCaliperOffset1(data.caliperOffset1)
        if data.caliperOffset2 is not None:
            item.setCaliperOffset2(data.caliperOffset2)
        if getattr(data, 'penColor', None) is not None:
            item.setCaliperColor(data.penColor)
        if data.calipers is not None:
            item.calipers = data.calipers
            
    def getData(self, data: CaliperRectItemData, item:GraphicsCaliperRectItem, targetItem:QGraphicsItem = None):
        RectItemSupport.getData(self, data, item, targetItem)
        item.updateCalipers()
        data.caliperWidth = item.caliperWidth
        data.caliperHeight = item.caliperHeight
        data.caliperGap = item.caliperGap
        data.caliperOffset1 = item.caliperOffset1
        data.caliperOffset2 = item.caliperOffset2
        data.penColor = item.caliperColor
        data.calipers = item.calipers
        
    def genData(self, item: GraphicsCaliperRectItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CaliperRectItemData()
        self.getData(data, item, targetItem)
        return data
        
class CaliperRotatedRectItemSupport(RotatedRectItemSupport):
    def setData(self, item:GraphicsCaliperRotatedRectItem, data: CaliperRotatedRectItemData):
        if isinstance(data, CaliperRotatedRectItemData):
            RotatedRectItemSupport.setData(self, item, data)
        if data.caliperWidth is not None:
            item.setCaliperWidth(data.caliperWidth)
        if data.caliperHeight is not None:
            item.setCaliperHeight(data.caliperHeight)
        if data.caliperGap is not None:
            item.setCaliperGap(data.caliperGap)
        if data.caliperOffset1 is not None:
            item.setCaliperOffset1(data.caliperOffset1)
        if data.caliperOffset2 is not None:
            item.setCaliperOffset2(data.caliperOffset2)
        if getattr(data, 'penColor', None) is not None:
            item.setCaliperColor(data.penColor)
        if data.calipers is not None:
            item.calipers = data.calipers
        
    def getData(self, data: CaliperRotatedRectItemData, item:GraphicsCaliperRotatedRectItem, targetItem:QGraphicsItem = None):
        RotatedRectItemSupport.getData(self, data, item, targetItem)
        item.updateCalipers()
        data.pos = item.rect().center()
        data.caliperWidth = item.caliperWidth
        data.caliperHeight = item.caliperHeight
        data.caliperGap = item.caliperGap
        data.caliperOffset1 = item.caliperOffset1
        data.caliperOffset2 = item.caliperOffset2
        data.penColor = item.caliperColor
        data.calipers = item.calipers
         
    def genData(self, item: GraphicsCaliperRotatedRectItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CaliperRotatedRectItemData()
        self.getData(data, item, targetItem)
        return data
    
class PolygonCaliperItemSupport(PolygonItemSupport):
    def setData(self, item:GraphicsCaliperPolygonItem, data: CaliperPolygonItemData):
        if isinstance(data, CaliperPolygonItemData):
            PolygonItemSupport.setData(self, item, data)
        if data.caliperWidth is not None:
            item.setCaliperWidth(data.caliperWidth)
        if data.caliperHeight is not None:
            item.setCaliperHeight(data.caliperHeight)
        if data.caliperGap is not None:
            item.setCaliperGap(data.caliperGap)
        if data.caliperOffset1 is not None:
            item.setCaliperOffset1(data.caliperOffset1)
        if data.caliperOffset2 is not None:
            item.setCaliperOffset2(data.caliperOffset2)
        if getattr(data, 'penColor', None) is not None:
            item.setCaliperColor(data.penColor)
        if data.calipers is not None:
            item.calipers = data.calipers
            
    def getData(self, data: CaliperPolygonItemData, item:GraphicsCaliperPolygonItem, targetItem:QGraphicsItem = None):
        PolygonItemSupport.getData(self, data, item, targetItem)
        item.updateCalipers()
        data.caliperWidth = item.caliperWidth
        data.caliperHeight = item.caliperHeight
        data.caliperGap = item.caliperGap
        data.caliperOffset1 = item.caliperOffset1
        data.caliperOffset2 = item.caliperOffset2
        data.penColor = item.caliperColor
        data.calipers = item.calipers
        if not item.polygon().empty():
            data.pos = item.polygon()[0]
        
    def genData(self, item: GraphicsCaliperPolygonItem, targetItem: QGraphicsItem = None):
        """Generate data from the item."""
        data = CaliperPolygonItemData()
        self.getData(data, item, targetItem)
        return data