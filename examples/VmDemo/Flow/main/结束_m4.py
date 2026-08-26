# -*- coding: utf-8 -*-
"""主流程收尾：进入 Qt 事件循环。

QTimer 驱动 UI 刷新与 [FPS]/[MEM] 日志；窗口关闭 → exec_ 返回 → 流程结束，
aboutToQuit 已挂管线优雅停止（见 创建UI_m3）。
"""
from main.ThreadGlobalData import *
qApp.exec_()
raise Exception("return", 0)
