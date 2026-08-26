from qfluentwidgets import TransparentToolButton, isDarkTheme
from qfluentwidgets import FlyoutViewBase, Flyout, FlyoutAnimationType, FlyoutAnimationManager
from qfluentwidgets import FluentIcon
from qfluentwidgets.components.date_time.picker_base import SeparatorWidget
from qfluentwidgets.common.overload import singledispatchmethod
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import Signal, Qt, QSize, QPoint
from PySide6.QtGui import QColor
from PySide6.QtCore import QPropertyAnimation

class FlyoutDialogView(FlyoutViewBase):
    accepted = Signal()
    rejected = Signal()

    def __init__(self, view: QWidget, parent: QWidget = None):
        super().__init__(parent)
        self.view_ = view
        self.hSeparatorWidget_ = SeparatorWidget(Qt.Orientation.Horizontal, self)

        self.yesButton_ = TransparentToolButton(FluentIcon(FluentIcon.ACCEPT), self)
        self.cancelButton_ = TransparentToolButton(FluentIcon(FluentIcon.CLOSE), self)
        self.vBoxLayout_ = QVBoxLayout(self)
        self.buttonLayout_ = QHBoxLayout()

        self.yesButton_.setIconSize(QSize(16, 16))
        self.cancelButton_.setIconSize(QSize(13, 13))
        self.yesButton_.setFixedHeight(33)
        self.cancelButton_.setFixedHeight(33)

        self.vBoxLayout_.setSpacing(0)
        self.vBoxLayout_.setContentsMargins(1, 0, 1, 0)

        self.buttonLayout_.setSpacing(6)
        self.buttonLayout_.setContentsMargins(3, 3, 3, 4)
        self.buttonLayout_.addWidget(self.yesButton_)
        self.buttonLayout_.addWidget(self.cancelButton_)
        self.yesButton_.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.cancelButton_.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.vBoxLayout_.addWidget(self.view_)
        self.vBoxLayout_.addWidget(self.hSeparatorWidget_)
        self.vBoxLayout_.addLayout(self.buttonLayout_, 1)

        self.yesButton_.clicked.connect(self.accepted)
        self.cancelButton_.clicked.connect(self.rejected)

    def borderColor(self) -> QColor:
        return QColor(255, 255, 255, 26) if isDarkTheme() else QColor(0, 0, 0, 15)

    def backgroundColor(self) -> QColor:
        return QColor(40, 40, 40) if isDarkTheme() else QColor(248, 248, 248)
    
class FlyoutDialog(Flyout):
    accepted = Signal()
    rejected = Signal()
    
    def __init__(self, view: QWidget, isDeleteOnClose: bool = True, parent: QWidget = None):
        super().__init__(FlyoutDialogView(view), parent, isDeleteOnClose)
        self.dialogView_:FlyoutDialogView = self.view

        self.dialogView_.accepted.connect(self.onAccepted)
        self.dialogView_.rejected.connect(self.onRejected)

    def fadeOut(self):
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.finished.connect(self.close)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setDuration(120)
        animation.start()

    def onAccepted(self):
        self.fadeOut()
        self.accepted.emit()

    def onRejected(self):
        self.fadeOut()
        self.rejected.emit()

    @singledispatchmethod
    @staticmethod
    def make(view: QWidget, target: QWidget = None, parent: QWidget = None, aniType = FlyoutAnimationType.PULL_UP, isDeleteOnClose: bool = True) -> 'FlyoutDialog':
        w = FlyoutDialog(view, isDeleteOnClose, parent)
        if not target:
            return w
        w.show()
        
        pos = FlyoutAnimationManager.make(aniType, w).position(target)
        w.exec(pos, aniType)
        
        return w

    @make.register(QPoint)
    @staticmethod
    def _(view: QWidget, pos: QPoint = QPoint(), parent: QWidget = None, isDeleteOnClose: bool = True) -> 'FlyoutDialog':
        w = FlyoutDialog(view, isDeleteOnClose, parent)
        
        if not pos or pos.isNull():
            return w

        w.show()
        w.exec(pos)
        
        return w