import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from hrfluentwidgets import DropDownColorPalette, DropDownColorPicker, ColorPickerDialog
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import setTheme, Theme

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    
    window = QWidget()
    window.setWindowTitle("DropDown Color Palette Example")
    window.setStyleSheet("background-color: #2d2d2d;")
    
    window.show()
    
    dialog = ColorPickerDialog(QColor(255, 0, 0), 'test', window, True)
    dialog.exec()
    
    widget = DropDownColorPicker()
    widget.setColor(dialog.color())
    
    widget1 = DropDownColorPalette()
    widget1.setColor(dialog.color())
    
    layout = QVBoxLayout(window)
    layout.addWidget(widget)
    layout.addWidget(widget1)
    
    window.show()
    sys.exit(app.exec())