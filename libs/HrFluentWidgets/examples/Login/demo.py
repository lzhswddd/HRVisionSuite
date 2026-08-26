import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtGui import  QPixmap
from PySide6.QtWidgets import QApplication, QWidget
from hrfluentwidgets import LoginWidget,LoginWidgetWithRole
from hrfluentwidgets import HrIcon




if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    def verify(username,password):
        if username == "admin" and password == "123456":
            return True,"欢迎您："+username,
        else:
            return False,"用户名或密码错误"

    widget = QWidget()
    def afterLogin():
        widget.show()
        print("登录成功")

    def afterLoginWithRole(role):
        widget.show()
        print("登录成功",role)

    demo = LoginWidget()
    demo.setTitile("英锐捷-AOI视觉系统")
    demo.setIcon(HrIcon.HRICON.icon())
    demo.setBackgroundImage(QPixmap(":/resource/images/test.jpg"))
    demo.setLogoImage(HrIcon.HRICON.icon().pixmap(100,100))
    demo.verifayFun = verify
    demo.afterLoginFun = afterLogin
    demo.show()



    demo2 = LoginWidgetWithRole()
    demo2.setTitile("英锐捷-AOI视觉系统")
    demo2.setIcon(HrIcon.HRICON.icon())
    demo2.setBackgroundImage(QPixmap(":/resource/images/test.jpg"))
    demo2.setLogoImage(HrIcon.HRICON.icon().pixmap(100,100))
    demo2.setRoleList(["操作员","工程师","厂商"])
    demo2.verifayFun = verify
    demo2.afterLoginFun = afterLoginWithRole
    demo2.show()
    app.exec()