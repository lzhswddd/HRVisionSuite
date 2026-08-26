import sys
from PySide6.QtCore  import Qt,Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QHBoxLayout,QWidget,QVBoxLayout,QStackedWidget, QGraphicsItem
from qfluentwidgets import CaptionLabel,PrimaryPushButton,CompactSpinBox,TextEdit,DoubleSpinBox
from qfluentwidgets import ComboBox,HeaderCardWidget
from ..CameraView import CameraView
from ...common import HrIcon,GraphicsCrossItem,GraphicsRectItem
from enum import Enum
import json

#棋盘标定,九点标定
class CalibrationType(Enum):
    CHESSBOARD = 0
    NINE_POINT = 1

class ChessboardCalibrationWidget(HeaderCardWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.calibrationFun = None

        self.setTitle("棋盘标定")
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)
        self.rowSpinBox = CompactSpinBox(self)
        self.colSpinBox = CompactSpinBox(self)
        self.sizeSpinBox = CompactSpinBox(self)
        self.sizeSpinBox.setSuffix("mm")
        self.sizeSpinBox.setRange(1,1000)
        self.calibrationBtn = PrimaryPushButton(self.tr("开始标定"),self)
        self.logview = TextEdit(self)
        self.logview.setReadOnly(True)

        self.initLayout()
        self.calibrationBtn.clicked.connect(self.__calibrationBtnClicked)

    def initLayout(self):
        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(6)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.addWidget(CaptionLabel(self.tr("行数:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.rowSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("列数:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.colSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("格子实际距离:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.sizeSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("标定按钮:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.calibrationBtn,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("日志:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.logview,0,Qt.AlignmentFlag.AlignLeft)

        self.viewLayout.setContentsMargins(12, 12, 12, 12)
        self.viewLayout.addLayout(self.vlayout)

    def updateLog(self,log:str):
        self.logview.append(log)

    def __calibrationBtnClicked(self):
        # 处理按钮点击事件
        if self.calibrationFun:
            data = {
                "row": self.rowSpinBox.value(),
                "col": self.colSpinBox.value(),
                "size": self.sizeSpinBox.value()
            }
            # print(self.objectName(),json.dumps(data))
            self.calibrationFun(self.objectName(),json.dumps(data))
        else:
            print("calibrationFun is None")

class NinePointCalibrationWidget(HeaderCardWidget):
    addRectSignal = Signal(str,QGraphicsItem)
    def __init__(self,parent=None):
        super().__init__(parent)

        self.calibrationFun = None

        self.rectItem = GraphicsRectItem()
        self.rectItem.setRect(0,0,200,200)
        self.rectItem.state = 2  #跳过编辑状态

        self.setTitle("九点标定")
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)
        self.rectBtn = PrimaryPushButton(HrIcon.RECT,self.tr("ROI"),self)
        self.matchSpinBox = DoubleSpinBox(self)
        self.xSpinBox = DoubleSpinBox(self)
        self.ySpinBox = DoubleSpinBox(self)
        self.rSpinBox = DoubleSpinBox(self)
        self.xSpinBox.setSuffix("mm")
        self.ySpinBox.setSuffix("mm")
        self.rSpinBox.setSuffix("°")
        self.calibrationBtn = PrimaryPushButton(self.tr("开始标定"),self)
        self.logview = TextEdit(self)
        self.logview.setReadOnly(True)

        self.initLayout()

        self.calibrationBtn.clicked.connect(self.__calibrationBtnClicked)
        self.rectBtn.clicked.connect(self.__addRoiRect)

    def initLayout(self):
        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(6)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.addWidget(CaptionLabel(self.tr("创建模板:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.rectBtn,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("匹配阈值:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.matchSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("X移动量:")))
        self.vlayout.addWidget(self.xSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("Y移动量:")))
        self.vlayout.addWidget(self.ySpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("R旋转量:")))
        self.vlayout.addWidget(self.rSpinBox,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("标定按钮:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.calibrationBtn,0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(CaptionLabel(self.tr("日志:")),0,Qt.AlignmentFlag.AlignLeft)
        self.vlayout.addWidget(self.logview,0,Qt.AlignmentFlag.AlignLeft)

        self.viewLayout.setContentsMargins(12, 12, 12, 12)
        self.viewLayout.addLayout(self.vlayout)

    def updateLog(self,log:str):
        self.logview.append(log)

    def __calibrationBtnClicked(self):
        # 处理按钮点击事件
        if not self.calibrationFun:
            if not self.rectItem.scene():
                return
            
            pixItem =  self.rectItem.scene().imageItem()
            if not pixItem:
                return
            
            rect = pixItem.mapFromItem(self.rectItem,self.rectItem.rect()).boundingRect()
            
            data = {
                "rect": {
                    "x": rect.x(),
                    "y": rect.y(),
                    "width": rect.width(),
                    "height": rect.height()
                },
                "matchThreshold": self.matchSpinBox.value(),
                "x": self.xSpinBox.value(),
                "y": self.ySpinBox.value(),
                "r": self.rSpinBox.value()
            }
            print(self.objectName(),json.dumps(data))
            self.calibrationFun(self.objectName(),json.dumps(data))
        else:
            print("calibrationFun is None")

    def __addRoiRect(self):
        if self.rectItem.scene() is None:
            self.addRectSignal.emit(self.objectName(),self.rectItem)
            
class CalibrationBase(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)

        self.headerWidget = HeaderCardWidget(self.tr("相机列表"),self)
        self.cameraStackeds = QStackedWidget(self)
        self.optionStackeds = QStackedWidget(self)
        self.pivot = ComboBox(self)

        self.pivot.currentTextChanged.connect(self.__onPivotChanged)

        self.initLayout()

    def initLayout(self):
        self.headerWidget.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerWidget.headerView.setFixedHeight(32)
        self.headerWidget.viewLayout.setContentsMargins(12, 12, 12, 12)
        self.headerWidget.viewLayout.addWidget(self.pivot)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(5)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.addWidget(self.headerWidget)
        self.vlayout.addWidget(self.optionStackeds)

        self.hlayout = QHBoxLayout(self)
        self.hlayout.setSpacing(5)
        self.hlayout.setContentsMargins(12, 12,12, 12)
        self.hlayout.addWidget(self.cameraStackeds)
        self.hlayout.addLayout(self.vlayout)

        self.hlayout.setStretchFactor(self.cameraStackeds, 7)
        self.hlayout.setStretchFactor(self.vlayout, 1)

    def __onPivotChanged(self,k):
        camera_widget = self.cameraStackeds.findChild(QWidget, k)
        option_widget = self.optionStackeds.findChild(QWidget, k)
        if camera_widget and option_widget:
            self.cameraStackeds.setCurrentWidget(camera_widget)
            self.optionStackeds.setCurrentWidget(option_widget)

    def addCalibrationWidget(self,CameraName:str,CalibrationType:CalibrationType):
        self.pivot.addItem(CameraName)
        widget = CameraView(self.cameraStackeds)
        widget.setTitle(CameraName)
        widget.setObjectName(CameraName)
        self.cameraStackeds.addWidget(widget)

        if CalibrationType == CalibrationType.CHESSBOARD:
            widget2 = ChessboardCalibrationWidget()
            widget2.setObjectName(CameraName)
            self.optionStackeds.addWidget(widget2)

        elif CalibrationType == CalibrationType.NINE_POINT:
            widget2 = NinePointCalibrationWidget()
            widget2.setObjectName(CameraName)
            self.optionStackeds.addWidget(widget2)
            widget2.addRectSignal.connect(self.__addRoiRect)
  
    def updateImage(self,cameraName:str,image:QImage):
        camera_widget = self.cameraStackeds.findChild(CameraView, cameraName)
        if camera_widget:
            camera_widget.scene.setImage(image)

    def updateCalibrationLog(self,cameraName:str,log:str):
        option_widget = self.optionStackeds.findChild(QWidget, cameraName)
        if option_widget:
           option_widget.updateLog(log)

    def updateCrossItems(self,cameraName:str,pos_list:list):
        camera_widget = self.cameraStackeds.findChild(CameraView, cameraName)
        if camera_widget:
            for pos in pos_list:
                scenePos = camera_widget.scene.imageItem().mapToScene(pos)
                item = GraphicsCrossItem()
                item.setPos(scenePos)
                camera_widget.scene.addItem(item)

    def __addRoiRect(self,cameraName:str,item:QGraphicsItem):
        camera_widget = self.cameraStackeds.findChild(CameraView, cameraName)
        if camera_widget:
            camera_widget.scene.addItem(item)