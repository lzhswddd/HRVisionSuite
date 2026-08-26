import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter, QPixmap,QImage,QPen,QPolygonF
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget,QGraphicsScene,QGraphicsPixmapItem,QGraphicsPolygonItem,QGridLayout
from hrfluentwidgets import CameraView,CameraResultView,CameraEditView,GroupCameraView
from qfluentwidgets import ToggleButton
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import Theme,setTheme,setThemeColor
class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('Demo{background: rgb(32, 32, 32)}')
        self.setWindowTitle("GroupCameraView Demo")
        self.lay = QVBoxLayout(self)

        cameraList = ["camera-1","camera-2","camera-3","camera-4","camera-5"]
        self.cameraView = GroupCameraView(cameraList,self)
        self.cameraView.setRowandCol(2,3)
        self.cameraView.setViewType(CameraResultView) 
        self.cameraView.initWidget()


        self.cameraView.setImage("camera-4",QImage("C:\\Users\\sr\\OneDrive\\Desktop\\执照.jpg"))
        self.lay.addWidget(self.cameraView)

        self.cameraView.getCamaeraView("camera-2").setResultText('''
        <span style="font-size: 20px;">
            <b style="color: #FF0000;">摄像头状态：</b>
            <b style="color: #00FF00;">运行中</b><br>
            <i>分辨率：</i>1920x1080
        </span>
        ''')
        


if __name__ == "__main__":
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    demo = Demo()
    demo.show()
    app.exec()