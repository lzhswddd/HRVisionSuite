from typing import Callable
from PySide6.QtWidgets import QVBoxLayout,QPushButton,QGridLayout,QWidget,QGraphicsItem
from PySide6.QtGui import QColor,QPolygonF,QImage
from PySide6.QtCore import Qt,Signal
from qfluentwidgets import HeaderCardWidget,PrimaryPushButton,FluentIconBase,ConfigItem,InfoBar
from .ParamWidget import RecipeParamWidget, USERDATA_KEY
from .GraphicsItemData import SupportBase
from ...common import (GraphicsItemScene, ParamConfig)
from ..CameraView import MatchView
import inspect

class RecipeUserItemParamWidget(RecipeParamWidget):
    applySignal = Signal(str,QImage)
    def __init__(self,parent=None):
        super().__init__(parent)
        
        self.editViewWidget = QWidget()
        self.editViewLayout = QVBoxLayout(self.editViewWidget)

        self.scene:GraphicsItemScene = None
        
        self.btnList:dict[QPushButton]={}
        self.paramSetting:dict[str, ParamConfig] = {}
        self.colorList:QColor = {}
        self.btnLayout = QGridLayout()
        
        self.editViewLayout.addLayout(self.btnLayout)
        self.editViewLayout.setContentsMargins(12, 12, 12,0)
        self.editViewLayout.setSpacing(5)
        
        self.viewLayout.insertWidget(0,self.editViewWidget)
        self.btnMaxColumn = 4
        
        self.btnFactory = {}
        self.itemFactory = {}
        self.itemDataSupport = {}
        
    def addItemType(self, itemType:str, factory:Callable[[], QGraphicsItem], support:SupportBase):
        self.itemFactory[itemType] = factory
        self.itemDataSupport[itemType] = support
        
    def addEditBtn(self,icon:FluentIconBase,text:str,type,paramSetting:ParamConfig,key:str,Color=Qt.GlobalColor.green,row:int=-1,col:int=-1):
        btn = PrimaryPushButton(icon,text,self)
        if row < 0:
            row = len(self.btnList)//self.btnMaxColumn
        if col < 0:
            col = len(self.btnList)%self.btnMaxColumn
        self.btnLayout.addWidget(btn,row,col)
        self.btnList[key] = btn
        self.paramSetting[key] = paramSetting
        self.colorList[key] = Color
        btn.setProperty("key", key)
        if type in self.itemFactory:
            self.btnFactory[key] = type
        btn.clicked.connect(self.createItem)

    def addApplyBtn(self,icon:FluentIconBase,text:str,key:str,row:int=-1,col:int=-1):
        btn = PrimaryPushButton(icon,text,self)
        if row < 0:
            row = self.btnLayout.count()//self.btnMaxColumn
        if col < 0:
            col = self.btnLayout.count()%self.btnMaxColumn
        btn.setProperty("key", key)
        self.btnLayout.addWidget(btn,row,col)
        btn.clicked.connect(self._applyBtnClicked)
    
    def _applyBtnClicked(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        key = btn.property("key")
        
        pixmapItem = self.scene.imageItem()
        if pixmapItem is None:
            return
        img = pixmapItem.pixmap().toImage()
        self.applySignal.emit(key,img)
    
    def createItem(self):
        if self.scene is None:
            return
        
        btn = self.sender()
        currentKey = btn.property("key")
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == currentKey:
                InfoBar.warning(
                    title=self.tr("警告"),
                    content=self.tr("已存在该类型的Roi"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent().parent()
                )
                return
        
        if currentKey in self.btnFactory:
            def wapper(key):
                def inner():
                    item = self.itemFactory[self.btnFactory[key]]()
                    item.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,key)
                    item.setPenColor(self.colorList[key])
                    return item
                return inner
                
            self.scene.addItemFunc = wapper(currentKey)
            self.scene.setEditMode(True)
            self.scene.setContinueEditMode(False)
        else:
            InfoBar.warning(
                title=self.tr("警告"),
                content=self.tr("未找到对应的Roi类型"),
                orient=Qt.Orientation.Horizontal,
                duration=5000,
                parent=self.parent().parent()
            )

    def setScene(self,scene:GraphicsItemScene):
        self.scene = scene
        if getattr(scene, 'itemFinished', None):
            scene.itemFinished.connect(self._onItemCreated)
        if getattr(scene, 'itemRemoved', None):
            scene.itemRemoved.connect(self._onItemRemoved)
        
    
    def updateGraphicsItem(self):
        if self.scene is None:
            return
        self.scene.clearOthers()
        for key in self.paramSetting:
            item = self.paramSetting[key].getItem(key)
            if item is None or not item.validator.validate(item.value):
                continue
            
            itemType = self.btnFactory.get(key, None)
            if itemType is None:
                continue
            factory = self.itemFactory.get(itemType, None)
            support:SupportBase = self.itemDataSupport.get(itemType, None)
            if factory is None or support is None:
                continue
            itemData = item.value
            if itemData is None:
                continue
            
            graphicsItem = factory()
            support.setData(graphicsItem, itemData)
            support.connectSignals(graphicsItem, self._onItemChanged)
                
            graphicsItem.setData(Qt.ItemDataRole.UserRole+USERDATA_KEY,key)
            graphicsItem.setPenColor(self.colorList[key])
            graphicsItem.state = 2
            
            self.scene.addItem(graphicsItem)
            if key in self.paramItemMap:
                self.paramItemMap[key].triggerValueChanged()
                
    def _onItemCreated(self, item:QGraphicsItem):
        if self.scene is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)
        if key is None or key == "":
            return
        if key in self.paramItemMap:
            self.paramItemMap[key].triggerValueChanged()
        itemType = self.btnFactory.get(key, None)
        support:SupportBase = self.itemDataSupport.get(itemType, None)    
        if support is not None:
            data = support.genData(item=item, targetItem=self.scene.imageItem())
            self.paramSetting[key].getItem(key).blockSignals(True)
            self.paramSetting[key].set(key,data)
            self.paramSetting[key].getItem(key).blockSignals(False)
            support.connectSignals(item, self._onItemChanged)
        
    def _onItemChanged(self, change):
        item = self.sender()
        if item is None:
            return
        
        key = item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)
        if key is None or key == "":
            return
        
        itemType = self.btnFactory.get(key, None)
        support:SupportBase = self.itemDataSupport.get(itemType, None)    
        if support is not None:
            data = support.genData(item=item, targetItem=self.scene.imageItem())
            self.paramSetting[key].getItem(key).blockSignals(True)
            self.paramSetting[key].set(key,data)
            self.paramSetting[key].getItem(key).blockSignals(False)

    def _onItemRemoved(self, items:list[QGraphicsItem]):
        if self.scene is None:
            return
        # Get the current stack frame
        stack = inspect.stack()
        # Check the previous function in the call stack
        if len(stack) > 1:
            previous_function = stack[1].function
            if previous_function == "keyPressEvent":
                for item in items:
                    key = item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY)
                    if key is None or key == "":
                        continue
                    if key in self.paramSetting:
                        self.paramSetting[key].set(key, None)

    def onValueChanged(self, key:str, value):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == key:
                itemType = self.btnFactory.get(key, None)
                support:SupportBase = self.itemDataSupport.get(itemType, None)    
                if support is not None:
                    item.blockSignals(True)
                    support.setData(item, value)
                    item.blockSignals(False)
                    
                    self.paramSetting[key].getItem(key).blockSignals(True)
                    self.paramSetting[key].set(key,support.genData(item=item, targetItem=self.scene.imageItem()))
                    self.paramSetting[key].getItem(key).blockSignals(False)
                    
                    item.update()
                    break

    def setItemUserData(self, key:str, data:object):
        for item in self.scene.items():
            if item.data(Qt.ItemDataRole.UserRole+USERDATA_KEY) == key:
                itemType = self.btnFactory.get(key, None)
                support:SupportBase = self.itemDataSupport.get(itemType, None)    
                if support is not None:
                    item.blockSignals(True)
                    support.setData(item, data)
                    item.blockSignals(False)
                    
                    self.paramSetting[key].getItem(key).blockSignals(True)
                    self.paramSetting[key].set(key,support.genData(item=item, targetItem=self.scene.imageItem()))
                    self.paramSetting[key].getItem(key).blockSignals(False)
                    item.update()
                    break

class RecipeUserItemWithViewParamWidget(RecipeUserItemParamWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.matchView = MatchView(self.editViewWidget)
        self.editViewLayout.insertWidget(0, self.matchView)
    
    def updateMatchViewImage(self,img:QImage):
        self.matchView.scene.setImage(img)
        self.matchView.fitView()
        