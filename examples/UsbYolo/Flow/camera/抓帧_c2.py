# -*- coding: utf-8 -*-
"""抓帧：USB 相机取帧 → 推送到 out 通道（队列每帧 / 映射降频）。

channel_out 是框架注入的聚合写通道（put=队列，write=映射，throttle 内部降频）。
"""
from camera.ThreadGlobalData import *
from services.camera_driver import UsbCamera
from HRVision.HRFlowController import _ChannelOut

# 相机驱动缓存到 thData（进程存活期持有，只初始化一次）
if thData.camera is None:
    thData.camera = UsbCamera(thData.source, thData.width, thData.height)  # type: ignore[arg-type]
    print("[%s] USB 相机初始化: %s" % (thData.cam_str, thData.source), flush=True)

frame = thData.camera.grab()  # type: ignore[union-attr]
if frame is None:
    raise Exception("return", 0)   # 取帧失败，回抓帧重试

thData.loop_count = getattr(thData, "loop_count", 0) + 1
thData.channel_out.put(frame)                                    # 队列通道：每帧发送
thData.channel_out.write(frame, throttle=thData.display_divisor) # 映射通道：降频写
print("[%s] camera 抓帧 loop=%d" % (thData.cam_str, thData.loop_count), flush=True)
raise Exception("return", 0)
