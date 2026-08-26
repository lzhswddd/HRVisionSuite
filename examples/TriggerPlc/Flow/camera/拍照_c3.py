# -*- coding: utf-8 -*-
"""拍照：触发后抓一帧 → 推送到 out 通道（队列每帧 / 映射降频）。

channel_out 是框架注入的聚合写通道（put=队列，write=映射，throttle 内部降频）。
"""
from camera.ThreadGlobalData import *
from services.camera_driver import CameraDriver
from HRVision.HRFlowController import _ChannelOut

# 相机驱动缓存到 thData（进程存活期持有，只初始化一次）
if thData.camera is None:
    thData.camera = CameraDriver(thData.source)  # type: ignore[arg-type]
    print("[%s] 相机初始化: %s" % (thData.cam_str, thData.source), flush=True)

frame = thData.camera.grab()  # type: ignore[union-attr]
if frame is None:
    raise Exception("return", 0)   # 取帧失败，回等待触发重试

thData.loop_count = getattr(thData, "loop_count", 0) + 1
thData.channel_out.put(frame)                                    # 队列通道：算法取
thData.channel_out.write(frame, throttle=thData.display_divisor) # 映射通道：UI 显示
print("[%s] 拍照 loop=%d" % (thData.cam_str, thData.loop_count), flush=True)
raise Exception("return", 0)
