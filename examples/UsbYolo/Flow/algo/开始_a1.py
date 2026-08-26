# -*- coding: utf-8 -*-
# 模型预加载：进程一开始就在后台线程预加载推理后端（GPU worker / 本进程模型，~3s），
# 与等帧并行；避免把模型加载压到首帧上，也不阻塞流程进入等帧。
import threading

from algo.ThreadGlobalData import *
from services.yolo_engine import YoloEngine


def _preload():
    try:
        YoloEngine.preload(thData.model_path, thData.device, thData.gpu_python)
    except Exception as e:
        print("[%s] %s 模型预加载失败: %s（等帧处理时重试）"
              % (thData.cam_str, thData.algo_key, e), flush=True)


threading.Thread(target=_preload, daemon=True).start()
raise Exception("return", 0)
