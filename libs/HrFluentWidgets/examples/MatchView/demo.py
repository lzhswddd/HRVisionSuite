import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

import HRVision.Algorithm.Match
import HRVision.Controller
import HRVision.Controller.ProcessQt

import HRVision.Algorithm
from PySide6.QtCore import Qt,QPointF,QLineF
from PySide6.QtGui import QImage,QPolygonF,QTransform,QPainter
from PySide6.QtWidgets import QApplication
from hrfluentwidgets import RecipeUserItemWithViewParamWidget
from hrfluentwidgets import HrIcon
from qfluentwidgets import FluentIcon as FIF,setTheme,Theme
from hrfluentwidgets import RecipeMatchInterface
from hrfluentwidgets import setting_cfg
from hrfluentwidgets import param_cfg
from qfluentwidgets import RangeConfigItem,RangeValidator


from hrfluentwidgets import(
    SpinBoxItem,
    GraphicsRectItem,RectItemSupport,
    RectItemData,GraphicsRotatedRectItem,RotatedRectItemSupport,
    RectItemConfigItem,RotatedRectItemData,RotatedRectItemConfigItem
)

def reduce_image(image: QImage, polygon: QPolygonF) -> QImage:
    line_width = QLineF(polygon[0], polygon[1])
    line_height = QLineF(polygon[1], polygon[2])
    center = QPointF(0, 0)
    for i in range(4):
        center += polygon[i]
    center = QPointF(center.x() / 4, center.y() / 4)
    angle = line_width.angle()
    transform = QTransform()
    transform.translate(line_width.length() / 2, line_height.length() / 2)
    transform.rotate(angle)
    transform.translate(-center.x(), -center.y())

    new_image = QImage(line_width.length(), line_height.length(), image.format())
    painter = QPainter(new_image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setTransform(transform)
    painter.drawImage(QPointF(0, 0), image)
    painter.end()

    return new_image

if __name__ == "__main__":
    import HRVision
    import numpy as np
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    
    pageName = "匹配"

    w2 = RecipeMatchInterface(setting_cfg.get(setting_cfg.recipePath))
    w2.setObjectName("recipe")

    param_cfg.addParam(RangeConfigItem("match", "match_scocer", 50, RangeValidator(1, 100)))


    param_cfg.addParam(RectItemConfigItem("match", "search",RectItemData()))
    param_cfg.addParam(RotatedRectItemConfigItem("match", "template", RotatedRectItemData()))
    
    paramWidget = RecipeUserItemWithViewParamWidget()
    paramWidget.addItemType("rect", lambda : GraphicsRectItem(), RectItemSupport())
    paramWidget.addItemType("rotated_rect", lambda : GraphicsRotatedRectItem(), RotatedRectItemSupport())
    paramWidget.addParamItem(SpinBoxItem("匹配分数:",param_cfg,"match.match_scocer"))
    
    paramWidget.addEditBtn(HrIcon.RECT,"搜索框","rect",param_cfg,"match.search",Qt.GlobalColor.green)
    paramWidget.addEditBtn(HrIcon.RECT,"模板框","rotated_rect",param_cfg,"match.template",Qt.GlobalColor.yellow)

    paramWidget.addApplyBtn(FIF.APPLICATION,"模板创建","match.template")
    paramWidget.addApplyBtn(FIF.APPLICATION,"模板测试","match.search")
    paramWidget.addApplyBtn(FIF.APPLICATION,"模板配准","match.reference")

    matchModel = HRVision.Algorithm.Match.ScaledShapeMatch()
    def test(key:str,img:QImage):
        if key == "match.template":
            data:RotatedRectItemData = param_cfg.get("match.template")
            img = reduce_image(img, data.polygon())
            matchModel.create_model(HRVision.Controller.ProcessQt.qimage_to_ndarray(img))
            paramWidget.updateMatchViewImage(img)
        elif key == "match.search":
           if matchModel.model_id is not None:
                data :RectItemData = param_cfg.get("match.search")
                if not data.rect.isNull():
                    matchModel.search_region = [data.rect.top(), data.rect.left(), data.rect.bottom(), data.rect.right()]
                result = matchModel.find_model(HRVision.Controller.ProcessQt.qimage_to_ndarray(img))
                if result is not None:
                    rows, cols, angles, scales, scores = result
                    if len(scores) > 0:
                        print("匹配成功")
                        pos = []
                        for i in range(len(rows)):
                            pos.append((cols[i], rows[i], True))
                        w2.updateMatchResult(pageName, pos)
                    else:
                        print("匹配失败")
                else:
                    print("匹配失败") 
        elif key == "match.reference":
            if matchModel.model_id is not None:
                rows, cols, angles, scales, scores = matchModel.find_model(HRVision.Controller.ProcessQt.qimage_to_ndarray(img))
                data:RotatedRectItemData = param_cfg.get("match.template")
                data.rect.moveCenter(QPointF(cols[0], rows[0]))
                data.rotation = -np.rad2deg(angles[0])
                paramWidget.setItemUserData("match.template", data)

    paramWidget.applySignal.connect(test)
    w2.addCamera(pageName,paramWidget)
    w2.setStyleSheet('''QWidget{background-color: rgb(32, 32, 32);}''')
    w2.show()
    
    image = QImage(r"C:\Users\lzh\Desktop\jiaokou\2025-05-28\20250528010819230.jpg")
    # image = QImage(r"C:\Users\14394\Desktop\dmp\浇口\20250528010822987.jpg")
    w2.updateImage(pageName, image)
    
    app.exec()