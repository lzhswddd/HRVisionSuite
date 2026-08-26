# -*- coding: utf-8 -*-
"""GPU YOLO 推理 worker：由算法进程用 GPU 环境（如 D:/AIProgram/python.exe，CUDA）拉起。

设计：
    - 只做推理，不做画框/通道/信号（那些留在算法进程，框架链路零改动）
    - 启动时加载模型到 GPU（首次 ~5s），打印 "READY <port>" 后进入服务循环
    - 连接断开即退出（父进程死亡时 OS 关闭 socket，worker 自动收尾）

协议（TCP 127.0.0.1，每消息 4 字节小端长度前缀 + 载荷）：
    收1: 帧头 JSON {"w","h","ch","conf","imgsz"}
    收2: 原始 BGR 帧字节（w*h*ch）
    发:  检测结果 JSON {"detections":[{"cls","conf","box":[x1,y1,x2,y2]}],
                       "count","time_ms"}

注意：本文件由 Python 3.9（GPU 环境）运行——不要使用 3.10+ 语法（X | None 等）。
"""
import json
import socket
import sys

import cv2
import numpy as np

from HRVision.ExternalWorker import recv_msg, send_msg   # 帧协议辅助（工具模块）


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else "D:/AiProgram/yolov8n.pt"

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(1)   # accept 轮询，可响应父进程 terminate
    print("READY %d" % srv.getsockname()[1], flush=True)

    # 延迟导入 + 首帧预热：READY 前完成模型加载，首请求即可达稳态速度
    from ultralytics import YOLO
    model = YOLO(model_path, task="detect")
    model.predict(np.zeros((480, 640, 3), dtype=np.uint8), verbose=False)  # CUDA 预热

    conn, _ = srv.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    conn.settimeout(30)
    try:
        while True:
            header = json.loads(recv_msg(conn).decode("utf-8"))
            raw = recv_msg(conn)
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                header["h"], header["w"], header["ch"])
            t0 = cv2.getTickCount()
            results = model.predict(frame, conf=header["conf"],
                                    imgsz=header["imgsz"], verbose=False)
            dets = []
            for r in results:
                names = r.names
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    score = float(box.conf[0])
                    dets.append({"cls": names[cls_id], "conf": round(score, 3),
                                 "box": [round(v, 1) for v in (x1, y1, x2, y2)]})
            time_ms = round((cv2.getTickCount() - t0)
                            / cv2.getTickFrequency() * 1000, 1)
            send_msg(conn, json.dumps(
                {"detections": dets, "count": len(dets),
                 "time_ms": time_ms}).encode("utf-8"))
    except (ConnectionError, OSError):
        pass   # 父进程退出/断开 → 正常收尾
    finally:
        conn.close()
        srv.close()


if __name__ == "__main__":
    main()
