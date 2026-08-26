import sys
from enum import Enum

from PySide6.QtCore import QLocale,Signal
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, Theme, FolderValidator, ConfigSerializer, __version__)

class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()

class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

class SettingConfig(QConfig):
    autoStartSig = Signal()
    """视觉参数"""
    imageSavePath =  ConfigItem("Vision", "ImageSavePath", "C:/VisionImage", FolderValidator())
    sourceImageSaveChecked = ConfigItem("Vision", "SourceImageSaveChecked", True, BoolValidator())
    calibrationPath = ConfigItem("Vision", "CalibrationPath", "C:/VisionImage/Calibration", FolderValidator())
    recipePath = ConfigItem("Vision", "RecipePath", "C:/VisionImage/Recipe", FolderValidator())
    """PLC参数"""
    plcIp = ConfigItem("PlcSetting","PlcIp","192.168.0.1")
    """轴卡参数"""

    """软件设置"""
    language = OptionsConfigItem("solfware", "Language",Language.AUTO,OptionsValidator(Language),LanguageSerializer(),restart=True)
    autoStart = ConfigItem("solfware", "AutoStart", False, BoolValidator())

    def __init__(self):
        super().__init__()
        
    def set(self, item, value, save=True, copy=True):
        if item == self.autoStart:
            self.autoStartSig.emit()
        return super().set(item, value, save, copy)

try:
    setting_cfg = SettingConfig()
    qconfig.load('config/config.json',setting_cfg)
except Exception as e:
    pass