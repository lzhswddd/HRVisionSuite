# -*- coding: utf-8 -*-
"""判定算法：ROI 模板匹配（首帧校准）→ OK/NG。

模板取自首帧 ROI；后续帧 ROI 内容漂移（被测物位移）→ 匹配分下降 → NG。
判定阈值 0.8（可配置 judge_threshold）。algo_load 模拟算法计算负载。
"""
import cv2
import numpy as np

cv2.setNumThreads(1)   # 进程模式多消费者：限制 OpenCV 线程池爆炸


class AlgoEngine:
    """类级状态（模板校准），子进程存活期持有。"""

    _tmpl: np.ndarray | None = None   # 首帧 ROI 模板

    @classmethod
    def reset(cls) -> None:
        cls._tmpl = None

    @classmethod
    def process(cls, frame: np.ndarray, algo_load: int,
                judge_threshold: float = 0.8) -> tuple[np.ndarray, dict]:
        """判定 + 标注；返回 (结果图, 判定数据)。

        结果数据：
            {"ok", "score", "time_ms", "first"}
        """
        t0: float = cv2.getTickCount()
        h, w = frame.shape[0], frame.shape[1]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = gray[h // 4:h // 4 + h // 3, w // 4:w // 4 + w // 3]

        first: bool = cls._tmpl is None
        if first:
            cls._tmpl = roi.copy()   # 首帧校准模板
            ok: bool = True
            score: float = 1.0
        else:
            res = cv2.matchTemplate(roi, cls._tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            score = float(max_val)
            ok = score >= judge_threshold

        # 模拟计算负载（algo_load 控制循环次数）
        if algo_load > 1:
            dst = roi.copy()
            for _ in range(algo_load * 3):
                dst = cv2.GaussianBlur(dst, (3, 3), 0)

        # 标注 ROI 与判定结果
        color = (0, 255, 0) if ok else (0, 0, 255)
        cv2.rectangle(frame, (w // 4, h // 4), (w // 4 + w // 3, h // 4 + h // 3),
                      color, 2)
        cv2.putText(frame, "OK %.3f" % score if ok else "NG %.3f" % score,
                    (w // 4, h // 4 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, color, 2)

        time_ms: float = round((cv2.getTickCount() - t0)
                               / cv2.getTickFrequency() * 1000, 1)
        return frame, {"ok": ok, "score": round(score, 3),
                       "time_ms": time_ms, "first": first}
