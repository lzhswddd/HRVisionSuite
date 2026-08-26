from qfluentwidgets import FluentIconBase, Theme,getIconColor
from enum import Enum
class HrIcon(FluentIconBase,Enum):
    """ 自定义图标 """

    # 定义图标
    HRICON = "HRLogo"
    MOUSE = "Mouse"
    POLYGON = "Polygon"
    RECT = "Rectangle"

    def path(self, theme=Theme.AUTO):
        return f':/hricon/icons/{self.value}_{getIconColor(theme)}.svg'
