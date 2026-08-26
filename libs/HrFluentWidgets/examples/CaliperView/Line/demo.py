import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QImage,QPolygon,QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsScene
from hrfluentwidgets import LoginWidget,LoginWidgetWithRole,AoiWindow,DetectInterface,SettingInterface,RecipeParamWithViewWidget, RecipeUserItemParamWidget
from hrfluentwidgets import HrIcon
from qfluentwidgets import FluentIcon as FIF,setTheme,Theme,NavigationItemPosition
from hrfluentwidgets import (CalibrationBase,CalibrationType,RecipeWithItemInterface,RecipeParamWidget)
import random 
from hrfluentwidgets import setting_cfg
from hrfluentwidgets import param_cfg,RangeValueConfigItem,RangeValueValidator,RangeValueSerializer,QPolygonFSerializer,QPolygonFValidator
from qfluentwidgets import  BoolValidator, OptionsValidator, ConfigItem,RangeConfigItem,RangeValidator,OptionsConfigItem


from hrfluentwidgets import(
    RangeValueConfigItem,RangeValueValidator,
    RangeValueSerializer,
    SpinBoxItem,DoubleSpinBoxItem,
    RangeSpinBoxItem,RangeDoubleSpinBoxItem,SwitchItem,ComboxItem,
    RectItemData,RectItemConfigItem,PolygonItemConfigItem,PolygonItemData,
    GraphicsCaliperRectParam, CaliperRectItemData, CaliperRectItemConfigItem, GraphicsCrossItem,
    GraphicsCaliperRotatedRectItem, CaliperRotatedRectItemData, CaliperRotatedRectItemConfigItem,
    CaliperRotatedRectItemSupport, RotatedRectItemSupport,
    CaliperLineItemSupport, CaliperLineItemData, CaliperLineItemConfigItem, GraphicsCaliperLineItem,
)

def polygon_to_points(polygons:list[QPolygonF]) -> tuple[list[tuple[float, float]]]:
    top_lefts = []
    top_rights = []
    bottom_lefts = []
    bottom_rights = []
    
    for polygon in polygons:
        top_left = polygon[0]
        top_right = polygon[1]
        bottom_left = polygon[3]
        bottom_right = polygon[2]
        
        top_lefts.append((top_left.x(), top_left.y()))
        top_rights.append((top_right.x(), top_right.y()))
        bottom_lefts.append((bottom_left.x(), bottom_left.y()))
        bottom_rights.append((bottom_right.x(), bottom_right.y()))
            
    return top_lefts, top_rights, bottom_lefts, bottom_rights

if __name__ == "__main__":
    from HRVision.Algorithm.Measure import Measure, MeasureResult
    from HRVision.Controller.ProcessQt import qimage_to_ndarray
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    
    pageName = "卡尺"

    w2 = RecipeWithItemInterface(setting_cfg.get(setting_cfg.recipePath))
    w2.setObjectName("recipe")

    param_cfg.addParam(CaliperLineItemConfigItem("measure", "calipers", CaliperLineItemData()))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-width", 20, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-height", 200, RangeValidator(1, 1000)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-gap", 20, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-offset", 10, RangeValidator(0, 100)))
    
    param_cfg.addParam(RangeConfigItem("measure", "sigma", 1, RangeValidator(0.1, 100)))
    param_cfg.addParam(RangeConfigItem("measure", "threshold", 30, RangeValidator(1, 100)))
    param_cfg.addParam(OptionsConfigItem("measure", "transition", "all", OptionsValidator(["all", "positive", "negative"])))
    param_cfg.addParam(OptionsConfigItem("measure", "select", "all", OptionsValidator(["all", "first", "last"])))
          
    paramWidget = RecipeUserItemParamWidget()
    paramWidget.addItemType("rotated_caliper_rect", lambda : GraphicsCaliperLineItem(), CaliperLineItemSupport())
    
    paramWidget.addParamItem(GraphicsCaliperRectParam("卡尺",param_cfg,"measure.calipers"))
    
    paramWidget.addParamItem(SpinBoxItem("平滑度:",param_cfg,"measure.sigma"))
    paramWidget.addParamItem(SpinBoxItem("阈值:",param_cfg,"measure.threshold"))
    paramWidget.addParamItem(ComboxItem("方向:",param_cfg,"measure.transition"))
    paramWidget.addParamItem(ComboxItem("顺序:",param_cfg,"measure.select"))
    
    paramWidget.addEditBtn(HrIcon.RECT,"创建","rotated_caliper_rect",param_cfg,"measure.calipers",Qt.GlobalColor.green)
    paramWidget.addApplyBtn(FIF.APPLICATION,"测试","measure.calipers")
            
    # image = QImage("C:/Users/lzh/Desktop/微信图片_20250410143310.bmp")
    image = QImage(r"C:\Users\lzh\Desktop\02.bmp")
            
    measure = Measure(width=image.width(),height=image.height())
    
    def addResultEvent(key:str, scene:QGraphicsScene ,result:list[tuple[float,float,bool]]):
        for i in range(len(result)):
            item = GraphicsCrossItem()
            item.penColor = Qt.GlobalColor.green if result[i][2] else Qt.GlobalColor.red
            item.setData(Qt.ItemDataRole.UserRole + 10, "result")
            item.setPos(result[i][0],result[i][1])
            scene.addItem(item)
            
    def clearResultEvent(key:str, scene:QGraphicsScene):
        for item in scene.items():
            if item.data(Qt.ItemDataRole.UserRole + 10) == "result":
                scene.removeItem(item)
                del item
    
    def test(key:str,img:QImage):
        if key == "measure.calipers":
            calipers = param_cfg.get("measure.calipers").calipers_polygon()
            if isinstance(calipers, dict):
                line = calipers.get("line", [])

                measure.clear()
                top_lefts, top_rights, bottom_lefts, bottom_rights = polygon_to_points(line)
                measure.add_rectangle2_point(top_left=top_lefts, 
                                                top_right=top_rights, 
                                                bottom_left=bottom_lefts, 
                                                bottom_right=bottom_rights)
                
                npImage = qimage_to_ndarray(img)
                result = measure.run(npImage, 
                                           sigma=param_cfg.get("measure.sigma"),
                                           threshold=param_cfg.get("measure.threshold"),
                                           transition=param_cfg.get("measure.transition"),
                                           select=param_cfg.get("measure.select"))
                
                pos = []
                for item in result:
                    value = item.best()
                    if value is not None:
                        pos.append((value[0], value[1], True))
                # pos = []
                # for item in top_lefts:
                #     pos.append((item[0], item[1], True))
                # for item in top_rights:
                #     pos.append((item[0], item[1], False))
                w2.updateResult(pageName, pos)
                
    paramWidget.applySignal.connect(test)
    
    w2.addResultItemSignal.connect(addResultEvent)
    w2.clearResultItemSignal.connect(clearResultEvent)
    w2.addCamera(pageName,paramWidget)
    w2.setStyleSheet('''QWidget{background-color: rgb(32, 32, 32);}''')
    w2.show()
    
    w2.updateImage(pageName,image)
    
    app.exec()