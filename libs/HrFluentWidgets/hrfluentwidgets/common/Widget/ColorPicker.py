from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QBrush
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QPushButton

from qfluentwidgets.components.date_time.picker_base import SeparatorWidget
from qfluentwidgets import (
    BodyLabel, ComboBox, SpinBox, FlyoutViewBase, 
    MaskDialogBase, SingleDirectionScrollArea, TransparentToolButton, FluentIcon, PrimaryPushButton,
    ToolButton, PrimaryToolButton, FluentStyleSheet)
from qfluentwidgets import setCustomStyleSheet, isDarkTheme
from qfluentwidgets.components.dialog_box.color_dialog import HuePanel, HexColorLineEdit
from .Slider import ColorSlider
from .ColorPalette import DropDownColorPalette, CustomDropDownColorPalette
from .FlyoutDialog import FlyoutDialog
from .._rc import resource

class ProHuePanel(HuePanel):
    def __init__(self, color, parent=None):
        super().__init__(color, parent)
        self.huePixmap = QPixmap(":/resource/images/color_picker/HuePanel.png")
        self.setFixedSize(288, 288)

class ProBrightnessSlider(ColorSlider):
    def __init__(self, color:QColor=None, parent=None):
        super().__init__(color=color, parent=parent)
    
    def setColor(self, color:QColor):
        super().setColor(QColor(color))
        self.setValue(color.value())

    def onValueChanged(self, value):
        self._color.setHsv(self._color.hue(), self._color.saturation(), value, self._color.alpha())
        self.setColor(self._color)
        self.colorChanged.emit(self._color)

    def _drawGroove(self, painter:QPainter):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor.fromHsv(self._color.hue(), self._color.saturation(), 0))
        gradient.setColorAt(1, QColor.fromHsv(self._color.hue(), self._color.saturation(), 255))
        painter.fillRect(self.rect(), gradient)

class OpacityChannelSlider(ColorSlider):
    def setColor(self, color:QColor):
        super().setColor(QColor(color))
        self.setValue(color.alpha())

    def onValueChanged(self, value):
        self._color.setAlpha(value)
        self.setColor(self._color)
        self.colorChanged.emit(self._color)

    def _drawGroove(self, painter:QPainter):
        painter.setBrush(QBrush(self.createTitledBackground()))
        painter.drawRoundedRect(self.rect(), 4, 4)
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        c = self._color
        gradient.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 0))
        gradient.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 255))
        painter.fillRect(self.rect(), gradient)

class RedChannelSlider(ColorSlider):
    def setColor(self, color:QColor):
        super().setColor(QColor(color))
        self.setValue(color.red())

    def onValueChanged(self, value):
        self._color.setRed(value)
        self.setColor(self._color)
        self.colorChanged.emit(self._color)

    def _drawGroove(self, painter:QPainter):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        c = self._color
        gradient.setColorAt(0, QColor(0, c.green(), c.blue()))
        gradient.setColorAt(1, QColor(255, c.green(), c.blue()))
        painter.fillRect(self.rect(), gradient)

class GreenChannelSlider(ColorSlider):
    def setColor(self, color:QColor):
        super().setColor(QColor(color))
        self.setValue(color.green())

    def onValueChanged(self, value):
        self._color.setGreen(value)
        self.setColor(self._color)
        self.colorChanged.emit(self._color)

    def _drawGroove(self, painter:QPainter):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        c = self._color
        gradient.setColorAt(0, QColor(c.red(), 0, c.blue()))
        gradient.setColorAt(1, QColor(c.red(), 255, c.blue()))
        painter.fillRect(self.rect(), gradient)

class BlueChannelSlider(ColorSlider):
    def setColor(self, color:QColor):
        super().setColor(QColor(color))
        self.setValue(color.blue())

    def onValueChanged(self, value):
        self._color.setBlue(value)
        self.setColor(self._color)
        self.colorChanged.emit(self._color)

    def _drawGroove(self, painter:QPainter):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        c = self._color
        gradient.setColorAt(0, QColor(c.red(), c.green(), 0))
        gradient.setColorAt(1, QColor(c.red(), c.green(), 255))
        painter.fillRect(self.rect(), gradient)
        
class ColorSpinBox(SpinBox):
    def __init__(self, value: int, parent: QWidget = None):
        super().__init__(parent)
        self.setSymbolVisible(False)

        self.setRange(0, 255)
        self.setFixedWidth(64)
        self.setValue(value)

        qss = "SpinBox{padding-right: 0px}"
        setCustomStyleSheet(self, qss, qss)
        
class ColorPickerView(FlyoutViewBase):
    colorChanged = Signal(QColor)

    def __init__(self, color: QColor, enableAlpha: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.enableAlpha_ = enableAlpha

        if not enableAlpha:
            color.setAlpha(255)

        self.color_ = color

        self.vBoxLayout_ = QVBoxLayout(self)
        self.huePanel_ = ProHuePanel(color, self)

        self.comboBox_ = ComboBox(self)
        self.hexLineEdit_ = HexColorLineEdit(color, self, enableAlpha)
        
        fontWidth = self.hexLineEdit_.fontMetrics().horizontalAdvance("#")
        fontHeight = self.hexLineEdit_.fontMetrics().height()
        
        self.hexLineEdit_.prefixLabel.deleteLater()
        self.hexLineEdit_.prefixLabel = BodyLabel('#', self.hexLineEdit_)
        self.hexLineEdit_.prefixLabel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hexLineEdit_.prefixLabel.setObjectName('prefixLabel')
        self.hexLineEdit_.prefixLabel.setFixedSize(fontWidth, fontHeight)
        self.hexLineEdit_.prefixLabel.move(7, self.hexLineEdit_.height() / 2 - fontHeight / 2)
        
        self.redLabel_ = BodyLabel("R ", self)
        self.blueLabel_ = BodyLabel("B ", self)
        self.greenLabel_ = BodyLabel("G ", self)
        self.opacityLabel_ = BodyLabel("A ", self)

        self.redSlider_ = RedChannelSlider(color, self)
        self.blueSlider_ = BlueChannelSlider(color, self)
        self.greenSlider_ = GreenChannelSlider(color, self)
        self.brightSlider_ = ProBrightnessSlider(color, self)
        self.opacitySlider_ = OpacityChannelSlider(color, self)

        self.redSpinBox_ = ColorSpinBox(color.red(), self)
        self.blueSpinBox_ = ColorSpinBox(color.blue(), self)
        self.greenSpinBox_ = ColorSpinBox(color.green(), self)
        self.opacitySpinBox_ = ColorSpinBox(color.alpha(), self)

        self.initWidgets()
        self.connectSignalToSlot()

    def initWidgets(self):
        self.setFixedWidth(318)
        self.brightSlider_.setFixedWidth(288)

        self.comboBox_.addItem("RGB")
        self.comboBox_.setFixedWidth(92)

        self.vBoxLayout_.setContentsMargins(15, 15, 15, 15)
        self.vBoxLayout_.setSpacing(0)

        self.vBoxLayout_.addWidget(self.huePanel_)
        self.vBoxLayout_.addSpacing(14)
        self.vBoxLayout_.addWidget(self.brightSlider_, 1)
        self.vBoxLayout_.addSpacing(14)

        layout = QHBoxLayout()
        layout.addWidget(self.comboBox_, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.hexLineEdit_, 0, Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout_.addLayout(layout)
        self.vBoxLayout_.addSpacing(12)

        self.addWidgetsToLayout(self.redLabel_, self.redSpinBox_, self.redSlider_)
        self.addWidgetsToLayout(self.greenLabel_, self.greenSpinBox_, self.greenSlider_)
        self.addWidgetsToLayout(self.blueLabel_, self.blueSpinBox_, self.blueSlider_)
        self.addWidgetsToLayout(self.opacityLabel_, self.opacitySpinBox_, self.opacitySlider_, 0)

        if not self.enableAlpha_:
            self.opacityLabel_.hide()
            self.opacitySpinBox_.hide()
            self.opacitySlider_.hide()

        self.huePanel_.setFocus()

        for slider in self.findChildren(ColorSlider):
            slider.setColor(self.color_)

    def connectSignalToSlot(self):
        self.huePanel_.colorChanged.connect(self.onHueChanged)
        self.redSpinBox_.valueChanged.connect(self.onRedChanged)
        self.blueSpinBox_.valueChanged.connect(self.onBlueChanged)
        self.greenSpinBox_.valueChanged.connect(self.onGreenChanged)
        self.hexLineEdit_.valueChanged.connect(self.onHexColorChanged)
        self.opacitySpinBox_.valueChanged.connect(self.onOpacityChanged)
        self.brightSlider_.colorChanged.connect(self.onBrightnessChanged)

        self.redSlider_.colorChanged.connect(lambda c: self.setColor(c))
        self.greenSlider_.colorChanged.connect(lambda c: self.setColor(c))
        self.blueSlider_.colorChanged.connect(lambda c: self.setColor(c))
        self.opacitySlider_.colorChanged.connect(lambda c: self.setColor(c))

    def addWidgetsToLayout(self, label: QWidget, spinBox: QWidget, slider: QWidget, spacing: int = 8):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(spinBox, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(slider, 1)
        slider.setFixedWidth(200)
        self.vBoxLayout_.addLayout(layout)
        self.vBoxLayout_.addSpacing(spacing)

    def setColor(self, color: QColor, movePicker: bool = True):
        if self.color_ == color:
            return 
        
        self.color_ = QColor(color)
        self.brightSlider_.setColor(color)
        self.hexLineEdit_.setColor(color)

        self.redSpinBox_.setValue(color.red())
        self.blueSpinBox_.setValue(color.blue())
        self.greenSpinBox_.setValue(color.green())
        self.opacitySpinBox_.setValue(color.alpha())

        self.redSlider_.setColor(color)
        self.greenSlider_.setColor(color)
        self.blueSlider_.setColor(color)
        self.opacitySlider_.setColor(color)

        if movePicker:
            self.huePanel_.setColor(color)

        self.colorChanged.emit(self.color_)

    def color(self) -> QColor:
        return self.color_

    def onHueChanged(self, color: QColor):
        self.setColor(QColor.fromHsv(color.hue(), color.saturation(), self.color_.value(), self.color_.alpha()))

    def onBrightnessChanged(self, color: QColor):
        self.setColor(QColor.fromHsv(self.color_.hue(), self.color_.saturation(), color.value(), self.color_.alpha()), False)

    def onRedChanged(self, red: int):
        self.setColor(QColor(red, self.color_.green(), self.color_.blue(), self.color_.alpha()))

    def onBlueChanged(self, blue: int):
        self.setColor(QColor(self.color_.red(), self.color_.green(), blue, self.color_.alpha()))

    def onGreenChanged(self, green: int):
        self.setColor(QColor(self.color_.red(), green, self.color_.blue(), self.color_.alpha()))

    def onHexColorChanged(self, hexColor: str):
        self.setColor(QColor("#" + hexColor))

    def onOpacityChanged(self, opacity: int):
        self.setColor(QColor(self.color_.red(), self.color_.green(), self.color_.blue(), opacity))
        
class DropDownColorPicker(DropDownColorPalette):
    def showPalette(self):
        view = ColorPickerView(self.color(), self.isAlphaChannelEnabled(), self)

        flyout = FlyoutDialog.make(view, self, self.window(), self.flyoutAnimationType())
        flyout.accepted.connect(lambda: self.setColor(view.color()))
        
class CustomDropDownColorPicker(CustomDropDownColorPalette):
    def showPalette(self):
        view = ColorPickerView(self.color(), self.isAlphaChannelEnabled(), self)

        flyout = FlyoutDialog.make(view, self, self.window(), self.flyoutAnimationType())
        flyout.accepted.connect(lambda: self.setColor(view.color()))

class ColorPickerDialog(MaskDialogBase):
    """ Color dialog """

    colorChanged = Signal(QColor)

    def __init__(self, color, title: str, parent=None, enableAlpha=False):
        """
        Parameters
        ----------
        color: `QColor` | `GlobalColor` | str
            initial color

        title: str
            the title of dialog

        parent: QWidget
            parent widget

        enableAlpha: bool
            whether to enable the alpha channel
        """
        super().__init__(parent)
        self.enableAlpha = enableAlpha
        if not enableAlpha:
            color = QColor(color)
            color.setAlpha(255)
        
        self.setWindowTitle(title)

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 80))
        self.setMaskColor(QColor(0, 0, 0, 76))
        
        self.vBoxLayout_ = QVBoxLayout(self.widget)
        self.buttonLayout_ = QHBoxLayout()
        
        self.colorPickerView = ColorPickerView(color, enableAlpha, self.widget)
        self.hSeparatorWidget_ = SeparatorWidget(Qt.Orientation.Horizontal, self.widget)
           
        self.yesButton_ = TransparentToolButton(FluentIcon(FluentIcon.ACCEPT), self.widget)
        self.cancelButton_ = TransparentToolButton(FluentIcon(FluentIcon.CLOSE), self.widget)

        self.yesButton_.setIconSize(QSize(16, 16))
        self.cancelButton_.setIconSize(QSize(13, 13))
        self.yesButton_.setFixedHeight(33)
        self.cancelButton_.setFixedHeight(33)
        
        self.yesButton_.setIconSize(QSize(16, 16))
        self.cancelButton_.setIconSize(QSize(13, 13))
        self.yesButton_.setFixedHeight(33)
        self.cancelButton_.setFixedHeight(33)
        
        self.widget.setFixedSize(320, 580+40*self.enableAlpha)
        
        self.vBoxLayout_.setSpacing(0)
        self.vBoxLayout_.setContentsMargins(1, 0, 1, 0)

        self.buttonLayout_.setSpacing(6)
        self.buttonLayout_.setContentsMargins(3, 3, 3, 4)
        self.buttonLayout_.addWidget(self.yesButton_)
        self.buttonLayout_.addWidget(self.cancelButton_)
        self.yesButton_.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.cancelButton_.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.vBoxLayout_.addWidget(self.colorPickerView)
        self.vBoxLayout_.addWidget(self.hSeparatorWidget_)
        self.vBoxLayout_.addLayout(self.buttonLayout_, 1)
        
        # self.colorPickerView.move((420-318)/2, 25)
        # self.buttonGroup.move(0, 25)
        # self.yesButton_.move(2, 12)
        # self.cancelButton_.move(318/2+8, 12)
        
        self.yesButton_.clicked.connect(self.accept)
        self.cancelButton_.clicked.connect(self.reject)
        self.colorPickerView.colorChanged.connect(self.colorChanged)
        
        FluentStyleSheet.COLOR_DIALOG.apply(self)
        
    def color(self) -> QColor:
        """ Get the selected color """
        return self.colorPickerView.color()
    
    def setColor(self, color: QColor):
        """ Set the selected color """
        self.colorPickerView.setColor(color, movePicker=False)
        
    def borderColor(self) -> QColor:
        return QColor(255, 255, 255, 26) if isDarkTheme() else QColor(0, 0, 0, 15)

    def backgroundColor(self) -> QColor:
        return QColor(40, 40, 40) if isDarkTheme() else QColor(248, 248, 248)