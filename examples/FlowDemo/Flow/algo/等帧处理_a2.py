# -*- coding: utf-8 -*-
"""等帧处理：取输入 → 算法 → 推输出 → 结果信号。

channel_in/channel_out 是框架注入的聚合通道（节点不关心通道类型/数量）。
"""
from algo.ThreadGlobalData import *
from services.algo_engine import AlgoEngine
from HRVision.HRFlowController import _ChannelIn, _ChannelOut

# 取输入（队列通道，阻塞等待，超时返回 None 回等帧继续）
frame = thData.channel_in.get(timeout=3)
if frame is None:
    raise Exception("return", 0)

# 算：多阶段检测链（algo_load 控制负载），返回结果图 + 检测结果数据
res, result = AlgoEngine.process(frame, thData.algo_load, thData.algo_key)

# 推输出（映射通道：throttle 降频写）
thData.signal_count = getattr(thData, "signal_count", 0) + 1
thData.channel_out.write(res, throttle=thData.signal_divisor)

# 检测结果走 SignalProgram relay（小数据消息：子进程 emit → 主进程真实 emit）
if thData.signal_count % max(1, thData.signal_divisor) == 0:
    signal_instance.algoResult.emit(thData.algo_key, result)
print("[%s] %s 处理完成" % (thData.cam_str, thData.algo_key), flush=True)

raise Exception("return", 0)   # 回等帧继续（测试项目持续运行）
