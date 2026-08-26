# -*- coding: utf-8 -*-
"""等帧处理：取输入 → YOLO 识别画框 → 推输出 → 结果信号。

channel_in/channel_out 是框架注入的聚合通道（节点不关心通道类型/数量）。
推理后端（本进程 PyTorch/OpenVINO 或 GPU worker 转发）由 YoloEngine 统一分发。
"""
from algo.ThreadGlobalData import *
from services.yolo_engine import YoloEngine
from HRVision.HRFlowController import _ChannelIn, _ChannelOut

# 取输入（队列通道，阻塞等待，超时返回 None 回等帧继续）
frame = thData.channel_in.get(timeout=3)
if frame is None:
    raise Exception("return", 0)

# 算：YOLO 检测 + 画框（后端由 gpu_python/device 决定），返回结果图 + 检测数据
try:
    res, result = YoloEngine.process(frame, thData.model_path, thData.conf,
                                     thData.imgsz, thData.device, thData.gpu_python)
except Exception as e:
    print("[%s] %s 推理失败: %s（回等帧重试）" % (thData.cam_str, thData.algo_key, e),
          flush=True)
    raise Exception("return", 0)

# 推输出（映射通道：throttle 降频写）
thData.signal_count = getattr(thData, "signal_count", 0) + 1
thData.channel_out.write(res, throttle=thData.signal_divisor)

# 检测结果走 SignalProgram relay（小数据消息：子进程 emit → 主进程真实 emit）
if thData.signal_count % max(1, thData.signal_divisor) == 0:
    signal_instance.yoloResult.emit(thData.algo_key, result)
print("[%s] %s 检测完成 count=%d" % (thData.cam_str, thData.algo_key, result["count"]),
      flush=True)

raise Exception("return", 0)   # 回等帧继续（测试项目持续运行）
