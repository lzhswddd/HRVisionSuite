import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import Qt
from PySide6.QtGui import  QPixmap
from PySide6.QtWidgets import QApplication, QWidget
from hrfluentwidgets import CalibrationBase,CalibrationType
from hrfluentwidgets import HrIcon
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import setTheme,setThemeColor,Theme



if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    widget = CalibrationBase()
    widget.setStyleSheet('''
                         QWidget{background-color: rgb(32, 32, 32);}
            
    ''')
    widget.addCalibrationWidget("camera-1",CalibrationType.CHESSBOARD)
    widget.addCalibrationWidget("camera-2",CalibrationType.CHESSBOARD)
    widget.addCalibrationWidget("camera-3",CalibrationType.CHESSBOARD)
    widget.addCalibrationWidget("camera-4",CalibrationType.CHESSBOARD)
    widget.addCalibrationWidget("camera-5",CalibrationType.CHESSBOARD)
    widget.addCalibrationWidget("camera-6",CalibrationType.NINE_POINT)
    widget.show()
    app.exec()