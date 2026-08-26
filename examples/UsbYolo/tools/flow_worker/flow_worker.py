# -*- coding: utf-8 -*-
"""打包子进程入口：--hrflow-bootstrap <pkl>（ProcessIsolate 协议）。

把流程子进程（如算法流程）打包成独立 exe —— 目标机器无需 Python 环境。
打包命令见同目录 build.bat；打包产物 dist/flow_worker/flow_worker.exe
配到 pipeline.json 的 python_exe 即可：
    {"id": "yolo_1", "flow": "algo", "python_exe": ".../flow_worker.exe", ...}
"""
import sys

from HRVision.ProcessIsolate import bootstrap_main

if __name__ == "__main__":
    sys.exit(bootstrap_main())
