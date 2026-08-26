# UsbYolo —— USB 相机0 + YOLO 识别画框返回结果

基于 HRFlowController 框架的 **USB 相机 + AI 检测** 例程：
USB 相机取帧 → YOLO 检测（画框）→ 结果图显示槽 + 检测数据信号。

## 结构

```
UsbYolo/
├── HRStar.py                  # 入口（纯框架装配）
├── services/
│   ├── camera_driver.py       # USB 相机驱动（source="usb:0"，也支持视频文件）
│   ├── yolo_engine.py         # YOLO 检测引擎（ultralytics，模型首帧加载，画框+结果数据）
│   └── ui.py                  # 检测窗格（CameraView + 原图/结果切换）
└── Flow/
    ├── ProgramGlobalData.py   # ProgramData + yoloResult 信号
    ├── pipeline.json          # 拓扑/参数（source、model_path、conf、imgsz…）
    ├── main/ camera/ algo/    # 流程节点（节点 .py 只写业务胶水）
    └── *.ndjs                 # 流程拓扑（编辑器导出，已入库）
```

## 配置（Flow/pipeline.json）

| 节点 | 参数 | 说明 |
|---|---|---|
| `grab_0` (camera) | `source` | `"usb:0"` 打开 USB 相机 0；也支持 `"videos/xx.avi"` |
| | `display_divisor` | 原图显示降频（每 N 帧写一次显示槽） |
| `yolo_1` (algo) | `model_path` | YOLO 模型（如 `D:/AiProgram/yolov8n.pt`） |
| | `conf` / `imgsz` | 置信度阈值 / 推理尺寸 |
| | `python_exe` | **进程隔离环境**：算法流程进程用指定解释器拉起（如 `D:/AIProgram/python.exe`） |
| | `device` | 推理设备：`auto`（有 CUDA 用 GPU）/ `0` / `cpu` / `openvino` |
| | `gpu_python` | （备用）GPU worker 转发环境；配了 `python_exe` 后不再需要 |


## 子进程打包成 exe

流程子进程（如算法流程）可以打包成独立 exe（PyInstaller）——目标机器**无需 Python 环境**：

```
tools/flow_worker/
├── flow_worker.py        # 入口：--hrflow-bootstrap <pkl>（调 ProcessIsolate.bootstrap_main）
├── build.bat             # 打包命令（onedir，含 Crypto/numpy/psutil/DLL 依赖收集）
└── bundle/HRVision/      # 精简框架包（cp312 pyd + ProcessIsolate + 精简 __init__，无 .py 源码）
```

打包后配到 `pipeline.json`：

```json
{"id": "yolo_1", "flow": "algo", "python_exe": ".../dist/flow_worker/flow_worker.exe", ...}
```

框架侧自动识别 `.exe` 走 `--hrflow-bootstrap` 协议（`python -c` 与 exe 共用同一
`bootstrap_main` 实现）。已验证：exe 子进程 FPS 与 python 版一致（3.4 @4K），0 错误。

> 打包注意（Anaconda 环境，详见 build.bat 注释）：
> ① `--collect-all Crypto`（pyd 的 import 静态不可见）② 排除 pkg_resources/setuptools
> （PyInstaller 自动 hook 会拖进 plistlib/expat 链）③ conda 的 DLL 依赖
> （ffi.dll/expat.dll/libbz2/liblzma/libssl 等）须 `--add-binary`。

## 运行模式（三选一）

| 模式 | 配置 | 特点 |
|---|---|---|
| **进程隔离（推荐）** | `python_exe: "D:/AIProgram/python.exe"` + `device: "auto"` | 算法流程进程直接跑在 CUDA 环境（GPU 原生推理 ~6ms），少一层转发；相机流程仍在 HRVision 环境 —— **混合双环境管线** |
| GPU worker | `gpu_python: "D:/AIProgram/python.exe"` | 推理转发 D:/AIProgram 起的 worker（不搬流程进程）；`python_exe` 出现后为备用路径 |
| 本进程 CPU | 都不配 | HRVision 环境内 OpenVINO/PyTorch CPU 推理（实测 ~13fps） |

> **进程隔离环境部署**：目标环境（D:/AIProgram）需要框架包 —— 已部署
> `D:/AIProgram/Lib/site-packages/HRVision/`（cp39 pyd + ProcessIsolate + 精简 __init__）。
> 其他环境：`python3.9 -m pip install d:/Python/frame/package/PyHRVision`（需 cp39 pyd）
> 或按 Core 的 Cython 流程编译对应版本。
> 无 PySide6 的环境也兼容（ProgramGlobalData 已条件导入 Qt）。

## 运行

```bash
cd d:/Python/frame/Flow/example/UsbYolo
D:/Anaconda3/envs/HRVision/python.exe HRStar.py     # 或激活 HRVision 环境后 python HRStar.py
```

## 验证

- 窗格标题显示 `FPS + N 个目标 + 类别/置信度`（结果图勾选时）
- 控制台：`[yolo] 模型加载: ...（推理设备 0）`（GPU）→ `[yolo_1] yolo_1 检测完成 count=N`
- 实测（本机 USB 相机 + yolov8n @ RTX3060，进程隔离模式）：FPS ≈ 30，0 错误
  （上限为 USB 相机采集帧率；worker 往返实测 124fps，GPU 推理 6ms 均非瓶颈）

> 模型来自 AI 环境 D:/AiProgram（yolov8n.pt / yolo11n.pt 等）。HRVision 环境已装
> ultralytics+torch（CPU）；配 `python_exe` 后算法进程在 D:/AIProgram（CUDA）跑。
