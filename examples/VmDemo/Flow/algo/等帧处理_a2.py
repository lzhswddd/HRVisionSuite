# -*- coding: utf-8 -*-
"""等帧处理：取输入 → 调用算法 → 返回结果 → 发送 vm 的通信结果 → 结果信号。

channel_in/channel_out 是框架注入的聚合通道（节点不关心通道类型/数量）。
"""
from algo.ThreadGlobalData import *
from services.vm_bridge import VmBridge
from HRVision.HRFlowController import _ChannelIn, _ChannelOut

# 取输入（队列通道，阻塞等待，超时返回 None 回等帧继续）
frame = thData.channel_in.get(timeout=3)
if frame is None:
    raise Exception("return", 0)

# VM 桥接缓存（进程存活期只初始化一次）
if thData.vm is None:
    thData.vm = VmBridge(thData.vm_mode, sim_source=thData.sim_source,
                         vm_solution=thData.vm_solution,
                         vm_procedure=thData.vm_procedure,
                         vm_resource_module=thData.vm_resource_module,
                         vm_device_id=thData.vm_device_id)

# 调用算法（vm 模式：推图进 VM 方案处理；sim 模式：本地轻量检测链）
res, result = thData.vm.process(frame)  # type: ignore[union-attr]

# 返回结果 + 发送 vm 的通信结果（vm 模式走 VisionMasterCore 通信设备）
result["vm_comm"] = thData.vm.send_result(result)  # type: ignore[union-attr]

# 推输出（映射通道：throttle 降频写）
thData.signal_count = getattr(thData, "signal_count", 0) + 1
thData.channel_out.write(res, throttle=thData.signal_divisor)

# 结果走 SignalProgram relay（小数据消息：子进程 emit → 主进程真实 emit）
if thData.signal_count % max(1, thData.signal_divisor) == 0:
    signal_instance.vmResult.emit(thData.algo_key, result)
print("[%s] VM 结果 %s | %s" % (
    thData.algo_key, "OK" if result["ok"] else "NG", result["vm_comm"]), flush=True)

raise Exception("return", 0)   # 回等帧继续
