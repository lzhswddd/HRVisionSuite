# -*- coding: utf-8 -*-
"""主窗口：算法实例窗格网格（GraphicsView 架构，hrfluentwidgets 现成控件）。

每窗格 = hrfluentwidgets CameraView（HeaderCardWidget + GraphicsView 放大镜 +
CommandBar 放大/缩小/适应/十字/清除 + GraphicsScene.setImage），
放大查看由 GraphicsView 滚轮缩放/按钮天然支持（无需自研缩放逻辑）。

显示数据走「显示槽」共享内存（DisplaySlot 单写单读）：
    原图槽按相机共享一段（相机进程写，fan-out 多窗格读同一段）；
    结果图槽每算法一段（算法进程写，谁的数据谁写）。
主进程只做读方：定时器按显示状态（勾选）读对应槽，seq 变化才 setImage；
QApplication 懒创建（仅在主进程 UI 节点调用；子进程不付 Qt GUI 开销）。
"""
from typing import Optional

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QVBoxLayout,
                               QWidget)

from hrfluentwidgets.components.CameraView.CameraView import CameraView

from HRVision.HRFlowController import Monitor

_APP: Optional[QWidget] = None   # 模块级持有：QApplication 是 Python 所有权对象，
                                 # 局部引用会在流程结束后被 GC；模块级 = 进程存活期


def ensure_qapp() -> QApplication:
    """返回全局 QApplication（懒创建，仅主进程调用；模块级保活）。"""
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


class MainWindow(QWidget):
    """算法实例窗格网格：每窗格 CameraView（GraphicsView 架构）+ 原图/结果切换。"""

    def __init__(self, gData, signal_instance, fps_limit: int = 15):
        super().__init__()
        global _APP
        self.gData = gData
        self.user = gData.user
        self.monitor: Monitor = Monitor(gData.user)
        _APP = self   # 模块级持有主窗口（无 parent QWidget，局部引用会被 GC）
        self.setWindowTitle("FlowDemo - %d 相机 × %d 算法 (%s 模式)" % (
            len(gData.user.cameraList), len(gData.user.pane_list), gData.user.run_mode))
        self.resize(1680, 1080)

        # 窗格按算法实例（algo_keys 由管线启动时填充，如 CCD1_A0..CCD1_A7）
        keys = gData.user.pane_list
        grid = QGridLayout(self)
        for i, key in enumerate(keys):
            row, col = i // 4, i % 4   # 4 列网格（最多 8 窗格两行）
            cell = QWidget()
            v = QVBoxLayout(cell)
            v.setContentsMargins(0, 0, 0, 0)
            view = CameraView(cell)
            view.setTitle(key + " 等待图像...")
            view.scene.setImage(QImage())   # 初始空图（写方就绪后定时器更新）
            checkbox = QCheckBox("显示结果图（不勾选 = 原图）")
            checkbox.setChecked(True)
            v.addWidget(view, 1)
            v.addWidget(checkbox)
            grid.addWidget(cell, row, col)
            gData.user.windows[key] = [view, checkbox, {"seq": -1, "result": None}]

            checkbox.stateChanged.connect(self._make_toggle(key))
            # SignalProgram relay：子进程 emit 的检测结果 → 主进程真实信号 → 消费
            signal_instance.algoResult.connect(
                self._make_on_result(key), Qt.ConnectionType.DirectConnection)

        # 刷新定时器：固定帧率读显示槽（seq 变化才 setImage，>刷新率的帧跳过）
        self._timer = QTimer()
        interval = max(1, int(1000 / fps_limit)) if fps_limit and fps_limit > 0 else 16
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    # ---------- 显示槽读取（DisplaySlot 封装：reshape + 未就绪静默） ----------

    def _read_slot(self, key: str, kind: str):
        """读窗格显示槽：返回 (seq, frame3d) 或 (None, None)（写方未就绪静默跳过）。"""
        return self.user.display_slots[key][kind].read()

    def _make_toggle(self, key: str):
        def toggle(state):
            self.user.windows[key][2]["seq"] = -1   # 切换后强制下周期重新显示
        return toggle

    def _make_on_result(self, key: str):
        # 信号带节点 id（如 algo_1），窗格 key 是 pane id（如 pane_algo_1）——
        # 按 state.pane_nodes 映射过滤（pane_id -> 结果信号源节点 id）
        node_id = self.user.pane_nodes.get(key)

        def on_result(algo_key, result):
            if algo_key != node_id:
                return
            self.user.windows[key][2]["result"] = result   # 缓存最新检测结果
        return on_result

    # ---------- 刷新（固定帧率定时器） ----------

    def _refresh(self):
        for key, (view, checkbox, imgs) in self.user.windows.items():
            show_res = checkbox.isChecked()
            kind = "res" if show_res else "origin"
            seq, img = self._read_slot(key, kind)
            if img is None or seq == imgs.get("seq"):
                continue                 # 无新帧（>刷新率的帧已被写方覆盖跳过）
            imgs["seq"] = seq
            view.scene.setImage(ndarray_to_qimage(img))
            st = self.user.fps_stats.get(key, {})
            r = imgs.get("result")
            res_str = ("blob=%d @%s %sms" % (r["blobs"], r["match"], r["time_ms"])
                       if r else "结果: -")
            view.setTitle("%s | %s | FPS: %.1f | %s" % (
                key, "结果图" if show_res else "原图", st.get("fps", 0.0), res_str))
        self.monitor.tick()


def ndarray_to_qimage(arr: np.ndarray) -> QImage:
    """numpy BGR → QImage（GraphicsScene.setImage 内部 fromImage 深拷贝，视图安全）。"""
    h: int = arr.shape[0]
    w: int = arr.shape[1]
    return QImage(arr.data, w, h, arr.strides[0], QImage.Format_RGB888).rgbSwapped()
