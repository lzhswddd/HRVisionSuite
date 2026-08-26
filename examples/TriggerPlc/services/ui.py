# -*- coding: utf-8 -*-
"""主窗口：判定窗格（CameraView）+ 触发/PLC 状态栏。

显示数据走「显示槽」共享内存（DisplaySlot 单写单读，头部带通道数还原 3D）：
    原图槽：相机进程写（触发拍照帧）；结果图槽：算法进程写（OK/NG 标注）。
主进程只做读方：定时器按显示状态（勾选）读对应槽，seq 变化才 setImage。
"""
from typing import Optional

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
                               QVBoxLayout, QWidget)

from hrfluentwidgets.components.CameraView.CameraView import CameraView

from HRVision.HRFlowController import Monitor

_APP: Optional[QWidget] = None   # 模块级持有：QApplication 局部引用会被 GC；模块级 = 进程存活期


def ensure_qapp() -> QApplication:
    """返回全局 QApplication（懒创建，仅主进程调用；模块级保活）。"""
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


class MainWindow(QWidget):
    """判定窗格：CameraView + 原图/结果切换 + 触发计数/PLC 状态标签。"""

    def __init__(self, gData, signal_instance, fps_limit: int = 15):
        super().__init__()
        global _APP
        self.gData = gData
        self.user = gData.user
        self.monitor: Monitor = Monitor(gData.user)
        self._status: QLabel = QLabel("等待触发...")
        _APP = self
        self.setWindowTitle("TriggerPlc - %s 模式（触发拍照 → 判定 → OK/NG → PLC）"
                            % gData.user.run_mode)
        self.resize(1280, 900)

        keys = gData.user.pane_list
        grid = QGridLayout(self)
        for i, key in enumerate(keys):
            row, col = i // 2, i % 2
            cell = QWidget()
            v = QVBoxLayout(cell)
            v.setContentsMargins(0, 0, 0, 0)
            view = CameraView(cell)
            view.setTitle(key + " 等待图像...")
            view.scene.setImage(QImage())
            checkbox = QCheckBox("显示结果图（不勾选 = 原图）")
            checkbox.setChecked(True)
            v.addWidget(view, 1)
            v.addWidget(checkbox)
            grid.addWidget(cell, row, col)
            gData.user.windows[key] = [view, checkbox, {"seq": -1, "result": None}]
            checkbox.stateChanged.connect(self._make_toggle(key))
            signal_instance.triggerResult.connect(
                self._make_on_result(key), Qt.ConnectionType.DirectConnection)
            signal_instance.triggerFired.connect(self._make_on_trigger(key))

        # 状态栏（触发计数 / PLC 线圈状态）
        grid.addWidget(self._status, len(keys) // 2 + 1, 0, 1, 2)

        self._timer = QTimer()
        interval = max(1, int(1000 / fps_limit)) if fps_limit and fps_limit > 0 else 16
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    # ---------- 显示槽读取 ----------

    def _read_slot(self, key: str, kind: str):
        return self.user.display_slots[key][kind].read()

    def _make_toggle(self, key: str):
        def toggle(state):
            self.user.windows[key][2]["seq"] = -1
        return toggle

    def _make_on_trigger(self, key: str):
        node_id = self.user.cameraList[0] if self.user.cameraList else "grab_0"

        def on_trigger(cam_id, info):
            if cam_id != node_id:
                return
            self._status.setText("触发拍照 #%d（PLC 模式 %s）" % (
                info.get("count", 0), self.user.pipeline_spec.get("nodes")[0].get(
                    "plc_mode", "?")))
        return on_trigger

    def _make_on_result(self, key: str):
        node_id = self.user.pane_nodes.get(key)

        def on_result(algo_key, result):
            if algo_key != node_id:
                return
            self.user.windows[key][2]["result"] = result
            st = "OK" if result.get("ok") else "NG"
            self._status.setText(
                "判定 %s（score=%.3f，%sms）| PLC: %s" % (
                    st, result.get("score", 0.0), result.get("time_ms", 0.0),
                    result.get("plc_write", "未发送")))
        return on_result

    # ---------- 刷新（固定帧率定时器） ----------

    def _refresh(self):
        for key, (view, checkbox, imgs) in self.user.windows.items():
            show_res = checkbox.isChecked()
            kind = "res" if show_res else "origin"
            seq, img = self._read_slot(key, kind)
            if img is None or seq == imgs.get("seq"):
                continue
            imgs["seq"] = seq
            view.scene.setImage(ndarray_to_qimage(img))
            st = self.user.fps_stats.get(key, {})
            r = imgs.get("result")
            res_str = ("-"
                       if not r else
                       ("OK" if r.get("ok") else "NG") + " score=" + str(r.get("score")))
            view.setTitle("%s | %s | FPS: %.1f | %s" % (
                key, "结果图" if show_res else "原图", st.get("fps", 0.0), res_str))
        self.monitor.tick()


def ndarray_to_qimage(arr: np.ndarray) -> QImage:
    """numpy BGR → QImage（GraphicsScene.setImage 内部 fromImage 深拷贝，视图安全）。"""
    h: int = arr.shape[0]
    w: int = arr.shape[1]
    return QImage(arr.data, w, h, arr.strides[0], QImage.Format_RGB888).rgbSwapped()
