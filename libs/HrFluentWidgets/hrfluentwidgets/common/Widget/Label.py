from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer
from qfluentwidgets import BodyLabel

class SvgLabel(BodyLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = QSvgRenderer()  # 创建一个SVG渲染器实例
        # self.renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

    def setSvg(self, svg_content):
        """
        设置SVG内容
        :param svg_content: SVG内容字符串
        """
        self.renderer.load(svg_content)
        
    def paintEvent(self, event):
        """
        重写paintEvent方法以绘制SVG内容
        :param event: 事件对象
        # """
        super().paintEvent(event)
        painter = QPainter(self)
        # 调整绘制区域以避免边框问题
        self.renderer.render(painter, self.rect().adjusted(0, 0, 1, 1))  # 绘制SVG内容到标签的矩形区域
        painter.end()