

from PySide6.QtCore import QRectF, Qt, QPointF, QLineF
from PySide6.QtGui import QColor,QPolygonF
from qfluentwidgets import (
    ConfigItem, ConfigValidator, ConfigSerializer
    )
from ...common import CaliperLineItemData
from ...common import LineItemData, RectItemData,PolygonItemData,RotatedRectItemData
from ...common import CaliperRectItemData, CaliperRotatedRectItemData
from ...common import CaliperItemData
from ...common import CurveItemData, CaliperCurveItemData
from ...common import PolygonItemData, CaliperPolygonItemData

class LineItemValidator(ConfigValidator):
    def validate(self, value):
        if isinstance(value, LineItemData):
            if value.line.isNull():
                return False
            return True
        return False
    
    def correct(self, value: LineItemData):
        return value if self.validate(value) else LineItemData()
    
class LineItemSerializer(ConfigSerializer):
    def serialize(self, value: LineItemData):
        # LineItemData
        return {
            "id": value.id,
            "depend": value.depend,
            "penColor": QColor(value.penColor).name(QColor.NameFormat.HexRgb),  # 转换为十六进制颜色字符串
            "type": value.type,
            "line": {
                "p1": {"x": value.line.p1().x(), "y": value.line.p1().y()},
                "p2": {"x": value.line.p2().x(), "y": value.line.p2().y()}
            },
            "pos": {"x": value.pos.x(), "y": value.pos.y()}  # 添加位置属性
        }
    
    def deserialize(self, value):
        # 从字典重建CaliperLineItemData对象
        try:
            data = LineItemData(
                id=value.get("id", "None"),  # 默认值为"None"
                depend=value.get("depend", "None"),  # 默认值为"None"
                penColor=QColor(value.get("penColor", "#00FF00")),  # 默认绿色
                type=value.get("type", "None"),  # 默认值为"None"
                line=QLineF(
                    QPointF(value.get("line", {}).get("p1", {}).get("x", 0), value.get("line", {}).get("p1", {}).get("y", 0)),
                    QPointF(value.get("line", {}).get("p2", {}).get("x", 0), value.get("line", {}).get("p2", {}).get("y", 0))
                ),
                pos=QPointF(value.get("pos", {}).get('x', 0), value.get("pos", {}).get('y', 0))  # 默认位置为(0, 0
            )
        except Exception as e:
            print("error",e)
        return data

class LineItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: CaliperLineItemData = None):
        super().__init__(group, name, default, LineItemValidator(), LineItemSerializer(), False)

class CurveItemValidator(ConfigValidator):
    def validate(self, value):
        if isinstance(value, CurveItemData):
            if value.polygon.isEmpty():
                return False
            return True
        return False
    
    def correct(self, value: CurveItemData):
        return value if self.validate(value) else CurveItemData()
    
class CurveItemSerializer(ConfigSerializer):
    def serialize(self, value: CurveItemData):
        # 将CurveItemData转换为可序列化的字典
        return {
            "id": value.id,
            "depend": value.depend,
            "penColor": QColor(value.penColor).name(QColor.NameFormat.HexRgb),  # 转换为十六进制颜色字符串
            "type": value.type,
            "polygon": [(point.x(), point.y()) for point in value.polygon],  # 转换为列表
            "pos": {"x": value.pos.x(), "y": value.pos.y()}  # 添加位置属性
        }
    
    def deserialize(self, value):
        # 从字典重建CurveItemData对象
        try:
            data = CurveItemData(
                id=value.get("id", "None"),  # 默认值为"None"
                depend=value.get("depend", "None"),  # 默认值为"None"
                penColor=QColor(value.get("penColor", "#00FF00")),  # 默认绿色
                type=value.get("type", "None"),  # 默认值为"None"
                polygon=QPolygonF([QPointF(*point) for point in value.get("polygon", [])]),  # 默认值为空列表
                pos=QPointF(value.get("pos", {}).get('x', 0), value.get("pos", {}).get('y', 0))  # 默认位置为(0, 0)
            )
        except Exception as e:
            print("error",e)
        return data
    
class CurveItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: CurveItemData = None):
        super().__init__(group, name, default, CurveItemValidator(), CurveItemSerializer(), False)

class PolygonItemValidator(ConfigValidator):
    def validate(self, value):
        if isinstance(value, PolygonItemData):
            if value.polygon.isEmpty():
                return False
            return True
        return False
    def correct(self, value: PolygonItemData):
        return value if self.validate(value) else PolygonItemData()
    
class PolygonItemSerializer(ConfigSerializer):
    def serialize(self, value: PolygonItemData):
        # 将PolygonItemData转换为可序列化的字典
        return {
            "id": value.id,
            "depend": value.depend,
            "penColor": QColor(value.penColor).name(QColor.NameFormat.HexRgb),  # 转换为十六进制颜色字符串
            "type": value.type,
            "polygon": [point.toTuple() for point in value.polygon],  # 转换为列表
            "is_closed": value.is_closed,  # 是否闭合多边形
        }
    
    def deserialize(self, value):
        # 从字典重建PolygonItemData对象
        try:
            data = PolygonItemData(
                id=value.get("id", "None"),  # 默认值为"None"
                depend=value.get("depend", "None"),  # 默认值为"None
                penColor=QColor(value.get("penColor", "#00FF00")),  # 默认绿色
                type=value.get("type", "None"),  # 默认值为"None"
                # polygon=[QPointF(*point) for point in value.get("polygon", [])]  # 默认值为空列表  
                polygon = QPolygonF([QPointF(x, y) for x, y in value.get("polygon", [])]),  # 默认值为空列表
                is_closed=value.get("is_closed", True)  # 是否闭合多边形，默认为True
            )
        except Exception as e:
            print("error",e)
        return data

class PolygonItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: PolygonItemData = None):
        super().__init__(group, name, default, PolygonItemValidator(), PolygonItemSerializer(), False)

    def __str__(self):
        return f'{self.__class__.__name__}({self.id}, {self.type}, {self.polygon}'
    
class RectItemValiator(ConfigValidator):
    def validate(self, value):
        if isinstance(value, RectItemData):
            if value.rect.isNull():
                return False
            return True
        return False

    def correct(self, value: RectItemData):
        return value if self.validate(value) else RectItemData()
    
class RectItemSerializer(ConfigSerializer):
    def serialize(self, value: RectItemData):
        # 将RectItemData转换为可序列化的字典
        return {
            "id": value.id,
            "depend": value.depend,
            "penColor": QColor(value.penColor).name(QColor.NameFormat.HexRgb),
            "type": value.type,
            "rect": {
                "x": value.rect.x(),
                "y": value.rect.y(),
                "width": value.rect.width(),
                "height": value.rect.height()
            } 
        }
    def deserialize(self, value):
        # 从字典重建RectItemData对象
        try:
            data =  RectItemData(
                id=value.get("id", "None"),
                depend=value.get("depend", "None"),
                penColor=QColor(value.get("penColor", "#00FF00")),  # 默认绿色
                type=value.get("type", "None"),
                rect=QRectF(
                    value.get("rect", {}).get("x", 0),
                    value.get("rect", {}).get("y", 0),
                    value.get("rect", {}).get("width", 0),
                    value.get("rect", {}).get("height", 0) 
                )  
            )
        except Exception as e:
            print("error",e)
        return data

class RectItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: RectItemData = None):
        super().__init__(group, name, default, RectItemValiator(), RectItemSerializer(), False)

    def __str__(self):
        return f'{self.__class__.__name__}({self.id}, {self.type}, {self.rect})'

class RotatedRectItemValidator(ConfigValidator):
    def validate(self, value: RotatedRectItemData):
        if isinstance(value, RotatedRectItemData):
            if value.rect.isNull():
                return False
            return True
        return False

    def correct(self, value: RectItemData):
        return value if self.validate(value) else RotatedRectItemData()
    
class RotatedRectItemSerializer(RectItemSerializer):
    def serialize(self, value: RotatedRectItemData):
        # 将RectItemData转换为可序列化的字典
        data = super().serialize(value)
        data["rotation"] = value.rotation  # 添加旋转角度
        return data
    
    def deserialize(self, value):
        # 从字典重建RectItemData对象
        try:
            basedata = super().deserialize(value)
            data = RotatedRectItemData()
            for attr in basedata.__dict__.keys():
                # 将RectItemData的属性复制到RotatedRectItemData
                setattr(data, attr, getattr(basedata, attr))
            data.rotation = value.get("rotation", 0)  # 默认旋转角度为0
        except Exception as e:
            print("error",e)
        return data
    
class RotatedRectItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: RotatedRectItemData = None):
        super().__init__(group, name, default, RotatedRectItemValidator(), RotatedRectItemSerializer(), False)

    def __str__(self):
        return f'{self.__class__.__name__}({self.id}, {self.type}, {self.rect}, {self.rotation})'

class CaliperItemDataSerializer(ConfigSerializer):
    def serialize(self, value: CaliperItemData):
        # 将CaliperItemData转换为可序列化的字典
        return {
            "caliperWidth": value.caliperWidth,
            "caliperHeight": value.caliperHeight,
            "caliperOffset1": value.caliperOffset1,
            "caliperOffset2": value.caliperOffset2,
            "caliperGap": value.caliperGap,
            "caliperColor": QColor(value.caliperColor).name(QColor.NameFormat.HexRgb),
        }
    def deserialize(self, value) -> CaliperItemData:
        # 从字典重建CaliperItemData对象
        try:
            data = CaliperItemData(
                caliperWidth=value.get("caliperWidth", 0),
                caliperHeight=value.get("caliperHeight", 0),
                caliperOffset1=value.get("caliperOffset1", 0),
                caliperOffset2=value.get("caliperOffset2", 0),
                caliperGap=value.get("caliperGap", 0),
                caliperColor=QColor(value.get("caliperColor", Qt.GlobalColor.darkMagenta))
            )
        except Exception as e:
            print("error",e)
        return data

class CaliperRectItemValidator(ConfigValidator):
    def validate(self, value: CaliperRectItemData):
        if isinstance(value, RectItemData):
            if value.rect.isNull():
                return False
            return True
        return False

    def correct(self, value: CaliperRectItemData):
        return value if self.validate(value) else CaliperRectItemData()
    
class CaliperRectItemSerializer(ConfigSerializer):
    def serialize(self, value: CaliperRectItemData):
        # 将CaliperRectItemData转换为可序列化的字典
        if isinstance(value, CaliperRectItemData):
            data = RectItemSerializer().serialize(value)
            data1 = CaliperItemDataSerializer().serialize(value)
            data.update(data1)  # 合并两个字典
            data["calipers"] = {}
            for key, caliper in value.calipers.items():
                data["calipers"][key] = []
                for rect in caliper:
                    data["calipers"][key].append({
                        "rect": [rect.x(), rect.y(), rect.width(), rect.height()]
                    })
            return data
    
    def deserialize(self, value):
        # 从字典重建RectCaliperItemData对象
        try:
            _data = RectItemSerializer().deserialize(value)
            _data1 = CaliperItemDataSerializer().deserialize(value)
            data = CaliperRectItemData()
            data.id = _data.id
            data.depend = _data.depend
            data.type = _data.type
            data.penColor = _data.penColor
            data.rect = _data.rect
            data.caliperWidth = _data1.caliperWidth
            data.caliperHeight = _data1.caliperHeight
            data.caliperGap = _data1.caliperGap
            data.caliperOffset1 = _data1.caliperOffset1
            data.caliperOffset2 = _data1.caliperOffset2
            data.caliperColor = _data1.caliperColor
            data.calipers = {}
            for key, caliper in value.get("calipers", {}).items():
                if key not in data.calipers:
                    data.calipers[key] = []
                for rectObj in caliper:
                    rect = rectObj.get("rect", [])
                    if len(rect) == 4:
                        data.calipers[key].append(QRectF(rect[0], rect[1], rect[2], rect[3]))
        except Exception as e:
            print("error",e)
        return data

class CaliperRectItemConfigItem(ConfigItem):
    def __init__(self, group, name, default,validator=CaliperRectItemValidator(), serializer=CaliperRectItemSerializer(), restart=False):
        super().__init__(group, name, default, validator, serializer, restart)
    
class CaliperRotatedRectItemValidator(CaliperRectItemValidator):
    def correct(self, value: CaliperRotatedRectItemData):
        return value if self.validate(value) else CaliperRotatedRectItemData()
    
class CaliperRotatedRectItemSerializer(CaliperRectItemSerializer):
    def serialize(self, value: CaliperRotatedRectItemData):
        if isinstance(value, CaliperRotatedRectItemData):
            data = super().serialize(value)
            data["rotation"] = value.rotation
            data["pos"] = {
                "x": value.pos.x(),
                "y": value.pos.y()
            }
            return data
    def deserialize(self, value):
        try:
            _data = super().deserialize(value)
            data = CaliperRotatedRectItemData()
            for key in _data.__dict__.keys():
                setattr(data, key, getattr(_data, key))
            data.rotation = value.get("rotation", 0.0)
            data.pos = QPointF(value.get("pos", {}).get('x', 0), value.get("pos", {}).get('y', 0))
        except Exception as e:
            print("error",e)
        return data
    
class CaliperRotatedRectItemConfigItem(ConfigItem):
    def __init__(self, group, name, default, validator=CaliperRotatedRectItemValidator(), serializer=CaliperRotatedRectItemSerializer(), restart=False):
        super().__init__(group, name, default, validator, serializer, restart)
    
class CaliperLineItemValidator(ConfigValidator):
    def validate(self, value: CaliperLineItemData):
        if isinstance(value, CaliperLineItemData):
            if value.line.isNull():
                return False
            return True
        return False

    def correct(self, value: CaliperLineItemData):
        return value if self.validate(value) else CaliperLineItemData()
    
class CaliperLineItemSerializer(ConfigSerializer):
    def serialize(self, value):
        # 将CaliperLineItemData转换为可序列化的字典
        if isinstance(value, CaliperLineItemData):
            data = LineItemSerializer().serialize(value)
            data1 = CaliperItemDataSerializer().serialize(value)
            data.update(data1)
            data["calipers"] = {}
            for key, caliper in value.calipers.items():
                data["calipers"][key] = []
                for polygon in caliper:
                    data["calipers"][key].append({
                        "polygon": [{'x': point.x(), 'y': point.y()} for point in polygon]
                    })
            return data
            
    def deserialize(self, value):
        # 从字典重建CaliperLineItemData对象
        try:
            _data = LineItemSerializer().deserialize(value)
            _data1 = CaliperItemDataSerializer().deserialize(value)
            data = CaliperLineItemData()
            data.id = _data.id
            data.depend = _data.depend
            data.type = _data.type
            data.penColor = _data.penColor
            data.line = _data.line
            data.pos = _data.pos
            data.caliperWidth = _data1.caliperWidth
            data.caliperHeight = _data1.caliperHeight
            data.caliperGap = _data1.caliperGap
            data.caliperOffset1 = _data1.caliperOffset1
            data.caliperOffset2 = _data1.caliperOffset2
            data.caliperColor = _data1.caliperColor
            data.calipers = {}
            for key, caliper in value.get("calipers", {}).items():
                if key not in data.calipers:
                    data.calipers[key] = []
                for polygonObj in caliper:
                    polygon_points = polygonObj.get("polygon", [])
                    polygon = QPolygonF([QPointF(point['x'], point['y']) for point in polygon_points])
                    data.calipers[key].append(polygon)
        except Exception as e:
            print("error",e)
        return data
                
class CaliperLineItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: CaliperLineItemData = None):
        super().__init__(group, name, default, CaliperLineItemValidator(), CaliperLineItemSerializer(), False)

class CaliperCurveItemValidator(ConfigValidator):
    def validate(self, value: CaliperCurveItemData):
        if isinstance(value, CaliperCurveItemData):
            if value.polygon.isEmpty():
                return False
            return True
        return False

    def correct(self, value: CaliperCurveItemData):
        return value if self.validate(value) else CaliperCurveItemData()

class CaliperCurveItemSerializer(ConfigSerializer):
    def serialize(self, value: CaliperCurveItemData):
        # 将CaliperCurveItemData转换为可序列化的字典
        if isinstance(value, CaliperCurveItemData):
            data = CurveItemSerializer().serialize(value)
            data1 = CaliperItemDataSerializer().serialize(value)
            data.update(data1)
            data["calipers"] = {}
            for key, caliper in value.calipers.items():
                data["calipers"][key] = []
                for polygon in caliper:
                    data["calipers"][key].append({
                        "polygon": [{'x': point.x(), 'y': point.y()} for point in polygon]
                    })
            return data
        
    def deserialize(self, value):
        # 从字典重建CaliperCurveItemData对象
        try:
            _data = CurveItemSerializer().deserialize(value)
            _data1 = CaliperItemDataSerializer().deserialize(value)
            data = CaliperCurveItemData()
            data.id = _data.id
            data.depend = _data.depend
            data.type = _data.type
            data.penColor = _data.penColor
            data.polygon = _data.polygon
            data.pos = _data.pos
            data.caliperWidth = _data1.caliperWidth
            data.caliperHeight = _data1.caliperHeight
            data.caliperGap = _data1.caliperGap
            data.caliperOffset1 = _data1.caliperOffset1
            data.caliperOffset2 = _data1.caliperOffset2
            data.caliperColor = _data1.caliperColor
            data.calipers = {}
            for key, caliper in value.get("calipers", {}).items():
                if key not in data.calipers:
                    data.calipers[key] = []
                for polygonObj in caliper:
                    polygon_points = polygonObj.get("polygon", [])
                    polygon = QPolygonF([QPointF(point['x'], point['y']) for point in polygon_points])
                    data.calipers[key].append(polygon)
        except Exception as e:
            print("error",e)
        return data
    
class CaliperCurveItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: CaliperCurveItemData = None):
        super().__init__(group, name, default, CaliperCurveItemValidator(), CaliperCurveItemSerializer(), False)
        
class CaliperPolygonItemValidator(ConfigValidator):
    def validate(self, value: CaliperPolygonItemData):
        if isinstance(value, CaliperPolygonItemData):
            if value.polygon.isEmpty():
                return False
            return True
        return False

    def correct(self, value: CaliperPolygonItemData):
        return value if self.validate(value) else CaliperPolygonItemData()
    
class CaliperPolygonItemSerializer(ConfigSerializer):
    def serialize(self, value: CaliperPolygonItemData):
        # 将CaliperPolygonItemData转换为可序列化的字典
        if isinstance(value, CaliperPolygonItemData):
            data = PolygonItemSerializer().serialize(value)
            data1 = CaliperItemDataSerializer().serialize(value)
            data.update(data1)
            data["pos"] = {
                "x": value.pos.x(),
                "y": value.pos.y()
            }
            data["calipers"] = {}
            for key, caliper in value.calipers.items():
                data["calipers"][key] = []
                for polygon in caliper:
                    data["calipers"][key].append({
                        "polygon": [{'x': point.x(), 'y': point.y()} for point in polygon]
                    })
            return data
        
    def deserialize(self, value):
        # 从字典重建CaliperPolygonItemData对象
        try:
            _data = PolygonItemSerializer().deserialize(value)
            _data1 = CaliperItemDataSerializer().deserialize(value)
            data = CaliperPolygonItemData()
            data.id = _data.id
            data.depend = _data.depend
            data.type = _data.type
            data.penColor = _data.penColor
            data.polygon = _data.polygon
            data.is_closed = _data.is_closed
            data.pos = QPointF(value.get("pos", {}).get('x', 0), value.get("pos", {}).get('y', 0))
            data.caliperWidth = _data1.caliperWidth
            data.caliperHeight = _data1.caliperHeight
            data.caliperGap = _data1.caliperGap
            data.caliperOffset1 = _data1.caliperOffset1
            data.caliperOffset2 = _data1.caliperOffset2
            data.caliperColor = _data1.caliperColor
            data.calipers = {}
            for key, caliper in value.get("calipers", {}).items():
                if key not in data.calipers:
                    data.calipers[key] = []
                for polygonObj in caliper:
                    polygon_points = polygonObj.get("polygon", [])
                    polygon = QPolygonF([QPointF(point['x'], point['y']) for point in polygon_points])
                    data.calipers[key].append(polygon)
        except Exception as e:
            print("error",e)
        return data
    
class CaliperPolygonItemConfigItem(ConfigItem):
    def __init__(self, group, name, default: CaliperPolygonItemData = None):
        super().__init__(group, name, default, CaliperPolygonItemValidator(), CaliperPolygonItemSerializer(), False)