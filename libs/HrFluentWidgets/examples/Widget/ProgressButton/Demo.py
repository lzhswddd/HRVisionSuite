import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme
from hrfluentwidgets import ProgressPushButton

if __name__ == "__main__":
    app = QApplication(sys.argv)

    setTheme(Theme.DARK)
    
    def clicked():
        print("Button clicked!")
        widget.load()
        QTimer.singleShot(2000, lambda: widget.reset())
    
    widget = ProgressPushButton('测试')
    widget.clicked.connect(clicked)
    widget.show()
    sys.exit(app.exec())