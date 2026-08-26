import json
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal,QRectF,QPointF
from PySide6.QtGui import QColor,QPolygonF
from qfluentwidgets import ConfigItem,exceptionHandler,FolderValidator, BoolValidator, ConfigValidator, ConfigSerializer,OptionsConfigItem

class QRectValidator(ConfigValidator):
    def validate(self, value: QRectF):
        if isinstance(value, QRectF):
            return value
        raise ValueError(f"Invalid value: {value}")
    
    def correct(self, value: QRectF):
        return value
    
class QRectSerializer(ConfigSerializer):
    def serialize(self, value: QRectF):
        # 将QRectF转换为可序列化的字典
        return {
            "x": value.x(),
            "y": value.y(),
            "width": value.width(),
            "height": value.height()
        }

    def deserialize(self, value):
        # 从字典重建QRectF对象
        return QRectF(
            value.get('x', 0),
            value.get('y', 0),
            value.get('width', 100),
            value.get('height', 100)
        )

class QPointValidator(ConfigValidator):
    def validate(self, value: QPointF):
        if isinstance(value, QPointF):
            return value
        raise ValueError(f"Invalid value: {value}")

    def correct(self, value: QPointF):
        return value
    
class QPointSerializer(ConfigSerializer):
    def serialize(self, value: QPointF):
        # 将QPointF转换为可序列化的字典
        return {
            "x": value.x(),
            "y": value.y()
        }

    def deserialize(self, value):
        # 从字典重建QPointF对象
        return QPointF(
            value.get('x', 0),
            value.get('y', 0)
        )

class QPolygonFValidator(ConfigValidator):
    def validate(self, value: QPolygonF):
        if isinstance(value, QPolygonF) :
            return True
        raise ValueError(f"Invalid value: {value}")

    def correct(self, value: QPolygonF):
        return value
    
class QPolygonFSerializer(ConfigSerializer):
    def serialize(self, value: QPolygonF):
        # 将QPolygonF转换为可序列化的列表
        return [point.toTuple() for point in value]

    def deserialize(self, value):
        # 从列表重建QPolygonF对象
        return QPolygonF([QPointF(x, y) for x, y in value])
    
class RangeValueValidator(ConfigValidator):
    def __init__(self,min,max):
        self.min = min
        self.max = max
        self.range = (min, max)

    def validate(self, value: List[float]):
        if isinstance(value, list) and len(value) == 2:
            return self.min <= value[0] <= self.max and self.min <= value[1] <= self.max
        return False

    def correct(self, value: List[float]):
        ret = [max(min(value[0], self.max), self.min), max(min(value[1], self.max), self.min)]
        return ret   

class RangeValueSerializer(ConfigSerializer):
    def serialize(self, value: List[float]):
        return {
            "min": value[0],
            "max": value[1]
        }

    def deserialize(self, value):
        return [value.get('min', 0),value.get('max', 0)]

class RangeValueConfigItem(ConfigItem):
    
    @property
    def range(self):
        return self.validator.range

    @property
    def start(self):
        return self.value[0]

    @property 
    def end(self):
        return self.value[1]

    def __str__(self):
        return f'{self.__class__.__name__}range={self.range} start:{self.start} end:{self.end}'  

class ParamConfig(QObject):
    def __init__(self, parent=None):
        super().__init__()
        self.file = Path("config/param.json")
        self._cfg = self
        self.paraList = {}
    
    def addParam(self,item):
        if not isinstance(item, ConfigItem):
            return
        self.paraList[item.group+"."+item.name] = item

    def get(self,name):
        if self.paraList.get(name) is None:
            return None
        return self.paraList.get(name).value
    
    def getItem(self,name):
        if self.paraList.get(name) is None:
            return None
        return self.paraList.get(name)

    def set(self,key,value):
        if self.paraList.get(key) is None:
            return
        
        if self.paraList.get(key).value == value:
            return
        
        try:
            self.paraList.get(key).value = deepcopy(value) # 深拷贝，避免修改原始值
        except Exception as e:
            self.paraList.get(key).value = value

        self.save()

    def toDict(self):
        items = {}
        for item in self.paraList.values():
            if not isinstance(item, ConfigItem):
                continue
        
            value = item.serialize() if item.serialize else item.value
            if not items.get(item.group):
                if not item.name:
                    items[item.group] = value
                else:
                    items[item.group] = {}

            if item.name:
                items[item.group][item.name] = value
        
        return items
    
    def save(self):
        self._cfg.file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cfg.file, 'w', encoding='utf-8') as f:
            json.dump(self.toDict(), f, ensure_ascii=False, indent=4)

    def clear(self):
        for item in self.paraList.values():
            if isinstance(item, ConfigItem):
                item.value = item.defaultValue

    @exceptionHandler()
    def load(self,file=None,config=None):
        if isinstance(file, (str, Path)):
            self._cfg.file = Path(file)
        
        try:
            with open(self._cfg.file, encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            cfg = {}

        # map config items'key to item
        items = {}
        for item in self.paraList.values():
            if isinstance(item, ConfigItem):
                items[item.key] = item

        for k,v,in cfg.items():
            if not isinstance(v, dict) and items.get(k) is not None:
                items[k].deserializeFrom(v)

            elif isinstance(v, dict):
                for key, value in v.items():
                    key = k + "." + key
                    if items.get(key) is not None:
                        items[key].deserializeFrom(value)


param_cfg = ParamConfig()
# print(param_cfg)

if __name__ == "__main__":
    param_cfg.addParam(ConfigItem("Vision", "ImageSavePath", "D:/VisionImage", FolderValidator()))
    param_cfg.addParam(ConfigItem("Vision", "SourceImageSaveChecked", True, BoolValidator()))
    param_cfg.addParam(ConfigItem("Vision", "CalibrationPath", "D:/VisionImage/Calibration", FolderValidator()))
    param_cfg.addParam(ConfigItem("Vision", "RecipePath", "D:/VisionImage/Recipe", FolderValidator()))
    param_cfg.addParam(ConfigItem("PlcSetting", "PlcIp","192.168.0.14"))
    param_cfg.addParam(ConfigItem("solfware", "AutoStart", True, BoolValidator()))


    param_cfg.load("config/param.json")


    print(param_cfg.get("Vision.ImageSavePath"))
    print(param_cfg.get("Vision.SourceImageSaveChecked"))
    print(param_cfg.get("Vision.CalibrationPath"))
    print(param_cfg.get("Vision.RecipePath"))
    print(param_cfg.get("PlcSetting.PlcIp"))
    print(param_cfg.get("solfware.AutoStart"))

    param_cfg.set("Vision.ImageSavePath","D:/VisionImage/Test")
    param_cfg.set("Vision.SourceImageSaveChecked",False)
    param_cfg.set("Vision.CalibrationPath","D:/VisionImage/Calibration/Test")
    param_cfg.set("Vision.RecipePath","D:/VisionImage/Recipe/Test")