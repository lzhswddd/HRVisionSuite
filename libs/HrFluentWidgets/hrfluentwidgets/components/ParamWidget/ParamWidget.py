
from PySide6.QtWidgets import QVBoxLayout,QPushButton,QGridLayout,QWidget
from PySide6.QtGui import QColor,QImage
from PySide6.QtCore import Qt,Signal
from qfluentwidgets import HeaderCardWidget,PrimaryPushButton,FluentIconBase,ScrollArea,InfoBar
from ..CameraView import MatchView
from ...common import (ParamItem, GraphicsItemScene,
                       GraphicsRectItem,GraphicsPolygonItem,
                       ParamConfig,RectItemData,PolygonItemData,
                       RotatedRectItemData, GraphicsRotatedRectItem)
from .GraphicsItemData import (
    PolygonItemSupport,
    RectItemSupport, RotatedRectItemSupport
)

USERDATA_KEY = 100

class RecipeParamWidget(HeaderCardWidget):
    def __init__(self,parent=None):
        super().__init__(parent)

        self.setTitle(self.tr("参数设置"))
        self.scrollarea = ScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.paramWidget = QWidget()
        self.scrollarea.setStyleSheet("background-color:transparent; border:none;")

        self.paramItemMap:dict[str,ParamItem] = {}
        self.paramLayout = QVBoxLayout(self.paramWidget)
        self.scrollarea.setWidget(self.paramWidget)

        self.initLayout()

    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)

        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(5)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.viewLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.viewLayout.addWidget(self.scrollarea)

        self.paramLayout.setContentsMargins(12, 12, 12, 12)
        self.paramLayout.setSpacing(5)
        self.paramLayout.setDirection(QVBoxLayout.Direction.TopToBottom)
        self.paramLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
    def addParamItem(self,item:ParamItem):
        item.valueChanged.connect(self.onValueChanged)
        self.paramItemMap[item.key] = item
        self.paramLayout.addWidget(item)

    def updateParam(self):
        for i in range(self.paramLayout.count()):
            self.paramLayout.itemAt(i).widget().updateParam()
            
    def onValueChanged(self,key:str,value:object):
        pass

class RecipeParamWithViewWidget(RecipeParamWidget):
    applySignal = Signal(str,QImage,object)
    def __init__(self,parent=None):

        self.editViewWidget = QWidget()
        self.editViewLayout = QVBoxLayout(self.editViewWidget)

        self.matchView = MatchView(self.editViewWidget)
        self.scene:GraphicsItemScene = None
        
        self.btnList:list[QPushButton]={}
        self.paramSetting:dict[str, ParamConfig] = {}
        self.colorList:QColor = {}
        self.btnLayout = QGridLayout()
        self.currentKey = None

        self.editViewLayout.addWidget(self.matchView)
        self.editViewLayout.addLayout(self.btnLayout)
        self.editViewLayout.setContentsMargins(12, 12, 12,0)
        self.editViewLayout.setSpacing(5)

        
        super().__init__(parent)
        self.viewLayout.insertWidget(0,self.editViewWidget)

    def addEditBtn(self,icon:FluentIconBase,text:str,type,paramSetting:ParamConfig,key:str,Color=Qt.GlobalColor.green):
        btn = PrimaryPushButton(icon,text,self)
        row = len(self.btnList)//4
        col = len(self.btnList)%4
        self.btnLayout.addWidget(btn,row,col)
        self.btnList[key] = btn
        self.paramSetting[key] = paramSetting
        self.colorList[key] = Color
        btn.setProperty("key",key)
        if type == "rect":
            btn.clicked.connect(self.createRect)
        elif type == "rotated_rect":
            btn.clicked.connect(self.createRotatedRect)
        elif type == "polygon":
            btn.clicked.connect(self.createPolygon)

    def addApplyBtn(self,icon:FluentIconBase,text:str,key:str):
        btn = PrimaryPushButton(icon,text,self)
        
        row = (self.btnLayout.count()+1)//4
        col = (self.btnLayout.count()+1)%4
        btn.setProperty("key",key)
        self.btnLayout.addWidget(btn,row,col)
        btn.clicked.connect(self._applyBtnClicked)
    
    def createRect(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        self.currentKey = btn.property("key")
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == self.currentKey:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr("已存在该类型的Roi"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent().parent()
                )
                return
            
        
        self.scene.addItemFunc = lambda: GraphicsRectItem()
        self.scene.setEditMode(True)
        self.scene.setContinueEditMode(False)

    def createRotatedRect(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        self.currentKey = btn.property("key")
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == self.currentKey:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr("已存在该类型的Roi"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent().parent()
                )
                return
            
        self.scene.addItemFunc = lambda: GraphicsRotatedRectItem()
        self.scene.setEditMode(True)
        self.scene.setContinueEditMode(False)

    def createPolygon(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        self.currentKey = btn.property("key")
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == self.currentKey:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr("已存在该类型的Roi"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent().parent()
                )
                return
             
        self.scene.addItemFunc = lambda: GraphicsPolygonItem()
        self.scene.setEditMode(True)
        self.scene.setContinueEditMode(False)

    def setScene(self,scene:GraphicsItemScene):
        self.scene = scene
        self.scene.itemFinished.connect(self._onItemCreated)
    
    def updateGraphicsItem(self):
        if self.scene is None:
            return
        self.scene.clearOthers()
        for key in self.paramSetting:
            item = self.paramSetting[key].getItem(key).value
            if isinstance(item,RotatedRectItemData) and not item.rect.isEmpty():
                rectItem = GraphicsRotatedRectItem()
                rectItem.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,key)
                rectItem.setPenColor(self.colorList[key])
                rectItem.setRect(item.rect)
                rectItem.setDepend(item.depend)
                rectItem.setId(item.id)
                rectItem.setRotation(item.rotation)
                rectItem.setTransformOriginPoint(item.rect.center())
                rectItem.state = 2
                rectItem.itemSizeChanged.connect(self._onItemChanged)
                self.scene.addItem(rectItem)
            
            elif isinstance(item,RectItemData) and not item.rect.isEmpty():
                rectItem = GraphicsRectItem()
                rectItem.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,key)
                rectItem.setPenColor(self.colorList[key])
                rectItem.setRect(item.rect)
                rectItem.setDepend(item.depend)
                rectItem.setId(item.id)
                rectItem.state = 2
                rectItem.itemSizeChanged.connect(self._onItemChanged)
                self.scene.addItem(rectItem)

            elif isinstance(item,PolygonItemData) and not item.polygon.isEmpty():
                polygonItem = GraphicsPolygonItem()
                polygonItem.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,key)
                polygonItem.setPenColor(self.colorList[key])
                polygonItem.setPolygon(item.polygon)
                polygonItem.setDepend(item.depend)
                polygonItem.setId(item.id)
                polygonItem.state = 2
                polygonItem.itemSizeChanged.connect(self._onItemChanged)
                self.scene.addItem(polygonItem)
        
    def _onItemCreated(self,item):
        if isinstance(item,GraphicsRotatedRectItem):
            item.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,self.currentKey)
            item.setPenColor(self.colorList[self.currentKey])
            item.itemSizeChanged.connect(self._onItemChanged)
            
            pixmapItem = self.scene.imageItem()
            saveRect = item.rect().translated(item.pos())
            itemData = RotatedRectItemData(item.id,item.depend,saveRect,item.rotation(),item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)
        
        elif isinstance(item,GraphicsRectItem):
            item.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,self.currentKey)
            item.setPenColor(self.colorList[self.currentKey])
            item.itemSizeChanged.connect(self._onItemChanged)
            
            pixmapItem = self.scene.imageItem()
            saveRect = pixmapItem.mapRectFromItem(item,item.rect())
            itemData = RectItemData(item.id,item.depend,saveRect,item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)
        
        elif isinstance(item,GraphicsPolygonItem):
            item.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,self.currentKey)
            item.setPenColor(self.colorList[self.currentKey])
            item.itemSizeChanged.connect(self._onItemChanged)
            
            pixmapItem = self.scene.imageItem()
            polygon = pixmapItem.mapFromItem(item,item.polygon())
            itemData = PolygonItemData(item.id,item.depend,polygon,item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)
   
    def _onItemChanged(self,change):
        item = self.sender()
        if item is None:
            return
        if isinstance(item,GraphicsRotatedRectItem):
            pixmapItem = self.scene.imageItem()
            saveRect = item.rect().translated(item.pos())
            itemData = RotatedRectItemData(item.id,item.depend,saveRect,item.rotation(),item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)
        
        elif isinstance(item,GraphicsRectItem):
            pixmapItem = self.scene.imageItem()
            saveRect = pixmapItem.mapRectFromItem(item,change)
            itemData = RectItemData(item.id,item.depend,saveRect,item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)

        elif isinstance(item,GraphicsPolygonItem):
            pixmapItem = self.scene.imageItem()
            polygon = pixmapItem.mapFromItem(item,change)
            itemData = PolygonItemData(item.id,item.depend,polygon,item.penColor)
            self.paramSetting[item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)].set(item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY),itemData)
            
    def _applyBtnClicked(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        key = btn.property("key")
        data = None
        
        pixmapItem = self.scene.imageItem()
        if pixmapItem is None:
            return
        img = pixmapItem.pixmap().toImage()
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == key:
                if isinstance(item,GraphicsRotatedRectItem):
                    roi = pixmapItem.mapFromItem(item,item.rect())
                    data = roi
                
                elif isinstance(item,GraphicsRectItem):
                    roi = pixmapItem.mapRectFromItem(item,item.rect())
                    data = roi

                elif isinstance(item,GraphicsPolygonItem):
                    roi = pixmapItem.mapFromItem(item,item.polygon())
                    data = roi
                    
                break
                    
        self.applySignal.emit(key,img,data)

    def updateMatchViewImage(self,img:QImage):
        self.matchView.scene.setImage(img)
        self.matchView.fitView()
        
    def setItemUserData(self, key:str, data:object):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == key:
                if isinstance(item,GraphicsRotatedRectItem) and isinstance(data,RotatedRectItemData):
                    RotatedRectItemSupport.setData(item, data)
                elif isinstance(item,GraphicsRectItem) and isinstance(data,RectItemData):
                    RectItemSupport.setData(item, data)
                elif isinstance(item,GraphicsPolygonItem) and isinstance(data,PolygonItemData):
                    PolygonItemSupport.setData(item, data)
                item.update()
