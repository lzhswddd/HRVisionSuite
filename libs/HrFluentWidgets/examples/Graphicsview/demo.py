import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QHBoxLayout
from hrfluentwidgets import (GraphicsView,
                             GraphicsRectItem,
                             GraphicsItemScene,
                             GraphicsPolygonItem,
                             GraphicsCaliperRectItem,
                             GraphicsRotatedRectItem,
                             GraphicsCaliperRotatedRectItem,
                             GraphicsLineItem,
                             GraphicsCaliperLineItem,
                             GraphicsBezierCurveItem,
                             GraphicsCaliperCurveItem
                             )

from qfluentwidgets import ToggleButton
from qfluentwidgets import FluentIcon as FIF

class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GraphicsView Demo")

        self.rectBtn = ToggleButton(FIF.ADD, '矩形', self)
        self.polygonBtn = ToggleButton(FIF.ADD_TO, '多边形', self)
        self.rectCaliperBtn = ToggleButton(FIF.ADD_TO, '矩形卡尺', self)
        self.rotatedRectBtn = ToggleButton(FIF.ADD_TO, '旋转矩形', self)
        self.rotatedRectCaliperBtn = ToggleButton(FIF.ADD_TO, '旋转矩形卡尺', self)
        self.lineBtn = ToggleButton(FIF.ADD_TO, '直线', self)
        self.lineCapilerBtn = ToggleButton(FIF.ADD_TO, '直线卡尺', self)
        self.curveBtn = ToggleButton(FIF.ADD_TO, '曲线', self)
        self.testBtn = ToggleButton(FIF.ADD_TO, '测试', self)
        
        self.rectBtn.clicked.connect(self.btnClicked)
        self.polygonBtn.clicked.connect(self.polygonBtnClicked)
        self.rectCaliperBtn.clicked.connect(self.rectCaliperBtnClicked)
        self.rotatedRectBtn.clicked.connect(self.rotatedRectBtnClicked)
        self.rotatedRectCaliperBtn.clicked.connect(self.rotatedRectCaliperBtnClicked)
        self.lineBtn.clicked.connect(self.lineBtnClicked)
        self.lineCapilerBtn.clicked.connect(self.lineCapilerBtnClicked)
        self.curveBtn.clicked.connect(self.curveBtnClicked)
        self.testBtn.clicked.connect(self.testBtnClicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graphicsview = GraphicsView(self)
        
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        
        hlayout.addWidget(self.rectBtn)
        hlayout.addWidget(self.polygonBtn)
        hlayout.addWidget(self.rectCaliperBtn)
        hlayout.addWidget(self.rotatedRectBtn)
        hlayout.addWidget(self.rotatedRectCaliperBtn)
        hlayout.addWidget(self.lineBtn)
        hlayout.addWidget(self.lineCapilerBtn)
        hlayout.addWidget(self.testBtn)
        layout.addLayout(hlayout)
        layout.addWidget(self.graphicsview)

        self.scene = GraphicsItemScene(self)
        self.graphicsview.setScene(self.scene)

        self.scene.setImage(QImage(":/resource/images/test.jpg"))
        self.scene.setContinueEditMode(False)
        # self.scene.addItemFunc = lambda: GraphicsPolygonItem()

        # self.scene.addItem(self.plyogonItem)
        self.resize(800, 600)
        
        def onItemFinished(item):
            if isinstance(item, GraphicsCaliperRectItem):
                print("矩形卡尺区域：", item.rect())
            elif isinstance(item, GraphicsPolygonItem):
                print("多边形区域：", item.polygon())
            elif isinstance(item, GraphicsRectItem):
                print("矩形区域：", item.rect())    
    
        self.scene.itemFinished.connect(onItemFinished)

    def btnClicked(self):
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio) 
        self.scene.setEditMode(self.rectBtn.isChecked())
        self.scene.addItemFunc = lambda: GraphicsRectItem()

    
    def polygonBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsPolygonItem()
        self.scene.setEditMode(self.polygonBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)

    def rectCaliperBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsCaliperRectItem(caliperWidth=10, caliperHeight=100, caliperGap=50)
        self.scene.setEditMode(self.rectCaliperBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)

    def rotatedRectBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsRotatedRectItem()
        self.scene.setEditMode(self.rotatedRectBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)
        
    def rotatedRectCaliperBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsCaliperRotatedRectItem(caliperWidth=10, caliperHeight=100, caliperGap=50)
        self.scene.setEditMode(self.rotatedRectCaliperBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)

    def lineBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsLineItem()
        self.scene.setEditMode(self.lineBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)
        
    def lineCapilerBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsCaliperLineItem(caliperWidth=10, caliperHeight=100, caliperGap=50)
        self.scene.setEditMode(self.lineCapilerBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)
        
    def curveBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsBezierCurveItem()
        self.scene.setEditMode(self.curveBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)
        
    def testBtnClicked(self):
        self.scene.addItemFunc = lambda: GraphicsCaliperCurveItem(caliperWidth=10, caliperHeight=100, caliperGap=50)
        self.scene.setEditMode(self.testBtn.isChecked())
        self.graphicsview.fitInView(self.scene.imageItem(), Qt.KeepAspectRatio)

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    app.exec()