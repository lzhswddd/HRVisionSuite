# -*- coding: utf-8 -*-
"""等帧处理：取输入 → 判定 OK/NG → 推输出 → 结果发 PLC → 结果信号。

channel_in/channel_out 是框架注入的聚合通道（节点不关心通道类型/数量）。
"""
from algo.ThreadGlobalData import *
from services.algo_engine import AlgoEngine
from services.plc import Plc
from HRVision.HRFlowController import _ChannelIn, _ChannelOut

# 取输入（队列通道，阻塞等待，超时返回 None 回等帧继续）
frame = thData.channel_in.get(timeout=3)
if frame is None:
    raise Exception("return", 0)

# 算：模板匹配判定 OK/NG（judge_threshold 由 pipeline.json 注入）
res, result = AlgoEngine.process(frame, thData.algo_load, thData.judge_threshold)

# 发送 OK/NG 给 PLC（PLCInterface 库写 ok/ng 地址；mock 模式写进内置从站，外部工具可读）
plc_msg: str = "PLC 未连接"
if thData.plc is None:
    thData.plc = Plc(thData.plc_type, thData.plc_host, thData.plc_port,
                     ok_addr=thData.ok_addr, ng_addr=thData.ng_addr,
                     addr_type=thData.addr_type)
if thData.plc.write_result(result["ok"]):
    addr = thData.ok_addr if result["ok"] else thData.ng_addr
    plc_msg = "OK→%s" % addr if result["ok"] else "NG→%s" % addr
result["plc_write"] = plc_msg

# 推输出（映射通道：throttle 降频写）
thData.signal_count = getattr(thData, "signal_count", 0) + 1
thData.channel_out.write(res, throttle=thData.signal_divisor)

# 判定结果走 SignalProgram relay（小数据消息：子进程 emit → 主进程真实 emit）
if thData.signal_count % max(1, thData.signal_divisor) == 0:
    signal_instance.triggerResult.emit(thData.algo_key, result)
print("[%s] 判定 %s score=%s %s" % (
    thData.algo_key, "OK" if result["ok"] else "NG", result["score"], plc_msg),
    flush=True)

raise Exception("return", 0)   # 回等帧继续
