from PySide6.QtCore import Qt,Signal,QObject
from PySide6.QtWidgets import QHBoxLayout,QWidget,QVBoxLayout
from qfluentwidgets import CaptionLabel
from ...common import (
    ParamConfig, CaliperItemData,
    CaliperRectItemConfigItem, CaliperRotatedRectItemConfigItem
)
from .ParamItem import (
    SpinBoxItem, ParamItem
)

class GraphicsCaliperRectParam(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title, paramSetting, key, parent)
        
        self.paramLayout = QVBoxLayout(self)
        self.paramLayout.addWidget(CaptionLabel(title))
        self.initLayout()
        
        self.caliperRectWidth = SpinBoxItem("卡尺宽度:",self.paramSetting,key+".caliperRect-width")   
        self.caliperRectWidth.valueChanged.connect(self.onValueChanged)
        
        self.caliperRectHeight = SpinBoxItem("卡尺高度:",self.paramSetting,key+".caliperRect-height")
        self.caliperRectHeight.valueChanged.connect(self.onValueChanged)

        self.caliperRectGap = SpinBoxItem("卡尺间隔:",self.paramSetting,key+".caliperRect-gap")
        self.caliperRectGap.valueChanged.connect(self.onValueChanged)

        self.caliperRectOffset = SpinBoxItem("卡尺偏移:",self.paramSetting,key+".caliperRect-offset")

        self.addParamItem(self.caliperRectWidth)
        self.addParamItem(self.caliperRectHeight)
        self.addParamItem(self.caliperRectGap)
        self.addParamItem(self.caliperRectOffset)
        
        item = self.paramSetting.getItem(key)
        self.data = CaliperItemData(
            id=None,
            depend=None,
            rect=None,
            penColor=None,
            type=None,
            caliperWidth=self.paramSetting.get(key+".caliperRect-width"),
            caliperHeight=self.paramSetting.get(key+".caliperRect-height"),
            caliperGap=self.paramSetting.get(key+".caliperRect-gap"),
            caliperOffset1=self.paramSetting.get(key+".caliperRect-offset"),
            caliperOffset2=self.paramSetting.get(key+".caliperRect-offset")
            )
        
    def initLayout(self):
        self.paramLayout.setContentsMargins(0, 0, 0, 0)
        self.paramLayout.setSpacing(6)
    
    def triggerValueChanged(self):
        self.valueChanged.emit(self.key, self.data)
    
    def onValueChanged(self, key, value):
        if key == self.caliperRectWidth.key:
            self.data.caliperWidth = value
        elif key == self.caliperRectHeight.key:
            self.data.caliperHeight = value
        elif key == self.caliperRectGap.key:
            self.data.caliperGap = value
        elif key == self.caliperRectOffset.key:
            self.data.caliperOffset1 = value
            self.data.caliperOffset2 = value
        self.valueChanged.emit(self.key, self.data)
        
    def addParamItem(self,item:ParamItem):
        item.valueChanged.connect(self.onValueChanged)
        self.paramLayout.addWidget(item)

    def updateParam(self):
        for i in range(self.paramLayout.count()):
            widget = self.paramLayout.itemAt(i).widget()
            if isinstance(widget, ParamItem):
                widget.updateParam()
            
    