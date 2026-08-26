import sys
from PySide6.QtCore  import Qt,Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QGraphicsItem,QGridLayout,QLabel,QWidget,QSizePolicy,QVBoxLayout,QHBoxLayout,QFrame
from qfluentwidgets import HeaderCardWidget
from qfluentwidgets import CommandBar,Action
from qfluentwidgets import FluentIcon as FIF
from ...common import GraphicsScene,GraphicsItemScene
from ...common import GraphicsView,InterfaceView

class MatchView(QFrame):
    def __init__(self,parent=None,**kwargs):
        super().__init__(parent, **kwargs)
        self.setObjectName('MatchView')
        self.viewlayout = QVBoxLayout(self)
        self.viewlayout.setContentsMargins(0, 0, 0, 0)
        self.viewlayout.setSpacing(0)
        self.viewlayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewlayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.view = kwargs.get('viewType', InterfaceView)(self)
        self.view.setMinimumHeight(200)
        self.view.setMaximumHeight(300)
        self.view.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred)
        self.scene = GraphicsScene(self)
        self.view.setScene(self.scene)
        self.scene.setObjectName('scene')
        self.scene.setImage(QImage())

        self.viewlayout.addWidget(self.view)
        self.view.setObjectName('view')

    def fitView(self):
        if self.scene.imageItem() is not None:
            self.scene.setSceneRect(self.scene.itemsBoundingRect())
            self.view.fitInView(self.scene.imageItem(), Qt.AspectRatioMode.KeepAspectRatio)

class CameraView(HeaderCardWidget):
    def __init__(self,parent=None,**kwargs):
        super().__init__(parent, **kwargs)
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)
        self.setObjectName('cameraView')
        
        self.graphicsView = kwargs.get('viewType', InterfaceView)(self)
        self.scene = self.creatScene()
        self.commanBar = CommandBar(self)
        # self.viewLayout2 = QVBoxLayout(self)
        self.graphicsView.setShowMagnifier(True)
        self.graphicsView.setScene(self.scene)
        self.scene.setImage(QImage())

        self.commanBar.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.commanBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.creatCommandBar()

        self.headerLayout.addWidget(self.commanBar,0,Qt.AlignmentFlag.AlignRight)
        self.viewLayout.setContentsMargins(1, 1, 1, 1)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.addWidget(self.graphicsView)

    def creatCommandBar(self):
        action = Action(FIF.ADD, self.tr('十字'), self)
        action.setCheckable(True)
        action.triggered.connect(self.graphicsView.setDrawCross)
        self.commanBar.addAction(action)

        action = Action(FIF.ZOOM_IN, self.tr('放大'), self)
        action.triggered.connect(self.graphicsView.scaleUp)
        self.commanBar.addAction(action)

        action = Action(FIF.ZOOM_OUT, self.tr('缩小'), self)
        action.triggered.connect(self.graphicsView.scaleDown)
        self.commanBar.addAction(action)

        action = Action(FIF.FIT_PAGE, self.tr('适应'), self)
        action.triggered.connect(self._fitView)
        self.commanBar.addAction(action)

        self.commanBar.addSeparator()

        action = Action(FIF.CLEAR_SELECTION, self.tr('清除'), self)
        action.triggered.connect(lambda:self.scene.clearOthers())
        self.commanBar.addAction(action)

    def creatScene(self):
        return GraphicsScene(self)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self._fitView()
        elif event.key() == Qt.Key.Key_Delete:
            self.scene.clearOthers()
        elif event.key() == Qt.Key.Key_Equal:
            self.graphicsView.scaleUp()
        elif event.key() == Qt.Key.Key_Minus:
            self.graphicsView.scaleDown()
        elif event.key() == Qt.Key.Key_X:
            self.graphicsView.setDrawCross(not self.graphicsView.isDrawCross())
        return super().keyPressEvent(event)
        
    def _fitView(self):
        if self.scene.imageItem() is not None:
            # print(self.scene.imageItem().boundingRect(),self.graphicsView.size(),self.graphicsView.viewport().size(),self.scene.sceneRect())
            self.scene.setSceneRect(self.scene.itemsBoundingRect())
            self.graphicsView.fitInView(self.scene.imageItem(), Qt.AspectRatioMode.KeepAspectRatio)
            self.graphicsView.centerOn(self.scene.imageItem())
        
class CameraResultView(CameraView):
    def __init__(self,parent=None,**kwargs):
        super().__init__(parent, **kwargs)
        self.setObjectName('cameraResultView')
        self.layout = QHBoxLayout(self.graphicsView)
        self.resultLabel = QLabel(self.graphicsView)
        self.resultLabel.setTextFormat(Qt.TextFormat.RichText)

        self.resultLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 穿透鼠标事件
        self.layout.addWidget(self.resultLabel,0,Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
        
    def setResultAlignment(self,align):
        self.layout.setAlignment(align)

    def setResultText(self,text):
        self.resultLabel.setText(text)
        self.resultLabel.adjustSize()
  
class CameraEditView(CameraView):
    itemCreated = Signal(QGraphicsItem)
    itemChanged = Signal(QGraphicsItem)

    def __init__(self,parent=None,**kwargs):
        super().__init__(parent, **kwargs)
        self.setObjectName('cameraEditView')

        self.initConnect()

    def creatScene(self):
        return GraphicsItemScene(self)
    
    def initConnect(self):
        self.scene.itemFinished.connect(self.itemCreated)

class GroupCameraView(QWidget):
    def __init__(self,routkey:list,parent=None):
        super().__init__(parent)
        self.routkey = routkey
        self.viewLayout = QGridLayout(self)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)
        self.viewType = None
        self.cameras = {}
        self.cols = 2
        self.rows = 2
    
    def setRowandCol(self,rows,cols):
        self.rows = rows
        self.cols = cols
        for _ in range(self.rows):
            self.viewLayout.setRowStretch(_, 1)
        for _ in range(self.cols):
            self.viewLayout.setColumnStretch(_, 1)

    def setViewType(self,viewType):
        self.viewType = viewType
    
    def initWidget(self):
        if self.viewType != None:
            for i in range(self.rows):
                for j in range(self.cols): 
                    if i*self.cols+j >= len(self.routkey):
                        break
                    camera = self.viewType(self)
                    camera.setResultAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)
                    camera.setObjectName(self.routkey[i*self.cols+j])
                    camera.setTitle(self.routkey[i*self.cols+j])
                    self.viewLayout.addWidget(camera,i,j)
                    self.cameras[self.routkey[i*self.cols+j]] = camera

    def setImage(self,key,image):
        self.cameras[key].scene.setImage(image)

    def getCamaeraView(self,key):
        return self.cameras[key]