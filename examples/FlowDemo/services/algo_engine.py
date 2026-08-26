# -*- coding: utf-8 -*-
"""OpenCV 模拟算法引擎：多阶段视觉检测链（高计算压力）。

阶段：灰度 → 金字塔下采样 → 模板匹配（滑动窗口）→ 形态学开运算 →
大核中值滤波 → Canny 边缘 → 连通域轮廓 → 渲染（轮廓 + 匹配框 + 标注）。
load 控制整链循环次数（每帧计算量 ≈ 旧简单链的 5-8 倍/次）。
单通道帧跳过 BGR→GRAY 转换。返回结果图（与原图肉眼可辨）。
"""
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class AlgoEngine:
    """算法引擎（多进程/多线程安全：模板首帧标定后只读，无竞争写）。"""

    _tmpl: Optional[np.ndarray] = None   # 首帧标定模板（目标初始位置 ROI）

    @staticmethod
    def process(frame: np.ndarray, load: int = 1,
                tag: str = "") -> Tuple[np.ndarray, dict]:
        """处理一帧，返回 (结果图, 检测结果 dict)。

        结果 dict（真实检测数据，供 SignalProgram 小数据消息传输）：
            blobs   连通域目标数（len(contours)）
            match   模板匹配位置 (x, y)（原分辨率，随目标移动）
            time_ms 处理耗时（毫秒）
        """
        cv2.setNumThreads(1)   # 单线程处理：避免每进程 OpenCV 线程池 × 多消费者 → 线程爆炸
        t0 = time.time()
        gray: np.ndarray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        res: Optional[np.ndarray] = None
        blob_count: int = 0
        match_pos: Optional[Tuple[int, int]] = None
        for _i in range(max(1, int(load))):
            # 1) 金字塔下采样两级（多尺度：160x120 @640x480）
            pyr: np.ndarray = gray
            for _p in range(2):
                pyr = cv2.pyrDown(pyr)
            ph: int = pyr.shape[0]
            pw: int = pyr.shape[1]
            # 2) 模板匹配：滑动窗口找目标（真实检测的主计算量）
            # 模板首帧标定（目标初始位置 ROI，跨越背景-目标边界含边缘特征），
            # 之后固定——目标移动后原位置内容变化，匹配位置跟随新位置（跟踪语义）
            if AlgoEngine._tmpl is None:
                AlgoEngine._tmpl = cv2.GaussianBlur(
                    pyr[ph // 4 - 10:ph // 4 + 10,
                        pw // 4 - 10:pw // 4 + 10], (5, 5), 0).copy()
            match = cv2.matchTemplate(pyr, AlgoEngine._tmpl, cv2.TM_CCOEFF_NORMED)
            _minv, _maxv, _minl, max_loc = cv2.minMaxLoc(match)
            match_pos = (max_loc[0] * 4, max_loc[1] * 4)   # 两级 pyrDown = 1/4 缩放，回原分辨率 ×4
            # 3) 形态学开运算（去噪点）
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morph = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            # 4) 大核中值滤波
            blur = cv2.medianBlur(morph, 9)
            # 5) Canny 边缘 + 连通域轮廓（目标数 = 检测结果）
            edges = cv2.Canny(blur, 50, 150)
            contours, _h = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
            blob_count = len(contours)
            # 6) 渲染：轮廓 + 匹配框
            res = frame.copy()
            cv2.drawContours(res, contours, -1, (0, 255, 0), 3)
            cx, cy = match_pos
            cv2.rectangle(res, (cx, cy), (cx + 40, cy + 40), (0, 255, 255), 2)
        # 结果图标注：算法实例名（fan-out 8 窗格可辨；原图无此文字）
        if tag:
            cv2.putText(res, tag, (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                        1.2, (0, 255, 0), 3)
        info = {
            "blobs": blob_count,
            "match": match_pos,
            "time_ms": round((time.time() - t0) * 1000, 1),
        }
        return res, info
