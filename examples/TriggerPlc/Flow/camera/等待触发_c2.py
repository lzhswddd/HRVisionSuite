# -*- coding: utf-8 -*-
"""等待触发：轮询 PLC 触发地址（mock 模式起内置从站）；auto_trigger_ms>0 时定时自动触发。

触发条件满足 → 进「拍照」节点。触发消费后清零地址（下次上升沿再触发）。
"""
import time

from camera.ThreadGlobalData import *
from services.plc import Plc, MockPlcServer

# 初始化 PLC：mock 模式起内置 Modbus 从站（外部工具可连 127.0.0.1:8000 读写地址）
if thData.plc is None:
    plc = Plc(thData.plc_type, thData.plc_host, thData.plc_port,
              thData.trigger_addr, thData.ok_addr, thData.ng_addr,
              thData.addr_type)
    if thData.plc_mode == "mock":
        thData.plc_server = MockPlcServer(port=thData.plc_port)
        thData.plc_server.start()
        time.sleep(0.5)   # 等服务就绪
    thData.plc = plc
    thData.trigger_t0 = time.time()
    print("[%s] PLC 初始化: mode=%s type=%s %s:%d trigger=%s ok=%s ng=%s" % (
        thData.cam_str, thData.plc_mode, thData.plc_type, thData.plc_host,
        thData.plc_port, thData.trigger_addr, thData.ok_addr, thData.ng_addr),
        flush=True)

# 轮询触发：PLC 地址上升沿 或 定时自动触发（演示无外部触发源也能跑通）
triggered = False
while True:
    if thData.plc.read_trigger():
        thData.plc.reset_trigger()          # 消费触发（清零，下次上升沿再触发）
        triggered = True
        break
    if (thData.auto_trigger_ms > 0
            and (time.time() - thData.trigger_t0) * 1000 >= thData.auto_trigger_ms):
        thData.trigger_t0 = time.time()
        triggered = True
        break
    time.sleep(0.02)                        # 20ms 轮询

thData.trigger_count += 1
signal_instance.triggerFired.emit(thData.cam_str, {"count": thData.trigger_count})
print("[%s] 触发拍照 #%d" % (thData.cam_str, thData.trigger_count), flush=True)
raise Exception("return", 0)   # 进拍照节点
