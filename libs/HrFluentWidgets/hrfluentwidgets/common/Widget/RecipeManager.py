

from PySide6.QtCore import Qt, Signal,QFileSystemWatcher
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy
from qfluentwidgets import (
    FluentIcon as FIF,
    MessageBoxBase,
    SubtitleLabel,
    HeaderCardWidget,
    BodyLabel,
    CaptionLabel,
    LineEdit,
    ComboBox,
    PrimaryPushButton,
    InfoBar,
    InfoBarPosition,
)
from pathlib import Path
import shutil
import zipfile as zip

class NewRecipeDialog(MessageBoxBase):
    def __init__(self,recipePath,parent=None):
        super().__init__(parent)
        self.recipePath = recipePath
        self.titleLabel = SubtitleLabel(self.tr("新建工单"),self)
        self.recipeNameEdit = LineEdit(self)
        self.warningLabel = CaptionLabel(self)
        
        self.recipeNameEdit.setPlaceholderText(self.tr("请输入新建工单名称"))
        self.recipeNameEdit.setMinimumWidth(200)
        self.recipeNameEdit.setClearButtonEnabled(True)
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))

        self.yesButton.setText(self.tr("新建"))
        self.cancelButton.setText(self.tr("取消"))

        self.initLayout()
        
    def initLayout(self):
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.recipeNameEdit)
        self.viewLayout.addWidget(self.warningLabel)
        self.warningLabel.hide()

    def validate(self):
        if not self.recipeNameEdit.text():
            self.warningLabel.setText(self.tr("请输入工单名称"))
            self.warningLabel.setHidden(False)
            self.recipeNameEdit.setError(True)
            return False
        file_path = Path(self.recipePath) / f"{self.recipeNameEdit.text()}.zip"
        # file_path.touch(exist_ok=True)
        # ret =  (Path(self.recipePath)/self.recipeNameEdit.text()+".json").exists()
        if file_path.exists():
            self.warningLabel.setText(self.tr("该名称的工单已存在"))
            self.warningLabel.setHidden(False)
            self.recipeNameEdit.setError(True)
            return False
        return True

class CopyRecipeDialog(NewRecipeDialog):
    def __init__(self,recipePath,parent=None):
        super().__init__(recipePath,parent)
        self.titleLabel.setText(self.tr("复制工单"))
        self.recipeList = ComboBox(self)
        self.recipeList.setMinimumWidth(200)
        self.recipeNameEdit.setPlaceholderText(self.tr("请输入复制后工单名称"))
        self.recipeNameEdit.setMinimumWidth(200)
        self.viewLayout.insertWidget(1,CaptionLabel(self.tr("旧工单")),0,Qt.AlignmentFlag.AlignLeft)
        self.viewLayout.insertWidget(2,self.recipeList,0,Qt.AlignmentFlag.AlignLeft)
        self.viewLayout.insertWidget(3,CaptionLabel(self.tr("新工单")),0,Qt.AlignmentFlag.AlignLeft)
        self.yesButton.setText(self.tr("复制"))
        self.oldRecipe = None

        #更新工单列表
        for file in Path(self.recipePath).iterdir():
            if file.is_file() and file.suffix == ".zip":
                self.recipeList.addItem(file.stem)

        
    #     self.recipeList.currentTextChanged.connect(self.__onTextChanged)

    # def __onTextChanged(self,text):
    #     self.oldRecipe = text
    def validate(self):
        if super().validate():
            if not self.recipeList.currentText():
                self.warningLabel.setText(self.tr("请选择旧工单"))
                self.warningLabel.setHidden(False)
                self.recipeList.setError(True)
                return False
            else:
                self.oldRecipe = self.recipeList.currentText()
                return True
        return False

class SaveAsRecipeDialog(NewRecipeDialog):
    def __init__(self,recipePath,parent=None):
        super().__init__(recipePath,parent)
        self.titleLabel.setText(self.tr("另存为..."))
        self.recipeNameEdit.setPlaceholderText(self.tr("请输入另存为后工单名称"))

        self.yesButton.setText(self.tr("另存为"))
        self.cancelButton.setText(self.tr("取消"))

class DeleteRecipeDialog(MessageBoxBase):
    def __init__(self,recipePath,parent=None):
        super().__init__(parent)
        self.recipePath = recipePath
        self.titleLabel = SubtitleLabel(self.tr("删除工单..."),self)
        self.recipeList = ComboBox(self)
        self.recipeList.setMinimumWidth(200)
        self.warningLabel = CaptionLabel(self)
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))

         #更新工单列表
        for file in Path(self.recipePath).iterdir():
            if file.is_file() and file.suffix == ".zip":
                self.recipeList.addItem(file.stem)

        self.yesButton.setText(self.tr("删除"))
        self.cancelButton.setText(self.tr("取消"))

        self.initLayout()
        

    def initLayout(self):
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(CaptionLabel(self.tr("请选择要删除的工单：")))
        self.viewLayout.addWidget(self.recipeList)
        self.viewLayout.addWidget(self.warningLabel)
        self.warningLabel.hide()

    def validate(self):
        if not self.recipeList.currentText():
            self.warningLabel.setText(self.tr("请选择要删除的工单"))
            self.warningLabel.setHidden(False)
            return False
        # file_path = Path(self.recipePath) / f"{self.recipeList.currentText()}.zip"
        # # if not file_path.exists():
        # #     self.warningLabel.setText(self.tr("该名称的工单不存在"))
        # #     self.warningLabel.setHidden(False)
        # #     return False
        return True

class RecipeManager(HeaderCardWidget):
    loadRecipeSignal = Signal(str)  # Define the signal
    saveRecipeSignal = Signal(str)  # Define the signal
    saveAsRecipeSignal = Signal(str)  # Define the signal
    copyRecipeSignal = Signal(str,str)  # Define the signal
    deleteRecipeSignal = Signal(str)  # Define the signal
    newRecipeSignal = Signal(str)  # Define the signal

    def __init__(self,recipePath,parent=None):
        super().__init__(parent)
        self.setTitle(self.tr("工单管理"))
        self.recipePath = recipePath
        self.currentRecipeName = BodyLabel(self.tr("-----"))
        self.recipeList = ComboBox(self)
        self.newRecipeBtn = PrimaryPushButton(FIF.ADD,self.tr("新建"),self)
        self.copyRecipeBtn = PrimaryPushButton(FIF.COPY,self.tr("复制"),self)
        self.deleteRecipeBtn = PrimaryPushButton(FIF.DELETE,self.tr("删除"),self)
        self.loadRecipeBtn = PrimaryPushButton(FIF.UPDATE,self.tr("加载"),self)
        self.saveRecipeBtn = PrimaryPushButton(FIF.SAVE,self.tr("保存"),self)
        self.saveAsRecipeBtn = PrimaryPushButton(FIF.SAVE_AS,self.tr("另存为"),self)

        self.recipeList.setPlaceholderText(self.tr("请选择工单"))
        self.recipeList.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)

        self.watcher = QFileSystemWatcher([self.recipePath],self)


        self._currentRecipePath = None  # 新增实例变量存储临时目录
        #更新工单列表
        for file in Path(self.recipePath).iterdir():
            if file.is_file() and file.suffix == ".zip":
                self.recipeList.addItem(file.stem)

        self.initLayout()
        self.initConnect()
    
    def __del__(self):
        self.watcher.removePath(self.recipePath)

    def initLayout(self):
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)
        self.viewLayout.setContentsMargins(12, 12, 12, 12)
        self.viewLayout.setDirection(QVBoxLayout.Direction.TopToBottom)

        self.currentRecipeName.setMinimumWidth(150)
        self.recipeList.setMinimumWidth(150)
        
    
        hlayout = QHBoxLayout()
        hlayout.setSpacing(10)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(CaptionLabel(self.tr("当前工单：")),0,Qt.AlignmentFlag.AlignLeft)
        hlayout.addWidget(self.currentRecipeName,1,Qt.AlignmentFlag.AlignLeft)
        hlayout.addWidget(self.newRecipeBtn)
        self.viewLayout.addLayout(hlayout)

        hlayout = QHBoxLayout()
        hlayout.setSpacing(10)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(CaptionLabel(self.tr("工单列表：")),0,Qt.AlignmentFlag.AlignLeft)
        hlayout.addWidget(self.recipeList,3,Qt.AlignmentFlag.AlignLeft)
        hlayout.addWidget(self.copyRecipeBtn)
        self.viewLayout.addLayout(hlayout)

        hlayout = QHBoxLayout()
        hlayout.setSpacing(3)
        hlayout.setContentsMargins(0, 0, 0, 0)
        # hlayout.addWidget(self.newRecipeBtn)
        # hlayout.addWidget(self.copyRecipeBtn)
        hlayout.addWidget(self.deleteRecipeBtn)
        hlayout.addWidget(self.loadRecipeBtn)
        hlayout.addWidget(self.saveRecipeBtn)
        hlayout.addWidget(self.saveAsRecipeBtn)
        self.viewLayout.addLayout(hlayout)

    def initConnect(self):
        self.newRecipeBtn.clicked.connect(self.__onNewRecipe)
        self.copyRecipeBtn.clicked.connect(self.__onCopyRecipe)
        self.deleteRecipeBtn.clicked.connect(self.__onDeleteRecipe)
        self.loadRecipeBtn.clicked.connect(self.__onLoadRecipe)
        self.saveRecipeBtn.clicked.connect(self.__onSaveRecipe)
        self.saveAsRecipeBtn.clicked.connect(self.__onSaveAsRecipe)
        self.watcher.directoryChanged.connect(self.__onDirChanged)
    
    def currentRecipePath(self):
        return self._currentRecipePath
    
    def __onNewRecipe(self):
        dialog = NewRecipeDialog(self.recipePath,self.parent())
        if dialog.exec():
            file_path = Path(self.recipePath) / f"{dialog.recipeNameEdit.text()}.zip"
            with zip.ZipFile(file_path, 'w'):
                pass  # 不添加任何文件
            self.newRecipeSignal.emit(dialog.recipeNameEdit.text())
            InfoBar.success(
                title=self.tr("成功"),
                content=self.tr(f"{dialog.recipeNameEdit.text()}工单创建成功"),
                orient=Qt.Orientation.Horizontal,
                duration=5000,
                parent=self.parent()
            )
            # file_path.touch()
            # (Path(self.recipePath) /dialog.recipeNameEdit.text()+".json").touch()

    def __onCopyRecipe(self):
        dialog = CopyRecipeDialog(self.recipePath,self.parent())
        if dialog.exec():
            old_path = Path(self.recipePath) / f"{dialog.oldRecipe}.zip"
            new_path = Path(self.recipePath) / f"{dialog.recipeNameEdit.text()}.zip"
            try:
                # 使用 shutil 实现文件复制
                import shutil
                shutil.copyfile(old_path, new_path)
                self.copyRecipeSignal.emit(dialog.oldRecipe,dialog.recipeNameEdit.text())
                InfoBar.success(
                    title=self.tr("成功"),
                    content=self.tr(f"{dialog.oldRecipe}工单复制成功"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent()
                )
            except Exception as e:
                # 异常处理
                InfoBar.error(
                    title=self.tr("复制失败"),
                    content=f"{self.tr('工单复制失败')}: {str(e)}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=5000,
                    parent=self.parent()
                )

    def __onDeleteRecipe(self):
        dialog = DeleteRecipeDialog(self.recipePath,self.parent())
        if dialog.exec():
            file_path = Path(self.recipePath) / f"{dialog.recipeList.currentText()}.zip"
            try:
                # 使用 shutil 实现文件复制
                file_path.unlink(missing_ok=True)
                self.deleteRecipeSignal.emit(dialog.recipeList.currentText())
                InfoBar.success(
                    title=self.tr("成功"),
                    content=self.tr(f"{dialog.recipeList.currentText()}工单删除成功"),
                    orient=Qt.Orientation.Horizontal, 
                    duration=5000,
                    parent=self.parent()
                )
            except Exception as e:    
                # 异常处理
                InfoBar.error(
                    title=self.tr("删除失败"),
                    content=f"{self.tr('工单删除失败')}: {str(e)}",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=5000,
                    parent=self.parent()
                )
    
    def __onLoadRecipe(self):
        selected = self.recipeList.currentText()
        if not selected:
            return
        
        target_path = Path(self.recipePath) / f"{selected}.zip"
        current_path = Path(self.recipePath) / "current" 
        
        try:
            if current_path.exists():
                shutil.rmtree(current_path)  # 删除整个目录
            current_path.mkdir(parents=True, exist_ok=True)

            with zip.ZipFile(target_path) as zf:
                bad = zf.testzip()
                if bad:
                    InfoBar.error(
                        title=self.tr("错误"), 
                        content=f"{self.tr('工单文件损坏')}: {bad}",
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=5000,
                        parent=self.parent()
                    )
                    return
                
                zf.extractall(current_path)
                self._currentRecipePath = current_path
                self.loadRecipeSignal.emit(selected)
                self.currentRecipeName.setText(selected)
                

                InfoBar.success(
                    title=self.tr("成功"),
                    content=self.tr("工单加载成功"),
                    orient=Qt.Orientation.Horizontal, 
                    parent=self.parent()
                )

        except Exception as e:
            InfoBar.error(
                title=self.tr("错误"),
                content=f"{self.tr('加载工单失败')}: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000,
                parent=self.parent()
            )
                 
    def __onSaveRecipe(self):
        currentRecipe= self.currentRecipeName.text()
        if currentRecipe == "-----":
            return
        
        try:
            file_path = Path(self.recipePath) / f"{currentRecipe}.zip"
            with zip.ZipFile(file_path, 'w') as zf:
                for file in Path(self.recipePath+"/current").iterdir():
                    if file.is_file():
                        zf.write(file, file.name)
            self.saveRecipeSignal.emit(currentRecipe)
            InfoBar.success(
                title=self.tr("成功"),
                content=self.tr(f"{self.currentRecipeName.text()}工单保存成功"),
                orient=Qt.Orientation.Horizontal,
                duration=5000,
                parent=self.parent()
            )
        except Exception as e:
            InfoBar.error(
                title=self.tr("错误"),
                content=f"{self.tr('保存工单失败')}: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=5000, 
                parent=self.parent()
            )
    
    def __onSaveAsRecipe(self):
        currentRecipe= self.currentRecipeName.text()
        if currentRecipe == "-----":
            return
        dialog = SaveAsRecipeDialog(self.recipePath,self.parent())
        if dialog.exec():
            try:
                file_path = Path(self.recipePath) / f"{dialog.recipeNameEdit.text()}.zip"
                with zip.ZipFile(file_path, 'w') as zf:
                    for file in Path(self.recipePath+"/current").iterdir():
                        if file.is_file():
                            zf.write(file, file.name)
                self.saveAsRecipeSignal.emit(dialog.recipeNameEdit.text())
                InfoBar.success(
                    title=self.tr("成功"),
                    content=self.tr(f"{dialog.recipeNameEdit.text()}工单另存为成功"),
                    orient=Qt.Orientation.Horizontal,
                    duration=5000,
                    parent=self.parent()
                )
            except Exception as e:
                InfoBar.error(
                    title=self.tr("错误"),
                    content=f"{self.tr('另存为工单失败')}: {str(e)}",
                    orient=Qt.Orientation.Horizontal,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=5000,
                    parent=self.parent()
                )

    def __onDirChanged(self):
        self.recipeList.clear()
        for file in Path(self.recipePath).iterdir():
            if file.is_file() and file.suffix == ".zip":
                self.recipeList.addItem(file.stem)