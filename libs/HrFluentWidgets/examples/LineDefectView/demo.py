import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QImage, QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsScene
from hrfluentwidgets import RecipeWithItemInterface
from hrfluentwidgets import HrIcon
from qfluentwidgets import setTheme, FluentIcon as FIF, Theme, RangeConfigItem, RangeValidator, OptionsConfigItem, OptionsValidator
from hrfluentwidgets import setting_cfg
from hrfluentwidgets import param_cfg
from hrfluentwidgets import (
    SpinBoxItem, ComboxItem, 
    RecipeUserItemParamWidget,
    CaliperRotatedRectItemSupport,
    GraphicsCaliperRotatedRectItem,
    GraphicsCaliperRectParam, 
    CaliperRotatedRectItemData, 
    CaliperRotatedRectItemConfigItem, 
    GraphicsCrossItem
)

def polygon_to_points(polygons:list[QPolygonF], dire:str) -> tuple[list[tuple[float, float]]]:
    top_lefts = []
    top_rights = []
    bottom_lefts = []
    bottom_rights = []
    
    for polygon in polygons:
        top_left = polygon[0]
        top_right = polygon[1]
        bottom_left = polygon[3]
        bottom_right = polygon[2]
        
        if dire == "top":
            top_lefts.append((top_left.x(), top_left.y()))
            top_rights.append((top_right.x(), top_right.y()))
            bottom_lefts.append((bottom_left.x(), bottom_left.y()))
            bottom_rights.append((bottom_right.x(), bottom_right.y()))
        elif dire == "left":
            top_lefts.append((bottom_left.x(), bottom_left.y()))
            top_rights.append((top_left.x(), top_left.y()))
            bottom_lefts.append((bottom_right.x(), bottom_right.y()))
            bottom_rights.append((top_right.x(), top_right.y()))
        elif dire == "bottom":
            top_lefts.append((bottom_right.x(), bottom_right.y()))
            top_rights.append((bottom_left.x(), bottom_left.y()))
            bottom_lefts.append((top_left.x(), top_left.y()))
            bottom_rights.append((top_right.x(), top_right.y()))
        elif dire == "right":
            top_lefts.append((top_right.x(), top_right.y()))
            top_rights.append((bottom_right.x(), bottom_right.y()))
            bottom_lefts.append((top_left.x(), top_left.y()))
            bottom_rights.append((bottom_left.x(), bottom_left.y()))
            
    return top_lefts, top_rights, bottom_lefts, bottom_rights

if __name__ == "__main__":
    from HRVision.Algorithm.Measure import Measure, MeasureResult
    from HRVision.Algorithm.DefectDetector import FitLineSegDefect
    from HRVision.Controller.ProcessQt import qimage_to_ndarray
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    
    pageName = "卡尺"

    w2 = RecipeWithItemInterface(setting_cfg.get(setting_cfg.recipePath))
    w2.setObjectName("recipe")

    param_cfg.addParam(CaliperRotatedRectItemConfigItem("measure", "calipers", CaliperRotatedRectItemData()))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-width", 20, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-height", 200, RangeValidator(1, 1000)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-gap", 20, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("measure.calipers", "caliperRect-offset", 20, RangeValidator(0, 1000)))
    
    param_cfg.addParam(RangeConfigItem("measure", "sigma", 1, RangeValidator(0.1, 100)))
    param_cfg.addParam(RangeConfigItem("measure", "threshold", 30, RangeValidator(1, 100)))
    param_cfg.addParam(OptionsConfigItem("measure", "transition", "negative", OptionsValidator(["all", "positive", "negative"])))
    param_cfg.addParam(OptionsConfigItem("measure", "select", "first", OptionsValidator(["all", "first", "last"])))
    
    param_cfg.addParam(RangeConfigItem("defect", "distance_min", 0, RangeValidator(0, 100)))
    param_cfg.addParam(RangeConfigItem("defect", "distance_max", 10, RangeValidator(0, 100)))
          
    paramWidget = RecipeUserItemParamWidget()
    paramWidget.addItemType("rotated_caliper_rect", lambda : GraphicsCaliperRotatedRectItem(), CaliperRotatedRectItemSupport())
    
    paramWidget.addParamItem(GraphicsCaliperRectParam("卡尺",param_cfg,"measure.calipers"))
    
    paramWidget.addParamItem(SpinBoxItem("平滑度:",param_cfg,"measure.sigma"))
    paramWidget.addParamItem(SpinBoxItem("阈值:",param_cfg,"measure.threshold"))
    paramWidget.addParamItem(ComboxItem("方向:",param_cfg,"measure.transition"))
    paramWidget.addParamItem(ComboxItem("顺序:",param_cfg,"measure.select"))
    
    paramWidget.addParamItem(SpinBoxItem("最小距离:",param_cfg,"defect.distance_min"))
    paramWidget.addParamItem(SpinBoxItem("最大距离:",param_cfg,"defect.distance_max"))
    
    paramWidget.addEditBtn(HrIcon.RECT,"创建","rotated_caliper_rect",param_cfg,"measure.calipers",Qt.GlobalColor.green)
    paramWidget.addApplyBtn(FIF.APPLICATION,"测试","measure.calipers")
            
    image = QImage("C:/Users/lzh/Desktop/微信图片_20250410143310.bmp")
            
    topDefectDetect = FitLineSegDefect()
    leftDefectDetect = FitLineSegDefect()
    bottomDefectDetect = FitLineSegDefect()
    rightDefectDetect = FitLineSegDefect()
            
    topMeasure = Measure(width=image.width(),height=image.height())
    leftMeasure = Measure(width=image.width(),height=image.height())
    bottomMeasure = Measure(width=image.width(),height=image.height())
    rightMeasure = Measure(width=image.width(),height=image.height())
    
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
            data = param_cfg.get("measure.calipers").calipers_polygon()
            if isinstance(data,dict):
                top = data.get("top", [])
                left = data.get("left", [])
                bottom = data.get("bottom", [])
                right = data.get("right", [])
                
                topMeasure.clear()
                leftMeasure.clear()
                bottomMeasure.clear()
                rightMeasure.clear()
                
                top_lefts, top_rights, bottom_lefts, bottom_rights = polygon_to_points(top, "top")
                topMeasure.add_rectangle2_point(top_left=top_lefts, 
                                                top_right=top_rights, 
                                                bottom_left=bottom_lefts, 
                                                bottom_right=bottom_rights)
                
                top_lefts, top_rights, bottom_lefts, bottom_rights = polygon_to_points(left, "left")
                leftMeasure.add_rectangle2_point(top_left=top_lefts, 
                                                top_right=top_rights, 
                                                bottom_left=bottom_lefts, 
                                                bottom_right=bottom_rights)
                
                top_lefts, top_rights, bottom_lefts, bottom_rights = polygon_to_points(bottom, "bottom")
                bottomMeasure.add_rectangle2_point(top_left=top_lefts, 
                                                top_right=top_rights, 
                                                bottom_left=bottom_lefts, 
                                                bottom_right=bottom_rights)
                
                top_lefts, top_rights, bottom_lefts, bottom_rights = polygon_to_points(right, "right")
                rightMeasure.add_rectangle2_point(top_left=top_lefts, 
                                                top_right=top_rights, 
                                                bottom_left=bottom_lefts, 
                                                bottom_right=bottom_rights)
                
                rect = param_cfg.get(key).rect
                
                topDefectDetect.set_line((rect.topLeft().x(), rect.topLeft().y()),
                                        (rect.topRight().x(), rect.topRight().y()))
                leftDefectDetect.set_line((rect.topLeft().x(), rect.topLeft().y()),
                                        (rect.bottomLeft().x(), rect.bottomLeft().y()))
                bottomDefectDetect.set_line((rect.bottomLeft().x(), rect.bottomLeft().y()),
                                        (rect.bottomRight().x(), rect.bottomRight().y()))
                rightDefectDetect.set_line((rect.bottomRight().x(), rect.bottomRight().y()),
                                        (rect.topRight().x(), rect.topRight().y()))
                
                topDefectDetect.set_measure(topMeasure)
                leftDefectDetect.set_measure(leftMeasure)
                bottomDefectDetect.set_measure(bottomMeasure)
                rightDefectDetect.set_measure(rightMeasure)
                npImage = qimage_to_ndarray(img)
                
                topResult = topDefectDetect.run(npImage,
                                    limit_distance=(param_cfg.get("defect.distance_min"), param_cfg.get("defect.distance_max")),
                                    measure_sigma=param_cfg.get("measure.sigma"),
                                    measure_threshold=param_cfg.get("measure.threshold"),
                                    measure_transition=param_cfg.get("measure.transition"),
                                    measure_select=param_cfg.get("measure.select"))
                leftResult = leftDefectDetect.run(npImage,
                                    limit_distance=(param_cfg.get("defect.distance_min"), param_cfg.get("defect.distance_max")),
                                    measure_sigma=param_cfg.get("measure.sigma"),
                                    measure_threshold=param_cfg.get("measure.threshold"),
                                    measure_transition=param_cfg.get("measure.transition"),
                                    measure_select=param_cfg.get("measure.select"))
                bottomResult = bottomDefectDetect.run(npImage,
                                    limit_distance=(param_cfg.get("defect.distance_min"), param_cfg.get("defect.distance_max")),
                                    measure_sigma=param_cfg.get("measure.sigma"),
                                    measure_threshold=param_cfg.get("measure.threshold"),
                                    measure_transition=param_cfg.get("measure.transition"),
                                    measure_select=param_cfg.get("measure.select"))
                rightResult = rightDefectDetect.run(npImage,
                                    limit_distance=(param_cfg.get("defect.distance_min"), param_cfg.get("defect.distance_max")),
                                    measure_sigma=param_cfg.get("measure.sigma"),
                                    measure_threshold=param_cfg.get("measure.threshold"),
                                    measure_transition=param_cfg.get("measure.transition"),
                                    measure_select=param_cfg.get("measure.select"))
                
                pos = []
                for item in topResult.get("defect", []):
                    pos.append((item[0], item[1], False))
                for item in topResult.get("other", []):
                    pos.append((item[0], item[1], True))
                for item in leftResult.get("defect", []):
                    pos.append((item[0], item[1], False))
                for item in leftResult.get("other", []):
                    pos.append((item[0], item[1], True))
                for item in bottomResult.get("defect", []):
                    pos.append((item[0], item[1], False))
                for item in bottomResult.get("other", []):
                    pos.append((item[0], item[1], True))
                for item in rightResult.get("defect", []):
                    pos.append((item[0], item[1], False))
                for item in rightResult.get("other", []):
                    pos.append((item[0], item[1], True))
                    
                w2.updateResult(pageName, pos)
                
    paramWidget.applySignal.connect(test)
    
    w2.addResultItemSignal.connect(addResultEvent)
    w2.clearResultItemSignal.connect(clearResultEvent)
    
    w2.addCamera(pageName,paramWidget)
    w2.setStyleSheet('''QWidget{background-color: rgb(32, 32, 32);}''')
    w2.show()
    
    w2.updateImage(pageName,image)
    
    app.exec()