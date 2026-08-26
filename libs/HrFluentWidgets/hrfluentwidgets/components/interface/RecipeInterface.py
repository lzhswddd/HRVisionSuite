
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QHBoxLayout,QWidget,QVBoxLayout,QStackedWidget,QGraphicsScene
from qfluentwidgets import ComboBox,HeaderCardWidget,ComboBox, CardWidget
from ..CameraView import CameraEditView
from ..ParamWidget import RecipeParamWidget,RecipeParamWithViewWidget
from ...common import RecipeManager,param_cfg
from .SettingConfig import setting_cfg
from ...common import GraphicsCrossItem

class RecipeInterface(QWidget):
    loadRecipeFinished = Signal(Path)
    def __init__(self,recipePath,parent=None):
        super().__init__(parent)
        self.recipePath = recipePath
        self.headerWidget = HeaderCardWidget(self.tr("相机列表"),self)
        self.recipeManager = RecipeManager(recipePath,self)
        self.cameraStackeds = QStackedWidget(self)
        self.paramStackeds = QStackedWidget(self)
        self.pivot = ComboBox(self)

        self.initLayout()
        self.initConnect()

    def initLayout(self):
        self.headerWidget.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerWidget.headerView.setFixedHeight(32)
        self.headerWidget.viewLayout.setContentsMargins(12, 12, 12, 12)
        self.headerWidget.viewLayout.addWidget(self.pivot)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(5)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.addWidget(self.recipeManager)
        self.vlayout.addWidget(self.headerWidget)
        self.vlayout.addWidget(self.paramStackeds)

        self.hlayout = QHBoxLayout(self)
        self.hlayout.setSpacing(5)
        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.hlayout.addWidget(self.cameraStackeds)
        self.hlayout.addLayout(self.vlayout)
        self.hlayout.setStretchFactor(self.cameraStackeds, 8)
        self.hlayout.setStretchFactor(self.vlayout, 2)

    def initConnect(self):
        self.pivot.currentTextChanged.connect(self.__onPivotChanged)
        self.recipeManager.loadRecipeSignal.connect(self.__onLoadRecipe)

    def setRecipePath(self,recipePath):
        self.recipePath = recipePath
        
    def addCamera(self,cameraName:str,paramWidget:RecipeParamWidget=None):
        self.pivot.addItem(cameraName)
        widget = CameraEditView(self.cameraStackeds)
        widget.setTitle(cameraName)
        widget.setObjectName(cameraName)
        self.cameraStackeds.addWidget(widget)
        if paramWidget:
            paramWidget.setObjectName(cameraName)
            paramWidget.setParent(self.paramStackeds)
            self.paramStackeds.addWidget(paramWidget)

            if getattr(paramWidget, "setScene", None):
                paramWidget.setScene(widget.scene)

    def updateImage(self,cameraName:str,image:QImage):
        camera_widget = self.cameraStackeds.findChild(QWidget, cameraName)
        if camera_widget:
            camera_widget.scene.setImage(image)

    def __onPivotChanged(self,k):
        camera_widget = self.cameraStackeds.findChild(QWidget, k)
        param_widget = self.paramStackeds.findChild(QWidget, k)
        if camera_widget:
            self.cameraStackeds.setCurrentWidget(camera_widget)
            
        if param_widget:
            self.paramStackeds.setCurrentWidget(param_widget)

    def __onLoadRecipe(self):
        for index in range(self.cameraStackeds.count()):
            widget = self.cameraStackeds.widget(index)
            if isinstance(widget,CameraEditView):
                widget.scene.clearOthers()
                
        #获取工单路径
        path = self.recipeManager.currentRecipePath()
        param_cfg.clear()
        #加载参数配置
        param_cfg.load(path/"param.json")

        #更新参数配置
        for index in range(self.paramStackeds.count()):
            widget = self.paramStackeds.widget(index)
            if getattr(widget, 'updateGraphicsItem', None):
                widget.updateGraphicsItem()
            if getattr(widget, 'updateParam', None):
                widget.updateParam()
        
        self.loadRecipeFinished.emit(self.recipeManager.currentRecipePath())
                
class RecipeMatchInterface(RecipeInterface):
    def __init__(self,recipePath,parent=None):
        super().__init__(recipePath,parent)
    
    def updateMatchResult(self,cameraName:str,matchResult:list[tuple[float,float,bool]]):
        self.clearMatchResult(cameraName)
        widget = self.cameraStackeds.findChild(CameraEditView, cameraName)
        for i in range(len(matchResult)):
            item = GraphicsCrossItem()
            item.penColor = Qt.GlobalColor.green if matchResult[i][2] else Qt.GlobalColor.red
            item.setData(Qt.ItemDataRole.UserRole + 10, "MatchResult")
            item.setPos(matchResult[i][0],matchResult[i][1])
            widget.scene.addItem(item)

    def clearMatchResult(self,cameraName:str):
        widget = self.cameraStackeds.findChild(CameraEditView, cameraName)
        for item in widget.scene.items():
            if isinstance(item,GraphicsCrossItem):
                if item.data(Qt.ItemDataRole.UserRole + 10) == "MatchResult":
                    widget.scene.removeItem(item)
                    del item
        widget.scene.update()
        
class RecipeWithItemInterface(RecipeInterface):
    addResultItemSignal = Signal(str,QGraphicsScene,object)
    clearResultItemSignal = Signal(str,QGraphicsScene)
    
    def __init__(self,recipePath,parent=None):
        super().__init__(recipePath,parent)
        
    def updateResult(self,cameraName:str,result:object):
        self.clearMatchResult(cameraName)
        widget = self.cameraStackeds.findChild(CameraEditView, cameraName)
        if widget:
            self.addResultItemSignal.emit(cameraName,widget.scene,result)

    def clearMatchResult(self,cameraName:str):
        widget = self.cameraStackeds.findChild(CameraEditView, cameraName)
        if widget:
            self.clearResultItemSignal.emit(cameraName,widget.scene)
            widget.scene.update()
                    