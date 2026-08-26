
from qfluentwidgets import ToolButton
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QPainterPath, QIcon
from PySide6.QtCore import Signal, QRect, QRectF, Qt
from qfluentwidgets import FlyoutAnimationType, isDarkTheme, FluentIcon, Theme, setTheme, drawIcon, ColorDialog
from qfluentwidgets import FlyoutViewBase, PushButton, BodyLabel, Flyout
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

class DefaultColorWidget(PushButton):
    def __init__(self, parent: QWidget = None, color: QColor = QColor(0, 0, 0)):
        super().__init__(parent)
        self.color_ = color
        self.setFixedHeight(42)

    def color(self) -> QColor:
        return self.color_

    def setColor(self, color: QColor):
        self.color_ = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.addRoundedRect(self.rect(), 8, 8)
        path.addRect(0, self.height() - 8, 8, 8)
        path.addRect(self.width() - 8, self.height() - 8, 8, 8)
        painter.setClipPath(path)

        # Draw background color
        painter.setPen(Qt.PenStyle.NoPen)
        isDark = isDarkTheme()
        if self.isDown():
            painter.setBrush(QColor(255, 255, 255, 6) if isDark else QColor(0, 0, 0, 6))
        elif self.underMouse():
            painter.setBrush(QColor(255, 255, 255, 9) if isDark else QColor(0, 0, 0, 9))

        painter.drawRect(self.rect())

        # Draw default color
        painter.setBrush(self.color_)
        painter.drawRoundedRect(12, 8, 28, 28, 3, 3)

        # Draw text
        painter.setFont(self.font())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(255, 255, 255) if isDark else QColor(0, 0, 0))
        painter.drawText(self.rect().translated(52, 0), Qt.AlignmentFlag.AlignVCenter, "Automatic")

class MoreColorWidget(PushButton):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setFixedHeight(42)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.addRoundedRect(self.rect(), 8, 8)
        path.addRect(0, 0, 8, 8)
        path.addRect(self.width() - 8, 0, 8, 8)
        painter.setClipPath(path)

        # Draw background color
        painter.setPen(Qt.PenStyle.NoPen)
        isDark = isDarkTheme()
        if self.isDown():
            painter.setBrush(QColor(255, 255, 255, 6) if isDark else QColor(0, 0, 0, 6))
        elif self.underMouse():
            painter.setBrush(QColor(255, 255, 255, 9) if isDark else QColor(0, 0, 0, 9))

        painter.drawRect(self.rect())

        # Draw icon
        FluentIcon(FluentIcon.PALETTE).render(painter, QRectF(16, 11, 20, 20))

        # Draw text
        painter.setFont(self.font())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(255, 255, 255) if isDark else QColor(0, 0, 0))
        painter.drawText(self.rect().translated(52, 0), Qt.AlignmentFlag.AlignVCenter, "More Colors...")

class PaletteSeparatorWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setFixedHeight(2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if isDarkTheme():
            painter.setPen(QColor(255, 255, 255, 22))
        else:
            painter.setPen(QColor(0, 0, 0, 22))

        painter.drawLine(1, 1, self.width() - 2, 1)

class PaletteColorCard(ToolButton):
    cardClicked = Signal(QColor)

    def __init__(self, color: QColor, parent: QWidget = None):
        super().__init__(parent)
        self.color_ = color
        self.isSelected_ = False
        self.underMouse_ = False
        self.setFixedSize(28, 28)
        self.clicked.connect(lambda: self.cardClicked.emit(self.color_))

    def setSelected(self, isSelected: bool):
        if isSelected == self.isSelected_:
            return

        self.isSelected_ = isSelected
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isSelected_:
            painter.setPen(QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

            painter.setBrush(self.color_)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(3, 3, -3, -3), 3, 3)
        elif self.underMouse_:
            painter.setPen(QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0))
            painter.setBrush(self.color_)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.color_)
            painter.drawRoundedRect(self.rect(), 4, 4)
        painter.end()
        
    def enterEvent(self, e):
        self.underMouse_ = True
        return super().enterEvent(e)
        
    def leaveEvent(self, e):
        self.underMouse_ = False
        return super().leaveEvent(e)
    
class ThemeColorPanel(QWidget):
    colorChanged = Signal(QColor)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.colorCards_ = {}
        self.label_ = BodyLabel("Theme Colors", self)
        self.vBoxLayout_ = QVBoxLayout(self)
        self.colorLayout_ = QVBoxLayout()

        self.setFixedHeight(256)
        self.vBoxLayout_.setContentsMargins(12, 8, 12, 16)
        self.vBoxLayout_.setSpacing(16)
        self.vBoxLayout_.addWidget(self.label_)
        self.vBoxLayout_.addLayout(self.colorLayout_)

        self.colorLayout_.setContentsMargins(0, 0, 0, 0)
        self.colorLayout_.setSpacing(4)

        colors = [
            ["#ffffff", "#000000", "#e7e6e6", "#44546a", "#4472c4", "#4472c4", "#a5a5a5", "#ffc000", "#5b9bd5", "#70ad47"],
            ["#f2f2f2", "#808080", "#d0cece", "#d6dce5", "#dae3f3", "#fbe5d6", "#ededed", "#fff2cc", "#deebf7", "#e2f0d9"],
            ["#d9d9d9", "#595959", "#afabab", "#adb9ca", "#b4c7e7", "#f8cbad", "#dbdbdb", "#ffe699", "#bdd7ee", "#c5e0b4"],
            ["#bfbfbf", "#404040", "#767171", "#8497b0", "#8faadc", "#f4b183", "#c9c9c9", "#ffd966", "#9dc3e6", "#a9d18e"],
            ["#a6a6a6", "#262626", "#3b3838", "#333f50", "#2f5597", "#c55a11", "#7c7c7c", "#bf9000", "#2e75b6", "#548235"],
            ["#808080", "#0d0d0d", "#181717", "#222a35", "#203864", "#843c0b", "#525252", "#806000", "#1f4e79", "#385624"]
        ]

        self.__addColors(colors[0])
        self.colorLayout_.addStretch(8)
        
        for i in range(1, len(colors)):
            self.__addColors(colors[i])

    def __addColors(self, colors: list[str]):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for color in colors:
            card = PaletteColorCard(QColor(color), self)
            card.cardClicked.connect(self.colorChanged)

            hexColor = QColor(color).name(QColor.NameFormat.HexArgb)
            self.colorCards_[hexColor] = card
            layout.addWidget(card)

        self.colorLayout_.addLayout(layout)

    def setColor(self, color: QColor):
        hexColor = color.name(QColor.NameFormat.HexArgb)
        if hexColor not in self.colorCards_:
            return

        for c in self.colorCards_:
            self.colorCards_[c].setSelected(c == hexColor)

class StandardColorPanel(QWidget):
    colorChanged = Signal(QColor)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.colorCards_ = {}
        self.label_ = BodyLabel("Standard Colors", self)
        self.vBoxLayout_ = QVBoxLayout(self)
        self.colorLayout_ = QHBoxLayout()

        self.setFixedHeight(88)
        self.vBoxLayout_.setContentsMargins(12, 8, 12, 16)
        self.vBoxLayout_.setSpacing(8)
        self.vBoxLayout_.addWidget(self.label_)
        self.vBoxLayout_.addLayout(self.colorLayout_)

        self.colorLayout_.setContentsMargins(0, 0, 0, 0)
        self.colorLayout_.setSpacing(4)

        colors = [
            "#c00000", "#ff0000", "#ffc000", "#ffff00", "#92d050",
            "#00b050", "#00b0f0", "#0070c0", "#002060", "#7030a0"
        ]

        for color in colors:
            card = PaletteColorCard(QColor(color), self)
            card.cardClicked.connect(self.colorChanged)

            hexColor = QColor(color).name(QColor.NameFormat.HexArgb)
            self.colorCards_[hexColor] = card
            self.colorLayout_.addWidget(card)

    def setColor(self, color: QColor):
        hexColor = color.name(QColor.NameFormat.HexArgb)
        if hexColor not in self.colorCards_:
            return

        for c in self.colorCards_:
            self.colorCards_[c].setSelected(c == hexColor)

class RecentColorPanel(QWidget):
    colorChanged = Signal(QColor)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.colors_ = []
        self.colorCards_ = {}
        self.label_ = BodyLabel("Recent Colors", self)
        self.vBoxLayout_ = QVBoxLayout(self)
        self.colorLayout_ = QHBoxLayout()

        self.setFixedHeight(76)
        self.vBoxLayout_.setContentsMargins(12, 8, 12, 16)
        self.vBoxLayout_.setSpacing(8)
        self.vBoxLayout_.addWidget(self.label_)
        self.vBoxLayout_.addLayout(self.colorLayout_)

        self.colorLayout_.setContentsMargins(0, 0, 0, 0)
        self.colorLayout_.setSpacing(4)
        self.colorLayout_.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def addColor(self, color: QColor):
        if len(self.colors_) >= 10:
            self.removeColor(QColor(self.colors_[0]))

        hexColor = color.name(QColor.NameFormat.HexArgb)
        card = PaletteColorCard(color, self)
        card.cardClicked.connect(self.colorChanged)

        self.colorCards_[hexColor] = card
        self.colorLayout_.addWidget(card, alignment=Qt.AlignmentFlag.AlignLeft)
        self.colors_.append(hexColor)

    def removeColor(self, color: QColor):
        hexColor = color.name(QColor.NameFormat.HexArgb)
        if hexColor not in self.colorCards_:
            return

        self.colors_.remove(hexColor)
        card = self.colorCards_.pop(hexColor)
        self.colorLayout_.removeWidget(card)
        card.setParent(None)

    def setColors(self, colors: list[QColor]):
        self.clear()
        for color in colors[-10:]:
            self.addColor(color)

    def clear(self):
        while self.colors_:
            self.removeColor(QColor(self.colors_[-1]))

    def setColor(self, color: QColor):
        hexColor = color.name(QColor.NameFormat.HexArgb)
        if hexColor not in self.colorCards_:
            return

        for c in self.colorCards_:
            self.colorCards_[c].setSelected(c == hexColor)

class ColorPaletteView(FlyoutViewBase):
    colorChanged = Signal(QColor)
    def __init__(self, color: QColor, enableAlpha: bool = True, parent: QWidget = None):
        super().__init__(parent)
        self.color_ = color
        self.enableAlpha_ = enableAlpha

        self.vBoxLayout_ = QVBoxLayout(self)
        self.defaultColorWidget_ = DefaultColorWidget(self)
        self.themeColorPanel_ = ThemeColorPanel(self)
        self.standardColorPanel_ = StandardColorPanel(self)
        self.moreColorWidget_ = MoreColorWidget(self)
        self.separator_ = PaletteSeparatorWidget(self)
        self.recentColorPanel_ = RecentColorPanel(self)

        self.vBoxLayout_.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout_.setSpacing(0)
        self.vBoxLayout_.addWidget(self.defaultColorWidget_)
        self.vBoxLayout_.addWidget(PaletteSeparatorWidget(self))
        self.vBoxLayout_.addWidget(self.themeColorPanel_)
        self.vBoxLayout_.addWidget(PaletteSeparatorWidget(self))
        self.vBoxLayout_.addWidget(self.standardColorPanel_)
        self.vBoxLayout_.addWidget(self.separator_)
        self.vBoxLayout_.addWidget(self.recentColorPanel_)
        self.vBoxLayout_.addWidget(PaletteSeparatorWidget(self))
        self.vBoxLayout_.addWidget(self.moreColorWidget_)

        self.separator_.hide()
        self.recentColorPanel_.hide()

        self.setColor(color)

        self.defaultColorWidget_.clicked.connect(lambda: self.onColorChanged(self.defaultColorWidget_.color()))
        self.themeColorPanel_.colorChanged.connect(self.onColorChanged)
        self.standardColorPanel_.colorChanged.connect(self.onColorChanged)
        self.recentColorPanel_.colorChanged.connect(self.onColorChanged)
        self.moreColorWidget_.clicked.connect(self.onMoreColorClicked)

    def isAlphaChannelEnabled(self) -> bool:
        return self.enableAlpha_

    def setRecentColors(self, colors: list[QColor]):
        self.recentColorPanel_.setColors(colors)
        self.recentColorPanel_.setVisible(bool(colors))
        self.separator_.setVisible(bool(colors))

    def color(self) -> QColor:
        return self.color_
    
    def setColor(self, color: QColor):
        self.color_ = color
        self.themeColorPanel_.setColor(color)
        self.standardColorPanel_.setColor(color)
        self.recentColorPanel_.setColor(color)

    def setDefaultColor(self, color: QColor):
        self.defaultColorWidget_.setColor(color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if isDarkTheme():
            painter.setBrush(QColor(40, 40, 40))
            painter.setPen(QColor(255, 255, 255, 26))
        else:
            painter.setBrush(QColor(248, 248, 248))
            painter.setPen(QColor(0, 0, 0, 15))

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)

    def onMoreColorClicked(self):
        parent_widget = self.parent()
        if parent_widget and isinstance(parent_widget, Flyout):
            parent_widget.hide()
            parent_window = self.window().parentWidget().window()
        else:
            parent_window = self.window()


        from .ColorPicker import ColorPickerView
        from .FlyoutDialog import FlyoutDialog
        
        # view = ColorPickerView(self.color(), self.isAlphaChannelEnabled(), self)
        # flyout = FlyoutDialog.make(view, parent_widget.parent(), parent_window, FlyoutAnimationType.DROP_DOWN)
        # flyout.accepted.connect(lambda: self.onColorChanged(view.color()))
        
        # view = ColorPickerView(self.color(), self.isAlphaChannelEnabled(), self)
        # view.colorChanged.connect(self.onColorChanged)
        # color_dialog = FlyoutDialog(view, parent=parent_window, isDeleteOnClose=True)
        # color_dialog.exec()
        
        color_dialog = ColorDialog(self.color_, "More Colors", parent_window, self.enableAlpha_)
        color_dialog.colorChanged.connect(self.onColorChanged)
        color_dialog.exec()

    def onColorChanged(self, color: QColor):
        self.setColor(color)
        self.colorChanged.emit(color)

class DropDownColorPalette(ToolButton):
    colorChanged = Signal(QColor)

    def __init__(self, parent=None, enableAlpha=True):
        super().__init__(parent)
        self.color_ = QColor()
        self.defaultColor_ = QColor()
        self.enableAlpha_ = enableAlpha
        self.recentColors_ = []
        self.aniType_ = FlyoutAnimationType.DROP_DOWN
        
        self.setFixedSize(55, 32)
        self.clicked.connect(self.showPalette)

    def color(self) -> QColor:
        return self.color_
        
    def setColor(self, color):
        if color == self.color_:
            return
        
        self.color_ = color
        self.update()
        self.colorChanged.emit(color)

    def isAlphaChannelEnabled(self) -> bool:
        return self.enableAlpha_

    def defaultColor(self) -> QColor:
        return self.defaultColor_
    
    def setDefaultColor(self, color: QColor):
        self.defaultColor_ = color

    def flyoutAnimationType(self) -> FlyoutAnimationType:
        return self.aniType_
    
    def setFlyoutAnimationType(self, aniType: FlyoutAnimationType):
        self.aniType_ = aniType

    def paintEvent(self, event:QPainter):
        super().paintEvent(event)
        self.__paint()
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.color())
        painter.setPen(Qt.PenStyle.NoPen)
        self.drawColor(painter)
        painter.end()

    def drawColor(self, painter:QPainter):
        painter.drawRoundedRect(5, 5, 22, 22, 4, 4)

    def showPalette(self):
        palette = ColorPaletteView(self.color(), self.isAlphaChannelEnabled())
        palette.setRecentColors(self.recentColors_)
        palette.setDefaultColor(self.defaultColor())
        palette.colorChanged.connect(self.setColor)

        flyout = Flyout.make(palette, self, self.window(), self.aniType_)
        palette.colorChanged.connect(flyout.close)
        
    def onColorSelected(self, color: QColor):
        if color not in self.recentColors_:
            self.recentColors_.append(color)

        self.setColor(color)

    def __paint(self):
        painter = QPainter(self)

        if self.isDown():
            painter.setOpacity(0.7)
        elif self.underMouse():
            painter.setOpacity(0.8)

        rect = QRectF(self.width() - 22, self.height() / 2.0 - 5, 10, 10)
        self.__drawDropDownIcon(painter, rect.translated(2, 0))

        painter.end()
        
    def __drawDropDownIcon(self, painter:QPainter, rect:QRectF):
        if isDarkTheme():
            FluentIcon(FluentIcon.ARROW_DOWN).render(painter, rect)
        else:
            FluentIcon(FluentIcon.ARROW_DOWN).render(
            painter, rect, Theme.AUTO, None, fill="#646464"
        )
            
class CustomDropDownColorPalette(DropDownColorPalette):
    def __init__(self, parent=None, enableAlpha=True):
        super().__init__(parent, enableAlpha)
        self.setIcon(FluentIcon(FluentIcon.PALETTE))
        
    def drawColor(self, painter: QPainter):
        painter.drawRect(6, 22, 24, 4)
        
    def drawIcon(self, painter: QPainter, rect: QRectF, state: QIcon.State):
        painter.setOpacity(painter.opacity() * 0.65)
        drawIcon(self.icon(), painter, rect, state)
    
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    
    window = QWidget()
    window.setWindowTitle("DropDown Color Palette Example")
    window.setStyleSheet("background-color: #2d2d2d;")
    
    widget = DropDownColorPalette()
    widget.setColor(QColor(255, 0, 0))
    
    layout = QVBoxLayout(window)
    layout.addWidget(widget)
    
    window.show()
    sys.exit(app.exec())