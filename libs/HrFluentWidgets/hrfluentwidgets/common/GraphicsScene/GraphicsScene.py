from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QPixmap,QKeySequence,QTransform,QCursor
from PySide6.QtWidgets import QGraphicsScene,QFileDialog,QGraphicsPixmapItem,QGraphicsItem
from qfluentwidgets import RoundMenu, Action,MenuAnimationType
from qfluentwidgets import FluentIcon as FIF

class GraphicsScene(QGraphicsScene):
    itemRemoved = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixItem:QGraphicsPixmapItem = None

    def imageItem(self):
        return self.pixItem
    
    def image(self):
        return self.pixItem.pixmap().toImage()
    
    def setImage(self,image):
        if(self.pixItem is not None):
            self.pixItem.setPixmap(QPixmap.fromImage(image))
        else:
            self.pixItem = self.addPixmap(QPixmap.fromImage(image))

    def clearOthers(self):
        delItems = []
        for item in self.items():
            if item != self.pixItem:
                delItems.append(item)
        self.itemRemoved.emit(delItems)
        for item in delItems:
            self.removeItem(item)
        self.views()[0].update()
    
    def clearAll(self):
        self.itemRemoved.emit(self.items())
        self.clear()
        self.pixItem = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.itemRemoved.emit(self.selectedItems())
            for item in self.selectedItems():
                self.removeItem(item)
                del item
        elif event.key() == Qt.Key_Escape:
            self.clearSelection()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_A:
            for item in self.items():
                item.setSelected(True)
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_S:
            self.saveImage()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        if event.modifiers() == Qt.ControlModifier :
            t = self.itemAt(event.scenePos(), QTransform())
            if t is not None and t == self.pixItem:
               self.sceneMenu().exec(QCursor.pos(), aniType=MenuAnimationType.DROP_DOWN)
        return super().contextMenuEvent(event)

    def saveImage(self):
        path,_ = QFileDialog.getSaveFileName(self.parent(),"保存图像","","Images (*.bmp);;(*.jpg);;(*.png);;(*.tiff)")
        if path:
            self.image().save(path)
    
    def sceneMenu(self):
        menu = RoundMenu()
        menu.addAction(Action(FIF.SAVE, self.tr("保存图像"), menu, shortcut=QKeySequence("Ctrl+S"),triggered=self.saveImage))
        return menu

class GraphicsItemScene(GraphicsScene):
    itemFinished = Signal(QGraphicsItem)
    itemChanged = Signal(QGraphicsItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tempItem = None
        self.addItemFunc = None
        self.isEdit = False
        self.continueEdit = True
    
    def setEditMode(self,ret:bool):
        self.isEdit = ret

    def setContinueEditMode(self,ret:bool):
        self.continueEdit = ret

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.addItemFunc is not None and self.isEdit and self.tempItem is None:
                self.tempItem = self.addItemFunc()
                self.tempItem.setPos(event.scenePos())
                self.tempItem.setSelected(True)
                self.addItem(self.tempItem)
                self.tempItem.mousePressEvent(event)
                return
            elif self.tempItem is not None:
                self.tempItem.mousePressEvent(event)
                # self.tempItem.setSelected(False)
                return
        return super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.tempItem is not None and self.isEdit:
            self.tempItem.mouseMoveEvent(event)
            return
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.tempItem is not None and self.tempItem.data(Qt.UserRole+1):
                self.tempItem.mouseReleaseEvent(event)
                self.itemFinished.emit(self.tempItem)
                self.tempItem.setSelected(False)
                self.tempItem = None
                if not self.continueEdit:
                    self.isEdit = False
                return
        return super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        if event.modifiers() == Qt.ControlModifier :
            t = self.itemAt(event.scenePos(), QTransform())
            if t is not None and t == self.pixItem:
                menu = self.sceneMenu()
                menu.exec(QCursor.pos(), aniType=MenuAnimationType.DROP_DOWN)
            else:
                menu = self.sceneMenu()
                menu.addAction(Action(FIF.DELETE, self.tr("删除"), menu, shortcut=QKeySequence("Delete"),triggered=self.clearOthers()))
                menu.exec(QCursor.pos(), aniType=MenuAnimationType.DROP_DOWN)
        return super().contextMenuEvent(event)
    