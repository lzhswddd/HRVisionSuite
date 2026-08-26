# HRVisionSuite —— HRVision 全家桶（一键部署）

汇总所有库与例程，一个命令完成 Python 环境部署。

## 包含内容

| 库 | 包名 | 说明 |
|---|---|---|
| 框架 | `HRVision` | HRFlowController（流程引擎 pyd）+ ProcessIsolate（进程隔离环境）+ ExternalWorker（外部工具进程通信）+ VisionMaster/HRCamera + bin |
| UI 组件 | `HrFluentWidgets` | 相机视图/参数树等工业 UI（依赖 PySide6-Fluent-Widgets） |
| 运动控制 | `HrMotionController` | 运动控制库 |
| PLC 通信 | `PLCInterface` | PLCDevice.dll + HslCommunication.dll 封装（Modbus/Profinet 等） |

| 例程 | 说明 |
|---|---|
| `FlowDemo` | 通用管线演示（任意流程拓扑 + 声明式通道，1080p） |
| `UsbYolo` | USB 相机 + YOLO 识别（进程隔离环境跑 AI 环境 GPU） |
| `TriggerPlc` | 触发拍照 + 判定 + OK/NG 发 PLC（PLCInterface） |
| `VmDemo` | VM（VisionMaster）采图/算法/通信结果 |

## 一键部署

```bat
install_all.bat            # 用默认 python 环境
install_all.bat D:\envs\HRVision\python.exe    # 指定环境
```

脚本执行：
1. `pip install` 四个库 + meta 包（依赖自动装：pycryptodome/numpy/psutil/PySide6 等）
2. 例程拷贝到 `D:\HRVisionExamples\`
3. 验证全部库可导入

## 运行例程

```bat
cd /d D:\HRVisionExamples\UsbYolo && python HRStar.py
cd /d D:\HRVisionExamples\FlowDemo && python HRStar.py
cd /d D:\HRVisionExamples\TriggerPlc && python HRStar.py
cd /d D:\HRVisionExamples\VmDemo && python HRStar.py
```

> 例程默认配置即开即用（视频源/模拟 PLC/模拟 VM）；接真实设备时改各例程
> `Flow/pipeline.json`（source / plc_host / vm_solution 等）。

## 目录结构

```
HRVisionSuite/
├── install_all.bat        # 一键部署
├── setup.py               # meta 包
├── README.md
└── examples/              # 例程（FlowDemo / UsbYolo / TriggerPlc / VmDemo）
```

子库源码：`../PyHRVision`、`../HrFluentWidgets`、`../HrMotionController`、`../PLCInterface`。
