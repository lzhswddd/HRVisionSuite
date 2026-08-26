# -*- coding: utf-8 -*-
"""收图：经 VM 取图（vm 模式走 VM 方案采图；sim 模式读本地视频）→ 推送 out 通道。

channel_out 是框架注入的聚合写通道（put=队列，write=映射，throttle 内部降频）。
"""
from camera.ThreadGlobalData import *
from services.vm_bridge import VmBridge
from HRVision.HRFlowController import _ChannelOut

# VM 桥接缓存到 thData（进程存活期持有，只初始化一次）
if thData.vm is None:
    thData.vm = VmBridge(thData.vm_mode, thData.sim_source, thData.sim_fps,
                         thData.vm_solution, thData.vm_procedure)
    print("[%s] VM 初始化: mode=%s" % (thData.cam_str, thData.vm_mode), flush=True)

frame = thData.vm.grab()  # type: ignore[union-attr]
if frame is None:
    raise Exception("return", 0)   # 取图失败，回收图重试

thData.loop_count = getattr(thData, "loop_count", 0) + 1
thData.channel_out.put(frame)                                    # 队列通道：算法取
thData.channel_out.write(frame, throttle=thData.display_divisor) # 映射通道：UI 显示
print("[%s] VM 收图 loop=%d" % (thData.cam_str, thData.loop_count), flush=True)
raise Exception("return", 0)
