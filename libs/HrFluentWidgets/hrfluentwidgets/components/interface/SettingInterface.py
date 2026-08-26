from qfluentwidgets import (SettingCardGroup, SwitchSettingCard,OptionsConfigItem,OptionsValidator,
                            OptionsSettingCard, ComboBoxSettingCard,ScrollArea,ExpandLayout,InfoBar,
                            PushSettingCard, FluentIcon as FIF)
from PySide6.QtWidgets import QWidget, QLabel, QFileDialog
from PySide6.QtCore import Qt
from .SettingConfig import SettingConfig, setting_cfg
from .Style_Sheet import StyleSheet
from ...common import IpSettingCard

class SettingInterface(ScrollArea):
    def __init__(self, setting_cfg:SettingConfig=setting_cfg, parent=None):
        super().__init__(parent)

        self.setting_cfg = setting_cfg
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.scrollWidget.setMaximumWidth(800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.settingLabel = QLabel(self.tr("设置"), self)
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')
        self.setObjectName('settingInterface')
        StyleSheet.SETTING_INTERFACE.apply(self)

        self.ioWatchWidgetType:type = None
        self.ioWatchWidget = None
        self.ioOptionWidgetType:type = None
        self.ioOptionWidget = None
        self.motion = None
        self.inputConfig = None
        self.outputConfig = None

        self.initGroups()
        self.initCards()
        self.initLayout()
        self.initConnect()

        self.plcGroup.hide()

    def initGroups(self):
        self.visionGroup = SettingCardGroup(self.tr("视觉设置"), self.scrollWidget)
        self.plcGroup = SettingCardGroup(self.tr("PLC设置"), self.scrollWidget)
        self.motionGroup = SettingCardGroup(self.tr("轴卡设置"), self.scrollWidget)
        self.solfwareGroup = SettingCardGroup(self.tr("软件设置"), self.scrollWidget)
    
    def initCards(self):
        self.savePathCard = PushSettingCard(
            self.tr("选择路径"),
            FIF.FOLDER_ADD,
            self.tr("选择图片存储路径"),
            self.setting_cfg.get(self.setting_cfg.imageSavePath),
            self.visionGroup
        )

        self.saveSourceImageCard = SwitchSettingCard(
            FIF.IMAGE_EXPORT,
            self.tr("原图存储"),
            self.tr("将会保存相机原始图像到存储路径"),
            self.setting_cfg.sourceImageSaveChecked,
            parent=self.visionGroup
        )

        #标定存储路径
        self.saveCalibrationPathCard = PushSettingCard(
            self.tr("选择路径"),
            FIF.FOLDER_ADD,
            self.tr("选择标定文件存储路径"),
            self.setting_cfg.get(self.setting_cfg.calibrationPath),
            self.visionGroup
        )

        #工单存储路径
        self.saveRecipePathCard = PushSettingCard(
            self.tr("选择路径"),
            FIF.FOLDER_ADD,
            self.tr("选择工单文件存储路径"),
            self.setting_cfg.get(self.setting_cfg.recipePath),
            self.visionGroup
        )

        self.languageCard = ComboBoxSettingCard(
            self.setting_cfg.language,
            icon=FIF.LANGUAGE,
            title=self.tr('语言'),
            content=self.tr('选择界面所使用的语言'),
            texts=['简体中文', '繁體中文', 'English', self.tr('跟随系统设置')],
            parent=self.solfwareGroup
        )

        self.autoStartCard = SwitchSettingCard(
            FIF.UPDATE,
            self.tr("开机自启动"),
            self.tr("在开机时自动启动软件"), 
            configItem=self.setting_cfg.autoStart,
            parent = self.solfwareGroup
        )

        self.ioStatausCard = PushSettingCard(
            self.tr("查看"),
            FIF.INFO,
            self.tr("输入IO"),
            self.tr("查看当前io输入状态"),
        )

        self.ioOutputCard = PushSettingCard(
            self.tr("操作"),
            FIF.DEVELOPER_TOOLS,
            self.tr("输出IO"), 
            self.tr("手动操作io输出状态"),
        )

        self.plcIpCard =IpSettingCard(
            self.setting_cfg.plcIp,
            FIF.GLOBE,
            self.tr("PLC IP"),
            self.tr("设置PLC的IP地址"),
            self.setting_cfg.get(self.setting_cfg.plcIp),
            parent=self.plcGroup
        )

        self.plcAddressCard = PushSettingCard(
            self.tr("配置"),
            FIF.CODE,
            self.tr("通信地址"),
            self.tr("配置PLC通信地址表"),
        )

    def initLayout(self):
        self.settingLabel.move(36, 30)
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
   
        self.expandLayout.addWidget(self.visionGroup)
        self.expandLayout.addWidget(self.plcGroup)
        self.expandLayout.addWidget(self.motionGroup)
        self.expandLayout.addWidget(self.solfwareGroup)

        self.visionGroup.addSettingCard(self.savePathCard)
        self.visionGroup.addSettingCard(self.saveSourceImageCard)
        self.visionGroup.addSettingCard(self.saveCalibrationPathCard)
        self.visionGroup.addSettingCard(self.saveRecipePathCard)

        self.plcGroup.addSettingCard(self.plcIpCard)
        self.plcGroup.addSettingCard(self.plcAddressCard)

        self.motionGroup.addSettingCard(self.ioStatausCard)
        self.motionGroup.addSettingCard(self.ioOutputCard)

        self.solfwareGroup.addSettingCard(self.languageCard)
        self.solfwareGroup.addSettingCard(self.autoStartCard)

    def resizeEvent(self, arg__1):
        self.settingLabel.move(self.scrollWidget.geometry().left()+36, 30)
        return super().resizeEvent(arg__1)

    def initConnect(self):
        self.savePathCard.clicked.connect(self.__onImageSavePathCardClicked)
        self.saveCalibrationPathCard.clicked.connect(self.__onCalibrationPathCardClicked)
        self.saveRecipePathCard.clicked.connect(self.__onRecipePathCardClicked)
        self.ioOutputCard.clicked.connect(self.__OnIoOutputCardClicked)
        self.ioStatausCard.clicked.connect(self.__onIoStatusCardClicked)

    def setIoWatchWidget(self, ioWatchWidget:type):
        """ 设置IO监视窗口
        :param ioWatchWidget: IO监视窗口类型
        """
        self.ioWatchWidgetType = ioWatchWidget

    def setIoOptionWidget(self, ioOptionWidget:type):
        """ 设置IO操作窗口
        :param ioOptionWidget: IO操作窗口类型
        """
        self.ioOptionWidgetType = ioOptionWidget
        
    def setMotion(self, motion):
        """ 设置运动控制对象
        :param motion: 运动控制对象
        """
        self.motion = motion
        
    def setInputConfig(self, data):
        """ 设置输入配置
        :param data: 输入配置数据
        """
        self.inputConfig = data
        
    def setOutputConfig(self, data):
        """ 设置输出配置
        :param data: 输出配置数据
        """
        self.outputConfig = data

    def __onImageSavePathCardClicked(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹路径"),self.setting_cfg.get(self.setting_cfg.imageSavePath))
        if not folder or self.setting_cfg.get(self.setting_cfg.imageSavePath) == folder:
            return 
        
        self.setting_cfg.set(self.setting_cfg.imageSavePath,folder)
        self.savePathCard.setContent(folder)

    def __onCalibrationPathCardClicked(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹路径"),self.setting_cfg.get(self.setting_cfg.calibrationPath))
        if not folder or self.setting_cfg.get(self.setting_cfg.calibrationPath) == folder:
            return
        self.setting_cfg.set(self.setting_cfg.calibrationPath,folder)
        self.saveCalibrationPathCard.setContent(folder)

    def __onRecipePathCardClicked(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹路径"),self.setting_cfg.get(self.setting_cfg.recipePath))
        if not folder or self.setting_cfg.get(self.setting_cfg.recipePath) == folder:
            return
        self.setting_cfg.set(self.setting_cfg.recipePath,folder)
        self.saveRecipePathCard.setContent(folder)

    def __onIoStatusCardClicked(self):
        if self.ioWatchWidgetType is None:
            InfoBar.warning(self.tr("提示"), self.tr("程序未设置IO监视窗口"), parent=self)
            return
        if self.ioWatchWidget is not None:
            InfoBar.warning(self.tr("提示"), self.tr("IO监视窗口已存在, 请先关闭窗口"), parent=self)
            return
        widget = self.ioWatchWidgetType()
        if isinstance(widget, QWidget):
            if getattr(widget, "setIoConfig", None) and self.inputConfig is not None:
                widget.setIoConfig(*self.inputConfig)
            if getattr(widget, "setMotion", None) and self.motion is not None:
                widget.setMotion(self.motion)
            if getattr(widget, "initWidget", None):
                widget.initWidget()
            widget.setParent(self, Qt.WindowType.Window)
            widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 设置关闭时自动删除
            widget.show()
            self.ioWatchWidget = widget  # 更新IO监视窗口引用
            widget.destroyed.connect(lambda: setattr(self, 'ioWatchWidget', None))  # 清理引用
        else:
            InfoBar.warning(self.tr("提示"), self.tr("IO监视窗口类型错误, 请检查设置"), parent=self)
        

    def __OnIoOutputCardClicked(self):
        if self.ioOptionWidgetType is None:
            InfoBar.warning(self.tr("提示"), self.tr("程序未设置IO操作窗口"), parent=self)
            return
        if self.ioOptionWidget is not None:
            InfoBar.warning(self.tr("提示"), self.tr("IO监视窗口已存在, 请先关闭窗口"), parent=self)
            return
        widget = self.ioOptionWidgetType()
        if isinstance(widget, QWidget):
            if getattr(widget, "setIoConfig", None) and self.outputConfig is not None:
                widget.setIoConfig(*self.outputConfig)
            if getattr(widget, "setMotion", None) and self.motion is not None:
                widget.setMotion(self.motion)
            if getattr(widget, "initWidget", None):
                widget.initWidget()
            widget.setParent(self, Qt.WindowType.Window)
            widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 设置关闭时自动删除
            widget.show()
            self.ioOptionWidget = widget  # 更新IO监视窗口引用
            widget.destroyed.connect(lambda: setattr(self, 'ioOptionWidget', None))  # 清理引用
        else:
            InfoBar.warning(self.tr("提示"), self.tr("IO操作窗口类型错误, 请检查设置"), parent=self)