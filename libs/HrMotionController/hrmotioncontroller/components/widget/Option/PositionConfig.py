
import hrfluentwidgets
import qfluentwidgets
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from ..Axis import AxisSettingConfig
from ..utils import HrTorchCompactDoubleSpinBox

class PositionValidator(qfluentwidgets.ConfigValidator):
    def __init__(self, axis_setting:AxisSettingConfig, group=[]):
        super().__init__()
        self.group = group
        self.info = axis_setting
        self.dims = 0
        for key in axis_setting.axis_name.value.values():
            if axis_setting.group.value.get(key, -1) in group:
                self.dims += 1
    
    def validate(self, value):
        if isinstance(value, dict) and len(value) == self.dims:
            for axis_name in self.info.axis_name.value.values():
                if self.info.group.value.get(axis_name, -1) not in self.group:
                    continue
                if not (self.info.min_position.value[axis_name] < value[axis_name] < self.info.max_position.value[axis_name]):
                    return False
            return True
        return False

    def correct(self, value):
        if self.validate(value):
            return value
        corrected = {}
        for axis_name in self.info.axis_name.value.values():
            if self.info.group.value.get(axis_name, -1) not in self.group:
                continue
            min_val = self.info.min_position.value[axis_name]
            max_val = self.info.max_position.value[axis_name]
            decimal = self.info.decimal.value[axis_name]
            if isinstance(value, dict):
                if min_val < value[axis_name] < max_val:
                    corrected_value = value[axis_name]
                else:
                    corrected_value = max(min_val, min(max_val, value[axis_name]))
            else:
                if min_val < 0 < max_val:
                    corrected_value = 0
                else:
                    corrected_value = min_val
            corrected[axis_name] = (round(corrected_value, decimal))
        return corrected
    
class PositionConfigItem(hrfluentwidgets.ParamItem):
    def __init__(self, title, paramSetting:hrfluentwidgets.ParamConfig, key:str, parent=None, **kwargs):
        super().__init__(title, paramSetting, key, parent)
        if not isinstance(self.configItem.validator, PositionValidator):
            raise ValueError("PositionConfigItem requires a PositionValidator")
    
        self.isTorch = kwargs.get("isTorch", False)
    
        hlayout = QHBoxLayout(self)
        position_label = qfluentwidgets.StrongBodyLabel(self.tr(self.title))
        hlayout.addWidget(position_label)
        for axis_name in self.configItem.validator.info.axis_name.value.values():
            axis_info = self.configItem.validator.info.getAxisInfo(axis_name)
            if axis_info.group in self.configItem.validator.group:
                if self.isTorch:
                    axis_value = HrTorchCompactDoubleSpinBox()
                else:
                    axis_value = hrfluentwidgets.HrCompactDoubleSpinBox()       
                axis_value.setPrefix(axis_info.title + ": ")
                axis_value.setRange(axis_info.min_position, axis_info.max_position)
                axis_value.setSingleStep(axis_info.single_step)
                axis_value.setDecimals(axis_info.decimal)
                axis_value.setSuffix(' ' + axis_info.distance_unit)
                axis_value.setValue(self.configItem.value[axis_name])
                # axis_value.setProperty("axis_name", axis_name)
                axis_value.setObjectName(axis_name)
                hlayout.addWidget(axis_value)
                
                axis_value.valueChanged.connect(self.__valueChanged)
            
        self.valueChanged.connect(self.updateParam)
            
    def updateSetting(self):
        for index in range(self.layout().count()):
            item = self.layout().itemAt(index).widget()
            if isinstance(item, qfluentwidgets.CompactDoubleSpinBox) or isinstance(item, HrTorchCompactDoubleSpinBox):
                axis_name = item.objectName()
                axis_info = self.configItem.validator.info.getAxisInfo(axis_name)
                item.setRange(axis_info.min_position, axis_info.max_position)
                item.setSingleStep(axis_info.single_step)
                item.setDecimals(axis_info.decimal)
                item.setSuffix(' ' + axis_info.distance_unit)
            
    def __valueChanged(self, value):
        sender = self.sender()
        if isinstance(sender, qfluentwidgets.CompactDoubleSpinBox) or isinstance(sender, HrTorchCompactDoubleSpinBox):
            axis_name = sender.objectName()
            current_values = self.configItem.value.copy()
            current_values[axis_name] = value
            self.paramSetting.set(self.key, current_values)
        else:
            print(f"Unexpected sender type: {type(sender)}")
    
    def updateParam(self, key, value):
        if key == self.key:
            for item_key in value.keys():
                if self.isTorch:
                    axis_value = self.findChild(HrTorchCompactDoubleSpinBox, item_key)
                else:
                    axis_value = self.findChild(qfluentwidgets.CompactDoubleSpinBox, item_key)
                if axis_value:
                    axis_value.blockSignals(True)
                    axis_value.setValue(value[item_key])
                    axis_value.blockSignals(False)
    
class PositionConfigWidget(qfluentwidgets.HeaderCardWidget):
    def __init__(self, axis_setting_config:AxisSettingConfig, param_config:hrfluentwidgets.ParamConfig=hrfluentwidgets.param_cfg, parent=None):
        super().__init__(parent)
        self.param_config = param_config
        self.axis_setting_config = axis_setting_config
        self.setTitle(self.tr("点位配置"))
        
        self.scrollarea = qfluentwidgets.ScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.positionWidget = QWidget()
        self.scrollarea.setStyleSheet("background-color:transparent; border:none;")

        self.positionLayout = QVBoxLayout(self.positionWidget)
        self.scrollarea.setWidget(self.positionWidget)
        
        self.initLayout()
 
        self.axis_setting_config.min_position.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.max_position.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.single_step.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.decimal.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.distance_unit.valueChanged.connect(self.updateSetting)
               
    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(5)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.addWidget(self.scrollarea)

        self.positionLayout.setContentsMargins(12, 12, 24, 12)
        self.positionLayout.setSpacing(5)
        self.positionLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.positionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
    def addPosition(self, name:str, key:str, **kwargs):
        config_item = PositionConfigItem(name, self.param_config, key, self, **kwargs)
        self.positionLayout.addWidget(config_item)
        self.positionLayout.addWidget(qfluentwidgets.components.widgets.card_widget.CardSeparator())
    
    def updateSetting(self, _):
        for index in range(self.positionLayout.count()):
            item = self.positionLayout.itemAt(index).widget()
            if isinstance(item, PositionConfigItem):
                item.updateSetting()
        
class PositionSelectWidget(qfluentwidgets.HeaderCardWidget):
    moveTo = Signal(dict)
    
    def __init__(self, group:str, key:str, 
                 axis_setting_config:AxisSettingConfig,
                 param_config:hrfluentwidgets.ParamConfig=hrfluentwidgets.param_cfg, 
                 parent=None):
        super().__init__(parent)
        self.param_config = param_config
        self.axis_setting_config = axis_setting_config
        self.setTitle(self.tr("点位选择"))
        
        self.positionLayout = QVBoxLayout()
        self.selectLayout = QHBoxLayout()
        self.editLayout = QVBoxLayout()
        self.optionLayout = QHBoxLayout()
        
        self.configItem = self.param_config.getItem(key)
        self.group = group
        
        if self.configItem:
            self.comboBox = qfluentwidgets.ComboBox()
            self.comboBox.setObjectName("position_select_combo")
            self.comboBox.addItems(self.configItem.validator.options)
            self.comboBox.currentTextChanged.connect(self.selectPosition)
            self.configItem.valueChanged.connect(self.updateComboBox)
        
        self.doubleSpinBoxList = {}
        
        self.applyBtn = qfluentwidgets.TransparentPushButton(self.tr("应用"))
        self.resetBtn = qfluentwidgets.TransparentPushButton(self.tr("重置"))
        self.moveBtn = qfluentwidgets.PrimaryPushButton(self.tr("移动"))
        
        self.axis_setting_config.min_position.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.max_position.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.single_step.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.decimal.valueChanged.connect(self.updateSetting)
        self.axis_setting_config.distance_unit.valueChanged.connect(self.updateSetting)
        
        self.moveBtn.clicked.connect(self.moveBtnClicked)
        self.resetBtn.clicked.connect(self.resetBtnClicked)
        self.applyBtn.clicked.connect(self.applyBtnClicked)
        
        self.initLayout()
 
    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(5)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.addLayout(self.positionLayout)
        
        self.positionLayout.setContentsMargins(12, 12, 24, 12)
        self.positionLayout.setSpacing(5)
        self.positionLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.positionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.selectLayout.setContentsMargins(0, 0, 0, 0)
        self.selectLayout.addWidget(self.comboBox)
        self.selectLayout.addStretch(1)
        self.selectLayout.addWidget(self.resetBtn,0,Qt.AlignmentFlag.AlignRight)
        
        self.editLayout.setContentsMargins(0, 0, 0, 0)
        self.editLayout.setSpacing(5)
        # self.editLayout.setDirection(QHBoxLayout.Direction.LeftToRight)
        self.editLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for spinBox in self.doubleSpinBoxList.values():
            self.editLayout.addWidget(spinBox)
        
        self.selectLayout.addStretch(1)
        self.optionLayout.addWidget(self.applyBtn)
        self.optionLayout.addWidget(self.moveBtn)
        
        self.positionLayout.addLayout(self.selectLayout)
        self.positionLayout.addLayout(self.editLayout)
        self.positionLayout.addLayout(self.optionLayout)
        
    def selectPosition(self, value:str):
        item = self.param_config.getItem(self.group + '.' + value)
        if item:
            value = item.value
            
            # 清除之前的SpinBox
            for _, widget in self.doubleSpinBoxList.items():
                self.editLayout.removeWidget(widget)
                widget.deleteLater()
            self.doubleSpinBoxList.clear()
            
            # self.doubleSpinBoxList.clear()
            for key in value.keys():
                axis_info = self.axis_setting_config.getAxisInfo(key)
                
                doubleSpinBox = hrfluentwidgets.HrCompactDoubleSpinBox()
                doubleSpinBox.setPrefix(axis_info.title + ": ")
                doubleSpinBox.setRange(axis_info.min_position, axis_info.max_position)
                doubleSpinBox.setSingleStep(axis_info.single_step)
                doubleSpinBox.setDecimals(axis_info.decimal)
                doubleSpinBox.setSuffix(' ' + axis_info.distance_unit)
                self.doubleSpinBoxList[key] = doubleSpinBox
                
                doubleSpinBox.blockSignals(True)
                doubleSpinBox.setValue(value[key])
                doubleSpinBox.blockSignals(False)
            
            for spinBox in self.doubleSpinBoxList.values():
                self.editLayout.addWidget(spinBox)
                
    def updateComboBox(self, value):
        if len(self.comboBox.items) != len(self.configItem.validator.options):
            self.comboBox.blockSignals(True)
            self.comboBox.clear()
            self.comboBox.addItems(self.configItem.validator.options)
            self.comboBox.setCurrentText(value)
            self.comboBox.blockSignals(False)
        
    def updateSetting(self, _):
        for axis_name in self.axis_setting_config.axis_name.value.values():
            axis_info = self.axis_setting_config.getAxisInfo(axis_name)
            doubleSpinBox = self.doubleSpinBoxList[axis_name]
            doubleSpinBox.setPrefix(axis_name + ": ")
            doubleSpinBox.setRange(axis_info.min_position, axis_info.max_position)
            doubleSpinBox.setSingleStep(axis_info.single_step)
            doubleSpinBox.setDecimals(axis_info.decimal)
            doubleSpinBox.setSuffix(' ' + axis_info.distance_unit)
            
    def moveBtnClicked(self):
        position = {axis_name: spinbox.value() for axis_name, spinbox in self.doubleSpinBoxList.items()}
        self.moveTo.emit(position)
        # print(f"Moving to position: {position}")

    def resetBtnClicked(self):
        value = self.comboBox.currentText()
        self.selectPosition(value)
        
    def applyBtnClicked(self):
        text = self.comboBox.currentText()
        item = self.param_config.getItem(self.group + '.' + text)
        if item:
            value = item.value.copy()
            for key in value.keys():
                spinbox = self.doubleSpinBoxList.get(key, None)
                if spinbox is not None: 
                    value[key] = spinbox.value()
            self.param_config.set(self.group + '.' + text, value)