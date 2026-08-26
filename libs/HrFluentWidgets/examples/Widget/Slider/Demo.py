import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF
from hrfluentwidgets import RangeSlider

class Demo(QWidget):
    def __init__(self):
        super().__init__()

        self.slider1 = RangeSlider(Qt.Orientation.Horizontal, self)
        self.slider1.setFixedWidth(300)
        self.slider1.move(100, 30)
        self.slider1.setRangeStart(20)
        self.slider1.setRangeEnd(80)

        self.slider2 = RangeSlider(Qt.Orientation.Vertical, self)
        self.slider2.setFixedHeight(300)
        self.slider2.move(240, 160)

        self.slider2.rangeChanged.connect(lambda start, end: print("range:",start, end))
        self.slider2.rangeStartChanged.connect(lambda start: print("strat:",start))
        self.slider2.rangeEndChanged.connect(lambda end: print("end:",end))
        self.slider2.valueChanged.connect(lambda value: print("value:",value))

        self.resize(500, 500)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    app.exec()