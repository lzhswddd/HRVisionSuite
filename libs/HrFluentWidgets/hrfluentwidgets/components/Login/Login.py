import sys
from PySide6.QtCore  import Qt,QRect,QSize
from PySide6.QtGui import QColor,QPixmap,QPainter
from PySide6.QtWidgets import QApplication,QHBoxLayout,QLabel,QWidget,QSizePolicy,QVBoxLayout,QSpacerItem
from qfluentwidgets import SplitTitleBar,BodyLabel,LineEdit,PrimaryPushButton,PasswordLineEdit,isDarkTheme,setThemeColor
from qfluentwidgets import InfoBar,InfoBarPosition,ComboBox
from ...common import SvgLabel

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


if isWin11():
    from qframelesswindow import AcrylicWindow as Window
else:
    from qframelesswindow import FramelessWindow as Window

class LoginWidget(Window):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.verifayFun = None
        self.afterLoginFun = None
        
        self.initUI()

        self.loginBtn.clicked.connect(self.loginClicked)

    def setTitile(self,title):
        self.setWindowTitle(title)
    
    def setIcon(self,icon):
        self.setWindowIcon(icon)

    def setBackgroundImage(self, svgPath:str):
        self.bgLabel.setSvg(svgPath)

    def setLogoImage(self,img):
        self.logoLabel.setPixmap(img)

    def initUI(self):
        self.setMinimumSize(QSize(700, 500))
        self.horizontalLayout = QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)

        self.bgLabel = SvgLabel(self)
        self.bgLabel.setScaledContents(False)
        self.bgLabel.setSvg(':/resource/images/login_bg.svg')
        self.horizontalLayout.addWidget(self.bgLabel)

        self.widget = QWidget(self)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QSize(360, 0))
        self.widget.setMaximumSize(QSize(360, 16777215))
        self.widget.setStyleSheet("QLabel{\n"
        "    font: 13px \'Microsoft YaHei\'\n"
        "}")

        self.verticalLayout_2 = QVBoxLayout(self.widget)
        self.verticalLayout_2.setContentsMargins(20, 20, 20, 20)
        self.verticalLayout_2.setSpacing(9)
        self.verticalLayout_2.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.logoLabel = QLabel(self.widget)
        self.logoLabel.setMinimumSize(QSize(100, 100))
        self.logoLabel.setMaximumSize(QSize(100, 100))
        self.logoLabel.setScaledContents(True)
        self.verticalLayout_2.addWidget(self.logoLabel, 0, Qt.AlignHCenter)
        self.verticalLayout_2.addItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.verticalLayout_2.addWidget(BodyLabel('用户名', self.widget), 0, Qt.AlignmentFlag.AlignLeft)
        self.userLineEdit = LineEdit(self.widget)
        self.verticalLayout_2.addWidget(self.userLineEdit)
        self.verticalLayout_2.addItem(QSpacerItem(20, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.verticalLayout_2.addWidget(BodyLabel('密码', self.widget), 0, Qt.AlignmentFlag.AlignLeft)
        self.passwordLineEdit = PasswordLineEdit(self.widget)
        self.verticalLayout_2.addWidget(self.passwordLineEdit)
        self.verticalLayout_2.addItem(QSpacerItem(20, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.loginBtn = PrimaryPushButton('登录', self.widget)
        self.verticalLayout_2.addWidget(self.loginBtn)    
        self.verticalLayout_2.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.horizontalLayout.addWidget(self.widget)

        # self.verticalLayout_2.addWidget(BodyLabel('© 2023 版权所有', self.widget), 0, Qt.AlignmentFlag.AlignCenter)
        setThemeColor('#28afe9')

        self.resize(1250, 820)
        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()
        self.windowEffect.setMicaEffect(self.winId(), isDarkMode=isDarkTheme())
        if not isWin11():
            color = QColor(25, 33, 42) if isDarkTheme() else QColor(240, 244, 249)
            self.setStyleSheet(f"LoginWidget{{background: {color.name()}}}")

        if sys.platform == "darwin":
            self.setSystemTitleBarButtonVisible(True)
            self.titleBar.minBtn.hide()
            self.titleBar.maxBtn.hide()
            self.titleBar.closeBtn.hide()

        self.titleBar.titleLabel.setStyleSheet("""
            QLabel{
                background: transparent;
                font: 13px 'Segoe UI';
                padding: 0 4px;
                color: white
            }
        """)
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
    
    def systemTitleBarRect(self, size):
        """ Returns the system title bar rect, only works for macOS """
        return QRect(size.width() - 75, 0, 75, size.height())
        
    def loginClicked(self):
        ret,message = self.callVerify()
        self.passwordLineEdit.clear()
        # 登录成功后调用afterLoginFun
        if ret:
                InfoBar.success(title="登录成功",content = message, position=InfoBarPosition.TOP,isClosable=False,duration=3000,parent=self)
                self.hide()
                self.callAfterLogin()
        else:
            InfoBar.warning(title="登录失败", content=message, position=InfoBarPosition.TOP,isClosable=False,duration=3000,parent=self)

    def callVerify(self):
        if self.verifayFun is not None:
            ret,message = self.verifayFun(self.userLineEdit.text(),self.passwordLineEdit.text())
            return ret,message
        else:
            print("未设置验证函数,verifayFun is None")
            return False,"未设置验证函数,verifayFun is None"
    
    def callAfterLogin(self):
        if self.afterLoginFun is not None:
            self.afterLoginFun()

class LoginWidgetWithRole(LoginWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.addui()

    def addui(self):
        self.verticalLayout_2.insertWidget(3,BodyLabel('角色',  self.widget), 0, Qt.AlignmentFlag.AlignLeft)
        self.roleComboBox = ComboBox(self.widget)
        self.verticalLayout_2.insertWidget(4,self.roleComboBox)
        self.verticalLayout_2.insertItem(5,QSpacerItem(20, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

    def setRoleList(self,roleList):
        self.roleComboBox.clear()
        self.roleComboBox.addItems(roleList)
    
    def callAfterLogin(self):
        if self.afterLoginFun is not None:
            self.afterLoginFun(self.roleComboBox.currentIndex())