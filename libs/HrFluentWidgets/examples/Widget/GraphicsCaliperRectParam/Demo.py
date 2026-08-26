import sys
import os

sys.path.insert(0, os.getcwd())
os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication,QMainWindow
from qfluentwidgets import (
    RangeConfigItem,RangeValidator
)
from hrfluentwidgets import (
    param_cfg, GraphicsCaliperRectParam
)
    
if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    
    param_cfg.addParam(RangeConfigItem("caliper", "caliperRect-width", 0.0, RangeValidator(0, 40)))
    param_cfg.addParam(RangeConfigItem("caliper", "caliperRect-height", 0.0, RangeValidator(0, 40)))
    param_cfg.addParam(RangeConfigItem("caliper", "caliperRect-interval", 0.0, RangeValidator(0, 40)))

    paramWidget = GraphicsCaliperRectParam("卡尺参数",param_cfg,"caliper")
    paramWidget.setConfigItem("caliper")
    paramWidget.updateParam()
    
    paramWidget.show()
    
    sys.exit(app.exec())