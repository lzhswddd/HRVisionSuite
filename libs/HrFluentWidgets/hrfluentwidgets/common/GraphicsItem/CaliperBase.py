from abc import abstractmethod
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class CaliperItemData:
    def __init__(self, **kwargs):
        self.caliperWidth = kwargs.get("caliperWidth", 0)
        self.caliperHeight = kwargs.get("caliperHeight", 0)
        self.caliperGap = kwargs.get("caliperGap", 0)
        self.caliperOffset1 = kwargs.get("caliperOffset1", 0)
        self.caliperOffset2 = kwargs.get("caliperOffset2", 0)
        self.caliperColor = kwargs.get("caliperColor", Qt.GlobalColor.red)
        self.calipers = kwargs.get("calipers",{})

class CaliperBase:
    def __init__(self, **kwargs):
        self.caliperWidth = kwargs.get("caliperWidth", 0)
        self.caliperHeight = kwargs.get("caliperHeight", 0)
        self.caliperGap = kwargs.get("caliperGap", 0)
        self.caliperOffset1 = kwargs.get("caliperOffset1", 0)
        self.caliperOffset2 = kwargs.get("caliperOffset2", 0)
        self.caliperColor = kwargs.get("caliperColor", Qt.GlobalColor.darkMagenta)
        
        self.calipers = {}
        
    def setCaliperWidth(self,width):
        self.caliperWidth = width
    
    def setCaliperHeight(self,height):
        self.caliperHeight = height
    
    def setCaliperGap(self,gap):
        self.caliperGap = gap
        
    def setCaliperOffset(self,offset):
        self.caliperOffset1 = offset
        self.caliperOffset2 = offset
        
    def setCaliperOffset1(self,offset):
        self.caliperOffset1 = offset
        
    def setCaliperOffset2(self,offset):
        self.caliperOffset2 = offset
        
    def setCaliperColor(self,color):
        self.caliperColor = QColor(color)
        
    @abstractmethod
    def updateCalipers(self, geo):
        """
        Update the calipers based on the geometry of the item.
        This method should be implemented in subclasses.
        """
        raise NotImplementedError("This method should be implemented in subclasses.")
        
    def getCalipers(self):
        return self.calipers
 