import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter, QPixmap,QImage,QPen,QPolygonF
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget,QGraphicsScene,QGraphicsPixmapItem,QGraphicsPolygonItem,QGridLayout
from hrfluentwidgets import CameraView,CameraResultView,CameraEditView
from qfluentwidgets import ToggleButton
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import Theme,setTheme,setThemeColor
class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('Demo{background: rgb(32, 32, 32)}')
        self.setWindowTitle("CameraView Demo")
        self.lay = QGridLayout(self)
        
        self.cameraView = CameraView(self)
        self.cameraView.setTitle("camera-1")
        self.lay.addWidget(self.cameraView,0,0,1,1)

        self.cameraResultView = CameraResultView(self)
        self.cameraResultView.setTitle("camera-2")
        self.cameraResultView.setResultAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)
        self.cameraResultView.setResultText('''
        <span style="font-size: 20px;">
            <b style="color: #FF0000;">摄像头状态：</b>
            <b style="color: #00FF00;">运行中</b><br>
            <i>分辨率：</i>1920x1080
        </span>
    ''')
        self.lay.addWidget(self.cameraResultView,1,0,1,1)

        self.cameraEditView = CameraEditView(self)
        self.cameraEditView.setTitle("camera-3 - 编辑框")
        self.lay.addWidget(self.cameraEditView,0,1,1,1)
        


if __name__ == "__main__":
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    demo = Demo()
    demo.show()
    app.exec()