
from PySide6.QtCore  import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout,QWidget,QVBoxLayout
from qfluentwidgets import (
    SwitchButton,
    CaptionLabel,
    ComboBox,
    ConfigItem
)
from ...common import (
    ParamConfig,
    RangeValueConfigItem,
)
from ...common.Widget.SpinBox import (
    HrCompactSpinBox,
    HrCompactDoubleSpinBox
)
from ...common.Widget.Slider import (
    RangeSlider, HrSlider 
)

class ParamItem(QWidget):
    valueChanged = Signal(str, object)
    
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(parent)
        self.title = title
        self.paramSetting = paramSetting
        self.configItem:ConfigItem = self.paramSetting.getItem(key)
        self.key = key
        
        if not self.configItem:
            raise ValueError(f"Config item with key '{key}' not found in ParamConfig.")
        self.configItem.valueChanged.connect(lambda x: self.valueChanged.emit(self.key,x))
        
    def triggerValueChanged(self):
        self.valueChanged.emit(self.key,self.configItem.value)
       
class SpinBoxItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)
        
        self.slider = HrSlider(Qt.Orientation.Horizontal,self)
        self.spinBox = HrCompactSpinBox(self)
 
        self.slider.setRange(self.configItem.range[0],self.configItem.range[1])
        self.spinBox.setRange(self.configItem.range[0],self.configItem.range[1])
        
        self.initLayout()
        self.initConnect()
        
        self.slider.setValue(self.configItem.value)

    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self.slider)
        hlayout.addWidget(self.spinBox)

        vLayout = QVBoxLayout()
        vLayout.setSpacing(6)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(CaptionLabel(self.title))
        vLayout.addLayout(hlayout)


        self.setLayout(vLayout)

    def initConnect(self):
        self.slider.valueChanged.connect(self.spinBox.setValue)
        self.spinBox.valueChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.spinBox.setValue(self.configItem.value)

    def __onValueChanged(self,value):
        if value!= self.slider.value():
            self.slider.setValue(value)
        self.paramSetting.set(self.key,value)

class DoubleSpinBoxItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)
        
        self.slider = HrSlider(Qt.Orientation.Horizontal,self)
        self.spinBox = HrCompactDoubleSpinBox(self)
        self.spinBox.setDecimals(2)
        # self.spinBox.setStepType(QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
        self.spinBox.setSingleStep(0.01)
 
        self.initLayout()
        self.initConnect()

        self.slider.setRange(self.configItem.range[0]*100,self.configItem.range[1]*100)
        self.slider.setValue(self.configItem.value*100)
        self.spinBox.setRange(self.configItem.range[0],self.configItem.range[1])
        
    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self.slider)
        hlayout.addWidget(self.spinBox)

        vLayout = QVBoxLayout()
        vLayout.setSpacing(6)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(CaptionLabel(self.title))
        vLayout.addLayout(hlayout)

        self.setLayout(vLayout)

    def initConnect(self):
        self.slider.valueChanged.connect(lambda x: self.spinBox.setValue(round(x/100.0,2)))
        self.spinBox.valueChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.spinBox.setValue(self.configItem.value)

    def __onValueChanged(self,value):
        if value != round(self.slider.value()/100.0,2):
            self.slider.setValue(round(value*100.0,2))
        self.paramSetting.set(self.key,round(value,2))

class RangeSpinBoxItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)

        self.rangeSlider = RangeSlider(Qt.Orientation.Horizontal,self)
        self.minSpinBox = HrCompactSpinBox(self)
        self.maxSpinBox = HrCompactSpinBox(self)


        range = self.configItem.range
        start = self.configItem.start
        end = self.configItem.end

        self.rangeSlider.setRange(range[0],range[1])
        self.minSpinBox.setRange(range[0],range[1])
        self.maxSpinBox.setRange(range[0],range[1])

        # self.minSpinBox.setValue(start)
        # self.maxSpinBox.setValue(end)

        self.initLayout()
        self.initConnect()

        self.rangeSlider.setRangeStart(start)
        self.rangeSlider.setRangeEnd(end)

    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self.minSpinBox)
        hlayout.addWidget(self.rangeSlider)
        hlayout.addWidget(self.maxSpinBox)

        vLayout = QVBoxLayout()
        vLayout.setSpacing(6)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(CaptionLabel(self.title))
        vLayout.addLayout(hlayout)

        self.setLayout(vLayout)

    def initConnect(self):
        self.rangeSlider.rangeStartChanged.connect(self.minSpinBox.setValue)
        self.rangeSlider.rangeEndChanged.connect(self.maxSpinBox.setValue)
        self.minSpinBox.valueChanged.connect(self.__onValueChanged)
        self.maxSpinBox.valueChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.minSpinBox.setValue(self.configItem.start)
        self.maxSpinBox.setValue(self.configItem.end)
    
    def __onValueChanged(self):
        if self.minSpinBox.value()!= self.rangeSlider.rangeStart():
            self.rangeSlider.setRangeStart(self.minSpinBox.value())
        if self.maxSpinBox.value()!= self.rangeSlider.rangeEnd():
            self.rangeSlider.setRangeEnd(self.maxSpinBox.value())
        self.paramSetting.set(self.key,(self.rangeSlider.rangeStart(),self.rangeSlider.rangeEnd()))

class RangeDoubleSpinBoxItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)

        self.rangeSlider = RangeSlider(Qt.Orientation.Horizontal,self)
        self.minSpinBox = HrCompactDoubleSpinBox(self)
        self.maxSpinBox = HrCompactDoubleSpinBox(self)
        self.minSpinBox.setDecimals(2)
        self.maxSpinBox.setDecimals(2)
        self.minSpinBox.setSingleStep(0.01)
        self.maxSpinBox.setSingleStep(0.01)


        range = self.configItem.range
        start = self.configItem.start
        end = self.configItem.end

        self.rangeSlider.setRange(range[0]*100,range[1]*100)
        self.minSpinBox.setRange(range[0],range[1])
        self.maxSpinBox.setRange(range[0],range[1])

        # self.minSpinBox.setValue(start)
        # self.maxSpinBox.setValue(end)

        self.initLayout()
        self.initConnect()

        self.rangeSlider.setRangeStart(start*100)
        self.rangeSlider.setRangeEnd(end*100)


    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self.minSpinBox)
        hlayout.addWidget(self.rangeSlider)
        hlayout.addWidget(self.maxSpinBox)

        vLayout = QVBoxLayout()
        vLayout.setSpacing(6)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(CaptionLabel(self.title))
        vLayout.addLayout(hlayout)

        self.setLayout(vLayout)

    def initConnect(self):
        self.rangeSlider.rangeStartChanged.connect(lambda x: self.minSpinBox.setValue(round(x/100.0,2)))
        self.rangeSlider.rangeEndChanged.connect(lambda x: self.maxSpinBox.setValue(round(x/100.0,2)))
        self.minSpinBox.valueChanged.connect(self.__onValueChanged)
        self.maxSpinBox.valueChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.minSpinBox.setValue(self.configItem.start)
        self.maxSpinBox.setValue(self.configItem.end)
    
    def __onValueChanged(self):
        if self.minSpinBox.value()!= round(self.rangeSlider.rangeStart()/100.0,2):
            self.rangeSlider.setRangeStart(round(self.minSpinBox.value()*100,2))
        if self.maxSpinBox.value()!= round(self.rangeSlider.rangeEnd()/100.0,2):
            self.rangeSlider.setRangeEnd(round(self.maxSpinBox.value()*100,2))

        self.paramSetting.set(self.key,(self.minSpinBox.value(),self.maxSpinBox.value()))

class SwitchItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)
        
        self.switch = SwitchButton(self)

        self.switch.setChecked(self.configItem.value)
 
        self.initLayout()
        self.initConnect()

    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(CaptionLabel(self.title))
        hlayout.addWidget(self.switch,0,Qt.AlignmentFlag.AlignRight)

        self.setLayout(hlayout)

    def initConnect(self):
        self.switch.checkedChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.switch.setChecked(self.configItem.value)

    def __onValueChanged(self,value):
            self.paramSetting.set(self.key,value)

class ComboxItem(ParamItem):
    def __init__(self,title,paramSetting:ParamConfig,key:str,parent=None):
        super().__init__(title,paramSetting,key,parent)
        
        self.combox = ComboBox(self)
        self.combox.setMinimumWidth(200)
        self.combox.addItems(self.configItem.options)
        self.combox.setCurrentText(self.configItem.value)

        self.initLayout()
        self.initConnect()

    def initLayout(self):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(6)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(CaptionLabel(self.title))
        hlayout.addWidget(self.combox,0,Qt.AlignmentFlag.AlignRight)

        self.setLayout(hlayout)

    def initConnect(self):
        self.combox.currentTextChanged.connect(self.__onValueChanged)

    def updateParam(self):
        self.combox.setCurrentText(self.configItem.value)

    def __onValueChanged(self,value):
            self.paramSetting.set(self.key,value)

