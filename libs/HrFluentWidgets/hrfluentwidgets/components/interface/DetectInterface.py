import sys
from PySide6.QtCore  import Qt,QRect,QSize
from PySide6.QtGui import QColor,QPixmap,QImage
from PySide6.QtWidgets import QApplication,QHBoxLayout,QLabel,QWidget,QSizePolicy,QVBoxLayout,QSpacerItem
from qfluentwidgets import SplitTitleBar,BodyLabel,LineEdit,PrimaryPushButton,PasswordLineEdit,isDarkTheme,setThemeColor
from qfluentwidgets import InfoBar,InfoBarPosition,ComboBox
from ..CameraView import GroupCameraView,CameraResultView
from ...common import LogWidget

class DetectInterface(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.cameraWidget = None
        self.customWidget = QWidget()
        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)
        self.customWidget.setLayout(self.vlayout)
        self.logWidget = LogWidget()


    def setCameraList(self,cameraList,row,col):
        self.cameraWidget = GroupCameraView(cameraList,self)
        self.cameraWidget.setRowandCol(row,col)
        self.cameraWidget.setViewType(CameraResultView)
        self.cameraWidget.initWidget()
     

    def initLayout(self):
        if self.cameraWidget:
            self.layout.addWidget(self.cameraWidget)
            self.layout.setStretchFactor(self.cameraWidget, 8)
        self.vlayout.addWidget(self.logWidget)
        self.layout.addWidget(self.customWidget)
        self.layout.setStretchFactor(self.customWidget, 2)

    def updateCameraImage(self,cameraName,image:QImage):
        if self.cameraWidget:
            self.cameraWidget.setImage(cameraName,image)

    def insertCustomWidget(self,index,widget):
        self.vlayout.insertWidget(index,widget)

    def appendLog(self,text):
        self.logWidget.append(text)

    def upDateDetectResult(self, cameraName, result="", status="运行中", custom_data=None):
        """
        更新摄像头检测结果展示
        参数:
            cameraName: 摄像头名称 
            result: 检测结果 (OK/NG)
            status: 摄像头状态，默认"运行中"
            custom_data: 字典类型，可包含分辨率等自定义参数
        """
        if(result != ""):
            self.result = result

        if self.cameraWidget:
            # 结果颜色配置
            # camera_color = "#00FF00" if status == "运行中" else "#FF0000"
            camera_color = "#00FF00"
            result_color = "#00FF00" if self.result == "OK" else "#FF0000"
            result_text = self.result
            
            # 自定义数据解析
            resolution = custom_data.get("resolution", "1920x1080") if custom_data else "1920x1080"
            
            # 构建动态HTML
            html_template = f'''
            <span style="font-size: 20px;">
                <b style="color: #FF0000;">相机: </b>
                <b style="color: {camera_color};">{status}</b><br>
                <b style="color: #00FF00;">结果: </b>
                <b style="color: {result_color};">{result_text}</b>
            </span>
            '''
            
            # 获取对应摄像头视图并更新
            self.cameraWidget.getCamaeraView(cameraName).setResultText(html_template)