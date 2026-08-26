import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QImage,QPolygon,QPolygonF,QPixmap
from PySide6.QtWidgets import QApplication, QWidget
from hrfluentwidgets import LoginWidget,LoginWidgetWithRole,AoiWindow,DetectInterface,SettingInterface,RecipeParamWithViewWidget,RecipeUserItemWithViewParamWidget
from hrfluentwidgets import HrIcon
from qfluentwidgets import FluentIcon as FIF,setTheme,Theme,NavigationItemPosition
from hrfluentwidgets import (CalibrationBase,CalibrationType,RecipeInterface,RecipeParamWidget)
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
    GraphicsCaliperRectParam, CaliperRectItemData, CaliperRectItemConfigItem,
    GraphicsRectItem, RectItemSupport, GraphicsCaliperRectItem, CaliperRectItemSupport, 
)

from hrfluentwidgets import log
from hrfluentwidgets.motion import IoOptionWidget, IoWatchWidget
import pandas as pd

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    
    cameraList = ["camera-1","camera-2","camera-3","camera-4","camera-5"]

    # param_cfg.addParam(ConfigItem("Vision", "ImageSavePath", "D:/VisionImage", FolderValidator()))
    # param_cfg.addParam(ConfigItem("Vision", "SourceImageSaveChecked", True, BoolValidator()))
    # param_cfg.addParam(ConfigItem("Vision", "CalibrationPath", "D:/VisionImage/Calibration", FolderValidator()))
    # param_cfg.addParam(ConfigItem("Vision", "RecipePath", "D:/VisionImage/Recipe", FolderValidator()))
    # param_cfg.addParam(ConfigItem("PlcSetting", "PlcIp","192.168.0.14"))
    # param_cfg.addParam(ConfigItem("solfware", "AutoStart", True, BoolValidator()))

    w1 = DetectInterface()
    w1.setObjectName("detect")
    w1.setCameraList(cameraList,2,3)
    w1.initLayout()
    w1.updateCameraImage("camera-1",QImage(":/resource/images/test.jpg"))

    w2 = RecipeInterface(setting_cfg.get(setting_cfg.recipePath),)
    w2.setObjectName("recipe")

    param_cfg.addParam(RangeConfigItem("camera-1", "match_scocer", 0, RangeValidator(0, 40)))
    param_cfg.addParam(RangeValueConfigItem("camera-1", "aera", [0,0], RangeValueValidator(0, 100), RangeValueSerializer()))
    param_cfg.addParam(RangeConfigItem("camera-1", "test", 0.0, RangeValidator(0, 1)))
    param_cfg.addParam(RangeValueConfigItem("camera-1", "test2", [0.0,0.0], RangeValueValidator(0, 100), RangeValueSerializer()))
    param_cfg.addParam(ConfigItem("camera-1", "test4", True, BoolValidator()))
    param_cfg.addParam(OptionsConfigItem("camera-1", "test5", "算法2", OptionsValidator(["算法1","算法2","算法3"])))

    param_cfg.addParam(RangeConfigItem("camera-1", "match_scocer1", 0.0, RangeValidator(0, 40)))
    param_cfg.addParam(RangeValueConfigItem("camera-1", "aera1", [0.0,0.0], RangeValueValidator(0, 100), RangeValueSerializer()))
    param_cfg.addParam(RangeConfigItem("camera-1", "test1",0.0, RangeValidator(0, 1)))
    param_cfg.addParam(RangeValueConfigItem("camera-1", "test21", [0.0,0.0], RangeValueValidator(0, 100), RangeValueSerializer()))
    param_cfg.addParam(ConfigItem("camera-1", "test41", True, BoolValidator()))
    param_cfg.addParam(OptionsConfigItem("camera-1", "test51", "算法2", OptionsValidator(["算法1","算法2","算法3"])))


    param_cfg.addParam(RangeConfigItem("camera-2", "match_scocer", 0.0, RangeValidator(0, 40)))
    param_cfg.addParam(RangeValueConfigItem("camera-2", "aera", [0.0,0.0], RangeValueValidator(0, 100), RangeValueSerializer()))
    param_cfg.addParam(RangeConfigItem("camera-2", "test", 0.0, RangeValidator(0, 1)))


    param_cfg.addParam(RectItemConfigItem("camera-2", "roi1",RectItemData()))
    param_cfg.addParam(RectItemConfigItem("camera-2", "roi2",RectItemData()))
    param_cfg.addParam(RectItemConfigItem("camera-2", "roi3",RectItemData()))
    param_cfg.addParam(RectItemConfigItem("camera-2", "roi4",RectItemData()))
    param_cfg.addParam(RectItemConfigItem("camera-2", "roi5",RectItemData()))

    param_cfg.addParam(PolygonItemConfigItem("camera-2", "polygon", PolygonItemData()))
    
    param_cfg.addParam(RectItemConfigItem("camera-3", "roi1", RectItemData()))
    param_cfg.addParam(CaliperRectItemConfigItem("camera-3", "calipers", CaliperRectItemData()))
    param_cfg.addParam(RangeConfigItem("camera-3.calipers", "caliperRect-width", 5, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("camera-3.calipers", "caliperRect-height", 20, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("camera-3.calipers", "caliperRect-gap", 5, RangeValidator(1, 100)))
    param_cfg.addParam(RangeConfigItem("camera-3.calipers", "caliperRect-offset", 5, RangeValidator(1, 100)))
    
    for cam in cameraList:
        if cam == "camera-1":
            parawidget = RecipeParamWidget()
            parawidget.addParamItem(SpinBoxItem("匹配分数:",param_cfg,"camera-1.match_scocer"))
            parawidget.addParamItem(RangeSpinBoxItem("面积(mm):",param_cfg,"camera-1.aera"))
            parawidget.addParamItem(DoubleSpinBoxItem("小数测试(mm):",param_cfg,"camera-1.test"))
            parawidget.addParamItem(RangeDoubleSpinBoxItem("小数rangeTest(mm):",param_cfg,"camera-1.test2"))
            parawidget.addParamItem(SwitchItem("是否开启算法:",param_cfg,"camera-1.test4"))
            parawidget.addParamItem(ComboxItem("算法选择:",param_cfg,"camera-1.test5"))

            parawidget.addParamItem(SpinBoxItem("匹配分数1:",param_cfg,"camera-1.match_scocer1"))
            parawidget.addParamItem(RangeSpinBoxItem("面积(mm)1:",param_cfg,"camera-1.aera1"))
            parawidget.addParamItem(DoubleSpinBoxItem("小数测试(mm)1:",param_cfg,"camera-1.test1"))
            parawidget.addParamItem(RangeDoubleSpinBoxItem("小数rangeTest(mm)1:",param_cfg,"camera-1.test21"))
            parawidget.addParamItem(SwitchItem("是否开启算法1:",param_cfg,"camera-1.test41"))
            parawidget.addParamItem(ComboxItem("算法选择1:",param_cfg,"camera-1.test51"))


            # parawidget.addEditItem(editBtn)


            w2.addCamera(cam,parawidget)

        elif cam == "camera-2":
            paramWidget = RecipeParamWithViewWidget()
            paramWidget.addParamItem(SpinBoxItem("匹配分数:",param_cfg,"camera-2.match_scocer"))
            paramWidget.addParamItem(RangeSpinBoxItem("面积(mm):",param_cfg,"camera-2.aera"))
            paramWidget.addParamItem(DoubleSpinBoxItem("小数测试(mm):",param_cfg,"camera-2.test"))
           
           
           
            paramWidget.addEditBtn(HrIcon.RECT,"ROI1","rect",param_cfg,"camera-2.roi1",Qt.GlobalColor.green)
            paramWidget.addEditBtn(HrIcon.RECT,"ROI2","rect",param_cfg,"camera-2.roi2",Qt.GlobalColor.yellow)
            paramWidget.addEditBtn(HrIcon.RECT,"ROI3","rect",param_cfg,"camera-2.roi3",Qt.GlobalColor.red)
            paramWidget.addEditBtn(HrIcon.RECT,"ROI4","rect",param_cfg,"camera-2.roi4",Qt.GlobalColor.blue)
            paramWidget.addEditBtn(HrIcon.RECT,"ROI5","rect",param_cfg,"camera-2.roi5",Qt.GlobalColor.cyan)

            paramWidget.addApplyBtn(FIF.APPLICATION,"模板测试","camera-2.roi5")
            paramWidget.addApplyBtn(HrIcon.RECT,"创建ROI","测试")

            def test(key:str,img:QImage,data:object):
                # print(key)
                # print(img)
                # print(polygon)
                #将img 按照polygon裁切
                if data is None:
                    return
                if isinstance(data,QPolygonF):
                    img = img.copy(data.boundingRect().toRect())
                elif isinstance(data,QRectF):
                    img = img.copy(data.toRect())
                paramWidget.updateMatchViewImage(img)

            paramWidget.applySignal.connect(test)
            paramWidget.addEditBtn(HrIcon.POLYGON,"多边形","polygon",param_cfg,"camera-2.polygon",Qt.GlobalColor.cyan)
            w2.addCamera(cam,paramWidget)
        elif cam == "camera-3":
            paramWidget1 = RecipeUserItemWithViewParamWidget()
            paramWidget1.addItemType("rect", lambda: GraphicsRectItem(), RectItemSupport())
            paramWidget1.addItemType("caliper_rect", lambda: GraphicsCaliperRectItem(), CaliperRectItemSupport())
            
            def test(key:str,img:QImage):
                if key == "camera-3.roi1":
                    data:RectItemData = param_cfg.get("camera-3.roi1")
                    if not data.rect.isNull():
                        img = img.copy(data.rect.toRect())
                        paramWidget.updateMatchViewImage(img)

            paramWidget1.addParamItem(GraphicsCaliperRectParam("卡尺",param_cfg,"camera-3.calipers"))
            paramWidget1.addEditBtn(HrIcon.RECT,"创建匹配框","rect",param_cfg,"camera-3.roi1",Qt.GlobalColor.green)
            paramWidget1.addEditBtn(HrIcon.RECT,"创建卡尺","caliper_rect",param_cfg,"camera-3.calipers",Qt.GlobalColor.yellow)
            paramWidget.addApplyBtn(FIF.APPLICATION,"测试","camera-3.roi1")

            w2.addCamera(cam,paramWidget1)
        else:
            w2.addCamera(cam,RecipeParamWidget())

    w3 = QWidget()
    w3.setObjectName("w3")

    w4 = SettingInterface()
    try:
        df = pd.read_excel('input_ioconfig.xlsx')
        names = df['Name']
        ios = df['IO']
        w4.setInputConfig((names, ios))
        df = pd.read_excel('output_ioconfig.xlsx')
        names = df['Name']
        ios = df['IO']
        w4.setOutputConfig((names, ios))
    except FileNotFoundError: 
        pass
    
    w4.setIoOptionWidget(IoOptionWidget)
    w4.setIoWatchWidget(IoWatchWidget)
    w4.setObjectName("settingInterface")

    w5 = CalibrationBase()
    w5.setObjectName("calibration")
    for cam in cameraList:
        w5.addCalibrationWidget(cam,random.choice([CalibrationType.CHESSBOARD, CalibrationType.NINE_POINT]))
        w5.updateCalibrationLog(cam,cam)

    posList = [QPointF(100,100),QPointF(100,200),QPointF(200,100),QPointF(200,200),QPointF(300,100),QPointF(300,200)]
    w5.updateCrossItems("camera-2",posList)
    w5.updateCrossItems("camera-1",posList)

    login = LoginWidgetWithRole()
    
    window = AoiWindow()
    #验证函数
    def verify(username,password):
        if username == "admin" and password == "123456":
            return True,"欢迎您："+username,
        else:
            return False,"用户名或密码错误"
        
    def onExitClicked():
        window.hide()
        login.show()

    window.setWindowIcon(HrIcon.HRICON.icon())
    window.setWindowTitle("英锐捷-AOI视觉系统")
    window.addSubInterface(w1, FIF.HOME, '检测',Role= 0)
    window.addSubInterface(w2, FIF.APPLICATION, '工单',Role= 1)
    window.addSubInterface(w3, FIF.VIDEO, '数据',Role= 1)
    window.addSubInterface(w4, FIF.SETTING, '设置',Role= 2,position=NavigationItemPosition.BOTTOM)
    window.addSubInterface(w5, FIF.APPLICATION, '标定',Role= 2)


       
    window.navigationInterface.addItem(
            routeKey='exit',
            icon=FIF.PEOPLE,
            text='账户退出',
            onClick=onExitClicked,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )

    # loop.exec()
    # window.show()

    #登录成功后调用的函数
    def afterLoginWithRole(role):
        # loop = QEventLoop()
        # QTimer.singleShot(3000, loop.quit)
        
        # window.setRole(role)
        # window.setWindowIcon(HrIcon.HRICON.icon())
        # window.setWindowTitle("英锐捷-AOI视觉系统")
        # window.addSubInterface(w1, FIF.HOME, '检测',Role= 0)
        # window.addSubInterface(w2, FIF.APPLICATION, '工单',Role= 1)
        # window.addSubInterface(w3, FIF.VIDEO, '数据',Role= 1)
        # window.addSubInterface(w4, FIF.SETTING, '设置',Role= 2,position=NavigationItemPosition.BOTTOM)
        # window.addSubInterface(w5, FIF.APPLICATION, '标定',Role= 2)

        # # loop.exec()
        # window.show()
        window.setRole(role)
        window.show()
        # w5.updateImage("camera-1",QImage("C:\\Users\\sr\\OneDrive\\Desktop\\执照.jpg"))
        # w5.updateImage("camera-2",QImage("C:\\Users\\sr\\OneDrive\\Desktop\\执照.jpg"))
        # w5.updateImage("camera-3",QImage("C:\\Users\\sr\\OneDrive\\Desktop\\执照.jpg"))

    login.setTitile("英锐捷-AOI视觉系统")
    login.setIcon(HrIcon.HRICON.icon())
    login.setLogoImage(HrIcon.HRICON.icon().pixmap(100,100))
    login.setRoleList(["操作员","工程师","厂商","超级管理员"])
    login.verifayFun = verify
    login.afterLoginFun = afterLoginWithRole
    login.show()
    
    # afterLoginWithRole(2)

    log.info("hello world")
    log.warning("hello world")
    
    app.exec()