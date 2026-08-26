# -*- coding: utf-8 -*-
"""创建主窗口：QApplication 懒创建（仅主进程）+ 判定窗格 + 状态栏 + 退出钩子。"""
from main.ThreadGlobalData import *
from services.ui import MainWindow, ensure_qapp

app = ensure_qapp()
win = MainWindow(gData, signal_instance)
win.show()
# 窗口关闭/退出 → 优雅停管线（relay 停止 + 子进程终止 + 共享内存清理）
app.aboutToQuit.connect(gData.user.pipeline.stop)
print("UI 已创建：触发拍照 → 判定 → OK/NG → PLC（%s 模式）" % gData.user.run_mode, flush=True)
raise Exception("return", 0)
