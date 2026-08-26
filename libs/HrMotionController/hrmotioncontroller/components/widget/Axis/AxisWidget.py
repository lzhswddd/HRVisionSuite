from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMenu, QDialog, QDialogButtonBox
from PySide6.QtGui import QPainter, QPolygon, QPixmap, QTransform, QMouseEvent, QColor, QPen, QAction
from PySide6.QtCore import Qt, QPoint, QObject, Signal, QTimerEvent
import qfluentwidgets
from hrfluentwidgets import ProgressPushButton, ParamConfig, HrCompactDoubleSpinBox
from ..utils import HrTorchCompactDoubleSpinBox
from ....common import AxisBase

if __name__ == "__main__":
    from _rc import resource
else:
    from ._rc import resource
import math
from enum import Enum

class BtnDire(Enum):
    CENTER      = 9
    LOAD        = 8
    UP          = 5
    DOWN        = 1
    LEFT        = 3
    RIGHT       = 7
    UP_LEFT     = 4
    UP_RIGHT    = 6
    DOWN_LEFT   = 2
    DOWN_RIGHT  = 0

class BtnDirection(QWidget):
    onBtnPress = Signal(BtnDire)
    onBtnRelease = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.polygons = [QPolygon() for _ in range(10)]
        self.polygonsPressed = dict()
        self.polygonsHovered = dict()
        self.iconSize = 0
        self.spacing = 0
        self.colorBackground = QColor("#fdfdfd")
        self.colorHovered = QColor("#fefefe")
        self.colorPressed = QColor("#f5f5f5")
        self.colorNormal = QColor("#fafafa")
        self.colorBorder = QColor("#bababa")
        self.colorText = QColor("#000000")
        self.image = QPixmap()
        
        self.initWidget()

    def initWidget(self):
        self.setMouseTracking(True)
        self.resize(600, 600)
        self.setMinimumSize(200, 200)
        self.changeTheme(qfluentwidgets.theme())
        qfluentwidgets.qconfig.themeChanged.connect(self.changeTheme)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)

        center = QPoint(self.width() // 2, self.height() // 2)
        radiusOuter = min(self.width(), self.height()) // 2
        radiusInner = int(radiusOuter * 0.5)
        self.spacing = radiusOuter - radiusInner
        self.iconSize = self.spacing - self.spacing // 4

        octagonPoints = [
            QPoint(center.x() + radiusOuter * math.cos((i + 0.5) * math.pi / 4),
                   center.y() + radiusOuter * math.sin((i + 0.5) * math.pi / 4))
            for i in range(8)
        ]

        innerOctagonPoints = [
            QPoint(center.x() + radiusInner * math.cos((i + 0.5) * math.pi / 4),
                   center.y() + radiusInner * math.sin((i + 0.5) * math.pi / 4))
            for i in range(8)
        ]

        horLeftPoint = QPoint((innerOctagonPoints[0].x() + innerOctagonPoints[7].x()) // 2,
                              (innerOctagonPoints[0].y() + innerOctagonPoints[7].y()) // 2)
        horRightPoint = QPoint((innerOctagonPoints[3].x() + innerOctagonPoints[4].x()) // 2,
                               (innerOctagonPoints[3].y() + innerOctagonPoints[4].y()) // 2)

        painter.setPen(QPen(self.colorBorder, 1.5))

        for i in range(len(self.polygons)):
            self.polygons[i].clear()
            if i < 8:
                self.polygons[i] << octagonPoints[i] << octagonPoints[(i + 1) % 8] \
                                 << innerOctagonPoints[(i + 1) % 8] << innerOctagonPoints[i]
            elif i == 8:
                self.polygons[i] << horLeftPoint << innerOctagonPoints[0] << innerOctagonPoints[1] \
                                 << innerOctagonPoints[2] << innerOctagonPoints[3] << horRightPoint
            elif i == 9:
                self.polygons[i] << horRightPoint << innerOctagonPoints[4] << innerOctagonPoints[5] \
                                 << innerOctagonPoints[6] << innerOctagonPoints[7] << horLeftPoint

            if i in self.polygonsPressed:
                painter.setBrush(self.colorPressed)
            else:
                painter.setBrush(self.colorHovered if i in self.polygonsHovered else self.colorNormal)
            painter.drawPolygon(self.polygons[i])

        painter.setPen(QPen(self.colorText))
        topRect = painter.fontMetrics().boundingRect("Center")
        centerTop = QPoint(center.x(), center.y() - self.spacing // 2)
        topRect.moveCenter(centerTop)
        painter.drawText(topRect, Qt.AlignmentFlag.AlignCenter, "Center")

        bottomRect = painter.fontMetrics().boundingRect("Load")
        centerBottom = QPoint(center.x(), center.y() + self.spacing // 2.5)
        bottomRect.moveCenter(centerBottom)
        painter.drawText(bottomRect, Qt.AlignmentFlag.AlignCenter, "Load")

        for i in range(8):
            self.drawIcon(painter, innerOctagonPoints[i], innerOctagonPoints[(i + 1) % 8])

    def resizeEvent(self, event):
        self.update()

    def mousePressEvent(self, event:QMouseEvent):
        for i, polygon in enumerate(self.polygons):
            if polygon.containsPoint(event.position().toPoint(), Qt.FillRule.OddEvenFill):
                self.polygonsPressed[i] = polygon
                self.onBtnPress.emit(BtnDire(i))
                break
        self.update()

    def mouseReleaseEvent(self, event:QMouseEvent):
        self.polygonsPressed.clear()
        self.onBtnRelease.emit()
        self.update()

    def mouseMoveEvent(self, event:QMouseEvent):
        if self.polygonsPressed:
            return

        self.polygonsHovered.clear()
        for polygon in self.polygons:
            if polygon.containsPoint(event.position().toPoint(), Qt.FillRule.OddEvenFill):
                self.polygonsHovered[self.polygons.index(polygon)] = polygon
        self.update()

    def drawIcon(self, painter:QPainter, start, end):
        midPoint = (start + end) / 2
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        midLineLength = self.iconSize // 2
        midLineStart = QPoint(midPoint.x() - dy * midLineLength / math.sqrt(dx * dx + dy * dy),
                              midPoint.y() + dx * midLineLength / math.sqrt(dx * dx + dy * dy))
        midLineEnd = QPoint(midPoint.x() + dy * midLineLength / math.sqrt(dx * dx + dy * dy),
                            midPoint.y() - dx * midLineLength / math.sqrt(dx * dx + dy * dy))
        rotatedPixmap = self.image.transformed(QTransform().rotate(self.calculateAngle(start, end)))
        imageCenter = midLineEnd
        imageCenter.setX(imageCenter.x() - self.iconSize // 2)
        imageCenter.setY(imageCenter.y() - self.iconSize // 2)
        painter.drawPixmap(imageCenter,
                           rotatedPixmap.scaled(self.iconSize, self.iconSize, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def calculateAngle(self, start, end):
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        return math.atan2(dy, dx) * 180 / math.pi
    
    def changeTheme(self, theme):
        if theme == qfluentwidgets.Theme.LIGHT:
            self.colorBackground = QColor("#fdfdfd")
            self.colorHovered = QColor("#fefefe")
            self.colorPressed = QColor("#f5f5f5")
            self.colorNormal = QColor("#fafafa")
            self.colorBorder = QColor("#bababa")
            self.colorText = QColor("#000000")
            self.image.load(":/resource/icons/triangle_dark.svg")
        elif theme == qfluentwidgets.Theme.DARK:
            self.colorBackground = QColor("#2c2c2c")
            self.colorHovered = QColor("#3c3c3c")
            self.colorPressed = QColor("#4c4c4c")
            self.colorNormal = QColor("#3a3a3a")
            self.colorBorder = QColor("#444444")
            self.colorText = QColor("#ffffff")
            self.image.load(":/resource/icons/triangle_light.svg")
        self.update()

class AxisInfo:
    def __init__(self, **kwargs):
        self.title = kwargs.get('title', 'Axis')
        self.name = kwargs.get('name', 'Axis')
        self.pulse_equivalent = kwargs.get('pulse_equivalent', 1.0)
        self.max_velocity = kwargs.get('max_velocity', 1000.0)
        self.acceleration = kwargs.get('acceleration', 1000.0)
        self.deceleration = kwargs.get('deceleration', 1000.0)
        self.sramp = kwargs.get('sramp', 0.0)
        self.min_position = kwargs.get('min_position', -1000.0)
        self.max_position = kwargs.get('max_position', 1000.0)
        self.decimal = kwargs.get('decimal', 2)
        self.single_step = kwargs.get('single_step', 0.1)
        self.distance_unit = kwargs.get('distance_unit', 'mm')
        self.group = kwargs.get('group', False)

class AxisSettingConfig(ParamConfig):
    def __init__(self):
        super().__init__()
        self.file = Path("config/axis_setting.json")
        
        self.axis_name = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Axis Name'), {})
        self.title = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Title'), {})
        self.pulse_equivalent = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Pulse Equivalent'), {})
        self.home_speed = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Home Speed'), {})
        self.home_creep = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Home Creep'), {})
        self.max_velocity = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Max Velocity'), {})
        self.acceleration = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Acceleration'), {})
        self.deceleration = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Deceleration'), {})
        self.sramp = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('S-Ramp'), {})
        self.min_position = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Min Position'), {})
        self.max_position = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Max Position'), {})
        self.decimal = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Decimal Places'), {})
        self.single_step = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Single Step'), {})
        self.distance_unit = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Distance Unit'), {})
        self.group = qfluentwidgets.ConfigItem(QObject.tr('Axis'), QObject.tr('Group'), {})
        
        self.addParam(self.axis_name)
        self.addParam(self.title)
        self.addParam(self.pulse_equivalent)
        self.addParam(self.max_velocity)
        self.addParam(self.acceleration)
        self.addParam(self.deceleration)
        self.addParam(self.sramp)
        self.addParam(self.min_position)
        self.addParam(self.max_position)
        self.addParam(self.decimal)
        self.addParam(self.single_step)
        self.addParam(self.distance_unit)
        self.addParam(self.group)
     
    def getAxisID(self, name:str) -> int:
        """ 获取指定轴的ID """
        if name not in self.axis_name.value.values():
            return -1
        # 更高效且更健壮的实现，避免多次遍历和异常
        for k, v in self.axis_name.value.items():
            if v == name:
                return k
        return -1
        
    def getAxisInfo(self, name:str) -> AxisInfo | None:
        """ 获取指定轴的信息 """
        if name not in self.axis_name.value.values():
            return None
        data = AxisInfo(
            name=name,
            title=self.title.value.get(name, 'Axis'),
            pulse_equivalent=self.pulse_equivalent.value.get(name, 1.0),
            max_velocity=self.max_velocity.value.get(name, 1000.0),
            acceleration=self.acceleration.value.get(name, 1000.0),
            deceleration=self.deceleration.value.get(name, 1000.0),
            sramp=self.sramp.value.get(name, 0.0),
            min_position=self.min_position.value.get(name, -1000.0),
            max_position=self.max_position.value.get(name, 1000.0),
            decimal=self.decimal.value.get(name, 2),
            single_step=self.single_step.value.get(name, 0.1),
            distance_unit=self.distance_unit.value.get(name, 'mm'),
            group=self.group.value.get(name, -1),
        )
        return data
        
class AxisOptionWidget(qfluentwidgets.HeaderCardWidget):
    def __init__(self, setting_config:AxisSettingConfig, parent=None):
        super().__init__(parent)
        self.setTitle(self.tr("轴配置"))
        self.setMinimumSize(300, 300)
        
        self.scrollarea = qfluentwidgets.ScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.axisWidget = QWidget()
        self.scrollarea.setStyleSheet("background-color:transparent; border:none;")

        self.axisLayout = QVBoxLayout(self.axisWidget)
        self.scrollarea.setWidget(self.axisWidget)
        
        self.axis:AxisBase = None
        self.setting_config = setting_config
        
        self.pulseEquivalentLabel = qfluentwidgets.StrongBodyLabel(self.tr("脉冲当量:"))
        
        self.initLayout()
        
    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(5)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.addWidget(self.scrollarea)

        self.axisLayout.setContentsMargins(12, 12, 12, 12)
        self.axisLayout.setSpacing(5)
        self.axisLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.axisLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
    
    def setAxis(self, axis:AxisBase):
        """ 设置轴对象 """
        self.axis = axis
        
    def applySettings(self):
        """ 应用轴设置 """
        if self._axis is None:
            return
        # 在这里添加应用设置的逻辑
        # 例如：self._axis.set_velocity(self.velocitySpinBox.value())
        pass
    
class AxisWidgetBase:
    class State(Enum):
        IDLE = 0
        HOMING = 1
        MOVING = 2
        
    def __init__(self, parent):
        super().__init__(parent)
        
        self._axis:AxisBase = None
        self._state = AxisWidget.State.IDLE
        self._changedState = AxisWidget.State.IDLE 
        self.axisStatus = qfluentwidgets.DotInfoBadge(self, qfluentwidgets.InfoLevel.ERROR)
        
    def startScan(self, gapTime=100):
        """ 开始扫描轴状态 """
        if self._axis is None:
            return
        if self._timerId is not None:
            self.killTimer(self._timerId)
        self._timerId = self.startTimer(gapTime)

    def stopScan(self):
        """ 停止扫描轴状态 """
        if self._timerId is not None:
            self.killTimer(self._timerId)
            self._timerId = None
        self.axisStatus.setLevel(qfluentwidgets.InfoLevel.ERROR)
    
    def homed(self):
        """ 轴归位完成 """
        self._changedState = AxisWidget.State.IDLE
        self.axisStatus.setLevel(qfluentwidgets.InfoLevel.SUCCESS)
        
    def moved(self):
        """ 轴移动完成 """
        self._changedState = AxisWidget.State.IDLE
        self.axisStatus.setLevel(qfluentwidgets.InfoLevel.SUCCESS)
        
    def timerEvent(self, event:QTimerEvent):
        if event.timerId() == self._timerId:
            self.axisUpdate()
            return
        super().timerEvent(event)

class AxisWidget(AxisWidgetBase, qfluentwidgets.SimpleCardWidget):
    def __init__(self, name:str, setting_cfg:AxisSettingConfig, parent=None, **kwargs):
        super().__init__(parent)
        self.setObjectName("AxisWidget")
        self.name = name
        self.setting_cfg = setting_cfg

        self.isTorch = kwargs.get("isTorch", False)

        self.canOptionAxis = kwargs.get("canOptionAxis", False)
        self.setFixedSize(250, 310+32+12)
        
        self.enableButton = qfluentwidgets.SwitchButton(self)
        
        self.axisTitle = qfluentwidgets.StrongBodyLabel(self.tr("控制模块"))
        self.axisName = qfluentwidgets.BodyLabel(name)
        
        self.axisDposTitle = qfluentwidgets.BodyLabel(self.tr("指令位置:"))
        self.axisMposTitle = qfluentwidgets.BodyLabel(self.tr("反馈位置:"))
        self.axisDposValue = qfluentwidgets.BodyLabel("0.0000 mm")
        self.axisMposValue = qfluentwidgets.BodyLabel("0.0000 mm")
        
        self.homeBtn = ProgressPushButton(self.tr("回原"), self)
        self.axisVelocityTitle = qfluentwidgets.BodyLabel(self.tr("速度:"))
        if self.isTorch:
            self.axisVelocityValue = HrTorchCompactDoubleSpinBox()
        else:
            self.axisVelocityValue = HrCompactDoubleSpinBox()
        self.axisVelocityValue.setMaximumWidth(150)
        self.axisVelocityValue.setMinimum(0.0)
        self.axisVelocityValue.setMaximum(setting_cfg.max_velocity.value.get(name, 1000.0))
        self.axisVelocityValue.setSingleStep(1)
        self.axisVelocityValue.setValue(10.0)
        self.axisVelocityValue.setDecimals(1)
        self.axisVelocityValue.setSuffix(' '+setting_cfg.distance_unit.value.get(name, "mm")+'/s')
        self.setVelocityBtn = qfluentwidgets.PrimaryPushButton(self.tr("设置"))
        self.setVelocityBtn.setFixedSize(64, 32)

        self.forwardBtn = ProgressPushButton(self.tr("正转"), self)
        self.reverseBtn = ProgressPushButton(self.tr("反转"), self)
        self.forwardBtn.setFixedSize(64, 32)
        self.reverseBtn.setFixedSize(64, 32)
        
        self.absMoveTitle = qfluentwidgets.BodyLabel(self.tr("绝对移动:"))
        if self.isTorch:
            self.absMoveValue = HrTorchCompactDoubleSpinBox()
        else:
            self.absMoveValue = HrCompactDoubleSpinBox()
        self.absMoveValue.setMaximumWidth(150)
        self.absMoveValue.setMinimum(setting_cfg.min_position.value.get(name, -1000.0))
        self.absMoveValue.setMaximum(setting_cfg.max_position.value.get(name, 1000.0))
        self.absMoveValue.setSingleStep(setting_cfg.single_step.value.get(name, 0.1))
        if self.absMoveValue.minimum() > 0.0 or self.absMoveValue.maximum() < 0.0:
            self.absMoveValue.setValue(self.absMoveValue.minimum())
        else:
            self.absMoveValue.setValue(0.0)  # 默认值为0.0或在范围内
        self.absMoveValue.setDecimals(setting_cfg.decimal.value.get(name, 2))
        self.absMoveValue.setSuffix(' '+setting_cfg.distance_unit.value.get(name, "mm"))
        self.absMoveBtn = ProgressPushButton(self.tr("移动"))
        self.absMoveBtn.setFixedSize(64, 32)
        
        self.relMoveTitle = qfluentwidgets.BodyLabel(self.tr("相对移动:"))
        if self.isTorch:
            self.relMoveValue = HrTorchCompactDoubleSpinBox()
        else:
            self.relMoveValue = HrCompactDoubleSpinBox()
        self.relMoveValue.setMaximumWidth(150)
        self.relMoveValue.setMinimum(setting_cfg.min_position.value.get(name, -1000.0))
        self.relMoveValue.setMaximum(setting_cfg.max_position.value.get(name, 1000.0))
        self.relMoveValue.setSingleStep(setting_cfg.single_step.value.get(name, 0.1))
        self.relMoveValue.setValue(0)  # 默认值为0.0或在范围内
        self.relMoveValue.setDecimals(setting_cfg.decimal.value.get(name, 2))
        self.relMoveValue.setSuffix(' '+setting_cfg.distance_unit.value.get(name, "mm"))
        self.relMoveBtn = ProgressPushButton(self.tr("移动"))
        self.relMoveBtn.setFixedSize(64, 32)
        
        self.vBoxLayout = QVBoxLayout(self)
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.axisTitle, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.axisName, 0, Qt.AlignmentFlag.AlignRight)
        hBoxLayout.addWidget(self.axisStatus, 0, Qt.AlignmentFlag.AlignRight)
        self.vBoxLayout.addLayout(hBoxLayout)
        
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(qfluentwidgets.BodyLabel(self.tr("使能:"), self), 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addWidget(self.enableButton, 0, Qt.AlignmentFlag.AlignLeft)   
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.homeBtn, 0, Qt.AlignmentFlag.AlignRight)  
        self.vBoxLayout.addLayout(hBoxLayout)
        
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.axisDposTitle, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.axisDposValue, 0, Qt.AlignmentFlag.AlignLeft)
        self.vBoxLayout.addLayout(hBoxLayout)
        
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.axisMposTitle, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.axisMposValue, 0, Qt.AlignmentFlag.AlignLeft)
        self.vBoxLayout.addLayout(hBoxLayout)
        
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.axisVelocityValue, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.setVelocityBtn, 0, Qt.AlignmentFlag.AlignRight)

        vBoxLayout = QVBoxLayout()
        vBoxLayout.addWidget(self.axisVelocityTitle, 0, Qt.AlignmentFlag.AlignLeft)
        vBoxLayout.addLayout(hBoxLayout)
        self.vBoxLayout.addLayout(vBoxLayout)
        
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.forwardBtn, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout.addWidget(self.reverseBtn, 0, Qt.AlignmentFlag.AlignRight)
        self.vBoxLayout.addLayout(hBoxLayout)

        hBoxLayout = QVBoxLayout()
        hBoxLayout1 = QHBoxLayout()
        hBoxLayout.addWidget(self.absMoveTitle, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout1.addWidget(self.absMoveValue, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout1.addStretch(1)
        hBoxLayout1.addWidget(self.absMoveBtn, 0, Qt.AlignmentFlag.AlignRight)
        hBoxLayout.addLayout(hBoxLayout1)
        self.vBoxLayout.addLayout(hBoxLayout)
        
        hBoxLayout = QVBoxLayout()
        hBoxLayout1 = QHBoxLayout()
        hBoxLayout.addWidget(self.relMoveTitle, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout1.addWidget(self.relMoveValue, 0, Qt.AlignmentFlag.AlignLeft)
        hBoxLayout1.addStretch(1)
        hBoxLayout1.addWidget(self.relMoveBtn, 0, Qt.AlignmentFlag.AlignRight)
        hBoxLayout.addLayout(hBoxLayout1)
        self.vBoxLayout.addLayout(hBoxLayout)
        
        self.initConnects()
        self.timerCount = 0
        
    def initConnects(self):
        self.enableButton.checkedChanged.connect(self.onEnableButtonChanged)
        self.homeBtn.clicked.connect(self.onHomeBtnClicked)
        self.setVelocityBtn.clicked.connect(self.onSetVelocityBtnClicked)
        self.forwardBtn.clicked.connect(self.onForwordClicked)
        self.reverseBtn.clicked.connect(self.onReverseClicked)
        self.absMoveBtn.clicked.connect(self.onAbsMoveBtnClicked)
        self.relMoveBtn.clicked.connect(self.onRelMoveBtnClicked)
        
    def onSetVelocityBtnClicked(self):
        """ 设置轴速度 """
        if self._axis is None:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("轴对象未设置。"),
                parent=self.window())
            return
        try:
            velocity = self.axisVelocityValue.value()
            if velocity < 0.0 or velocity > self.setting_cfg.max_velocity.value.get(self.name, 1000.0):
                raise ValueError(self.tr("速度值超出范围。"))
            self._axis.set_velocity(velocity)
            qfluentwidgets.InfoBar.success(
                self.tr("成功"), 
                self.tr("轴速度已设置为 {0} {1}/s").format(velocity, self.setting_cfg.distance_unit.value.get(self.name, "mm")),
                parent=self.window())
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("设置速度失败: {0}").format(str(e)),
                parent=self.window())
        
    def onEnableButtonChanged(self, checked:bool):
        """ 启用或禁用轴 """
        if self._axis is None:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("轴对象未设置。"),
                parent=self.window())
            return
        if checked:
            self._axis.enable()
        else:
            self._axis.disable()
        
    def onHomeBtnClicked(self):
        try:
            if self.homeBtn.isLoading():
                self.__canceled()
                # self.homeBtn.reset()
            else:
                if self._axis is None:
                    raise ValueError(self.tr("未设置轴对象。"))
                if self._state == AxisWidget.State.IDLE and self._axis.is_enabled():
                    self._axis.home()
                    # self.homeBtn.load()
                    self._changedState = AxisWidget.State.HOMING
                else:
                    raise RuntimeError(self.tr("轴未启用或不在空闲状态。"))
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("回原失败: {0}").format(str(e)),
                parent=self.window())
        
    def onForwordClicked(self):
        try:
            if self.forwardBtn.isLoading():
                self.__canceled()
                # self.forwardBtn.reset()
            else:
                if self._axis is None:
                    raise ValueError(self.tr("轴对象未设置。"))
                if self._state == AxisWidget.State.IDLE and self._axis.is_enabled():
                    velocity = self.axisVelocityValue.value()
                    self._axis.continuous_move(1, velocity=velocity)
                    self._changedState = AxisWidget.State.MOVING
                else:
                    raise RuntimeError(self.tr("轴未启用或不在空闲状态。"))
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("正转失败: {0}").format(str(e)),
                parent=self.window())
            
    def onReverseClicked(self):
        try:
            if self.reverseBtn.isLoading():
                self.__canceled()
                # self.reverseBtn.reset()
            else:
                if self._axis is None:
                    raise ValueError(self.tr("轴对象未设置。"))
                if self._state == AxisWidget.State.IDLE and self._axis.is_enabled():
                    velocity = self.axisVelocityValue.value()
                    self._axis.continuous_move(-1, velocity=velocity)
                    self._changedState = AxisWidget.State.MOVING
                else:
                    raise RuntimeError(self.tr("轴未启用或不在空闲状态。"))
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("反转失败: {0}").format(str(e)),
                parent=self.window())   

    def onAbsMoveBtnClicked(self):
        try:
            if self.absMoveBtn.isLoading():
                self.__canceled()
                # self.absMoveBtn.reset()
            else:
                if self._axis is None:
                    raise ValueError(self.tr("轴对象未设置。"))
                if self._state == AxisWidget.State.IDLE and self._axis.is_enabled():
                    velocity = self.axisVelocityValue.value()
                    value = self.absMoveValue.value()
                    self._axis.move_absolute(value, velocity)
                    # self.absMoveBtn.load()
                    self._changedState = AxisWidget.State.MOVING
                else:
                    raise RuntimeError(self.tr("轴未启用或不在空闲状态。"))
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"), 
                self.tr("绝对移动失败: {0}").format(str(e)),
                parent=self.window())
        
    def onRelMoveBtnClicked(self):
        try:
            if self.relMoveBtn.isLoading():
                self.__canceled()
                # self.relMoveBtn.reset()
            else:
                if self._axis is None:
                    raise ValueError(self.tr("轴对象未设置。"))
                if self._state == AxisWidget.State.IDLE and self._axis.is_enabled():
                    velocity = self.axisVelocityValue.value()
                    value = self.relMoveValue.value()
                    self._axis.move_relative(value, velocity)
                    # self.relMoveBtn.load()
                    self._changedState = AxisWidget.State.MOVING
                else:
                    raise RuntimeError(self.tr("轴未启用或不在空闲状态。"))
        except Exception as e:
            qfluentwidgets.InfoBar.error(
                self.tr("错误"),
                self.tr("相对移动失败: {0}").format(str(e)),
                parent=self.window())
        
    def __canceled(self):
        if self._axis is not None:
            self._axis.stop()
        self._changedState = AxisWidget.State.IDLE
        # self.__reset()
        
    def __load(self):
        self.absMoveBtn.load()
        self.relMoveBtn.load()
        self.homeBtn.load()
        self.reverseBtn.load()
        self.forwardBtn.load()
        
    def __reset(self):
        self.absMoveBtn.reset()
        self.relMoveBtn.reset()
        self.homeBtn.reset()
        self.reverseBtn.reset()
        self.forwardBtn.reset()

    def dposUpdated(self, dpos):
        self.axisDposValue.setText(f"{dpos:.4f} mm")
    
    def mposUpdated(self, mpos):
        self.axisMposValue.setText(f"{mpos:.4f} mm")
        
    def setAxis(self, axis: AxisBase):
        """ 设置轴对象 """
        self._axis = axis
        self.enableButton.setChecked(axis.is_enabled())
        
    def axisUpdate(self):
        if self._axis is not None:
            self.timerCount = self.timerCount + 1
            if self.timerCount % 10 == 0:
                self.timerCount = 0
            # 更新轴状态
            is_enable = self._axis.is_enabled()
            if is_enable:
                self.enableButton.blockSignals(True)
                self.enableButton.setChecked(True)
                self.enableButton.blockSignals(False)
            else:
                self.enableButton.blockSignals(True)
                self.enableButton.setChecked(False)
                self.enableButton.blockSignals(False)
                self.axisStatus.setLevel(qfluentwidgets.InfoLevel.WARNING)
                
            dpos = self._axis.get_dpos()
            mpos = self._axis.get_mpos()
            self.dposUpdated(dpos)
            self.mposUpdated(mpos)
            
            if is_enable:
                if self._state == AxisWidget.State.HOMING:
                    if self._axis.is_homed():
                        self.homed()
                    else:
                        self.axisStatus.setText(self.tr("Homing..."))
                        self.axisStatus.setLevel(qfluentwidgets.InfoLevel.ATTENTION)
                elif self._state == AxisWidget.State.MOVING:
                    if not self._axis.idle():
                        self.axisStatus.setText(self.tr("Moving..."))
                        self.axisStatus.setLevel(qfluentwidgets.InfoLevel.ATTENTION)
                    else:
                        self.moved()
                elif self._state == AxisWidget.State.IDLE:
                    self.axisStatus.setText(self.tr("Idle"))
                    self.axisStatus.setLevel(qfluentwidgets.InfoLevel.SUCCESS)
                
                if not self._axis.idle():
                    self.__load()
                    velocity = self._axis.get_velocity()
                    velocity_round = round(velocity, self.setting_cfg.decimal.value.get(self.name, 2))
                    if velocity_round != self.axisVelocityValue.value() and not self.axisVelocityValue.hasFocus():
                        self.axisVelocityValue.blockSignals(True)
                        self.axisVelocityValue.setValue(velocity_round)
                        self.axisVelocityValue.blockSignals(False)
                else:
                    self.__reset()
                    
                self.relMoveValue.setRange(
                    self.absMoveValue.minimum() - mpos,
                    self.absMoveValue.maximum() - mpos
                )
                
            if self._state != self._changedState:
                self._state = self._changedState
        else:
            self.axisStatus.setLevel(qfluentwidgets.InfoLevel.ERROR)
        
    def contextMenuEvent(self, event):
        if not self.canOptionAxis:
            super().contextMenuEvent(event)
            return
        
        """ 右键菜单事件 """
        menu = qfluentwidgets.RoundMenu(parent=self)
        action = qfluentwidgets.Action(qfluentwidgets.FluentIcon.SETTING, self.tr("Settings"))
        menu.addAction(action)
        
        def showSettings():
            
            """ 显示轴设置对话框 """
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("Axis Settings"))
            layout_ = QVBoxLayout(dialog)
            layout_.setContentsMargins(12, 12, 12, 12)
            settingWidget = AxisOptionWidget(self.setting_cfg, self)
            settingWidget.setAxis(self._axis)
            layout_.addWidget(settingWidget)
            buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
            buttonBox.accepted.connect(lambda: settingWidget.applySettings())
            buttonBox.rejected.connect(dialog.reject)
            layout_.addWidget(buttonBox)
            dialog.exec()
            
        action.triggered.connect(showSettings)
        menu.exec(event.globalPos())
    
class AxisControlWidget(qfluentwidgets.HeaderCardWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setTitle(self.tr("轴控制器"))
        self.setMinimumSize(300, 300)
        
        self.scrollarea = qfluentwidgets.ScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.axisWidget = QWidget()
        self.scrollarea.setStyleSheet("background-color:transparent; border:none;")

        self.axisLayout = qfluentwidgets.FlowLayout(self.axisWidget)
        # self.axisLayout = QVBoxLayout(self.axisWidget)
        self.scrollarea.setWidget(self.axisWidget)
        
        self.initLayout()
        
        self.timerId = self.startTimer(200)  # 每100毫秒更新一次
        
    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(5)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.addWidget(self.scrollarea)

        self.axisLayout.setContentsMargins(12, 12, 12, 12)
        self.axisLayout.setSpacing(5)
        # self.axisLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.axisLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
    def addAxis(self, name, axis:AxisBase, setting_cfg:AxisSettingConfig, **kwargs):
        """ 添加轴控件到指定位置 """
        axisWidget = AxisWidget(name, setting_cfg, self, **kwargs)
        axisWidget.setAxis(axis)
        self.axisLayout.addWidget(axisWidget)
        
    def timerEvent(self, event:QTimerEvent):
        if event.timerId() == self.timerId:
            for i in range(self.axisLayout.count()):
                item = self.axisLayout.itemAt(i)
                if item is not None:
                    widget = item.widget()
                    if isinstance(widget, AxisWidget):
                        widget.axisUpdate()
                else:
                    continue
            return
        return super().timerEvent(event)

if __name__ == "__main__":
    import sys
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    qfluentwidgets.setTheme(qfluentwidgets.Theme.DARK)

    # widget = BtnDirection()
    # widget.onBtnPress.connect(lambda dire: print(f"Button pressed: {dire.name}"))
    # widget.onBtnRelease.connect(lambda: print("Button released"))
    # widget.show()
    
    # def clicked():
    #     print("Button clicked!")
    #     widget.load()
    #     QTimer.singleShot(2000, lambda: widget.reset())
    
    widget = AxisWidget()
    widget.show()
    sys.exit(app.exec())