import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF
from hrfluentwidgets import LogWidget

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    demo = LogWidget()
    demo.setWindowTitle("LogWidget")
    demo.show()
    app.exec()