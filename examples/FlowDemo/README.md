# FlowDemo

基于 HRFlowController 框架的通用管线演示项目：**任意流程拓扑 + 声明式通道 + 多运行模式**。

> 流程代码（.ndjs 拓扑 → 节点 .py → 框架装配 → pipeline.json 运行时拓扑）的生成与修改详见 **[生成流程代码说明.md](生成流程代码说明.md)**。

## 架构总览

```
┌──────────────────────────── 主进程（UI/调度/监控）────────────────────────────┐
│                                                                              │
│  MainWindow（hrfluentwidgets CameraView 网格）    Monitor（seq FPS/MEM）      │
│       ▲ 读显示槽（定时器，seq 变化才刷新）              ▲ seq 增量统计          │
│       │                                                  │                   │
│  ┌────┴──────────────────────────────────────────────────┴─────┐             │
│  │  显示槽（DisplaySlot 共享内存，单写单读覆盖写）               │             │
│  │  origin 槽：相机写（多窗格共享一段）                         │             │
│  │  res 槽：算法写（每算法一段，可配置共享）                    │             │
│  └────▲──────────────────────────────────────────────────▲─────┘             │
│       │ write（throttle 降频）                  │ write                    │
│  ┌────┴─────────┐  queue（shm/线程）    ┌───────┴─────────┐                │
│  │ grabber 节点 │──ch_xxx──▶──────────▶│ algo 节点        │                │
│  │ flow=camera  │                      │ flow=algo        │                │
│  │ mode=?       │                      │ mode=?           │                │
│  └──────────────┘                      └───────┬──────────┘                │
│                                                │ algoResult（SignalProgram │
│                                                │ relay：子进程→主进程）      │
│  PipelineManager：解析 pipeline_spec → 建通道 → 按节点 mode 启动             │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 核心概念

### 1. pipeline_spec（外部配置，JSON）

拓扑、运行方式、联通方式全部由 `Flow/pipeline.json` 声明（`ProgramGlobalData` 启动时加载，无文件则用内置默认 1:1）：

```json
{
  "run_mode": "process",
  "nodes": [
    {"id": "grabber_1", "flow": "camera", "source": "videos/ccd1.avi",
     "mode": "process", "display_divisor": 3},
    {"id": "algo_1", "flow": "algo", "algo_load": 1,
     "signal_divisor": 2, "mode": "process"}
  ],
  "channels": [
    {"id": "ch_grabber_1_algo_1", "from": "grabber_1", "to": "algo_1",
     "kind": "queue", "maxlen": 1, "overflow": "drop_oldest"},
    {"id": "ch_grabber_1_origin", "from": "grabber_1", "to": "ui",
     "kind": "shm", "slot": "origin"},
    {"id": "ch_algo_1_res", "from": "algo_1", "to": "ui",
     "kind": "shm", "slot": "res"}
  ],
  "panes": [
    {"id": "pane_algo_1", "node": "algo_1",
     "origin": "ch_grabber_1_origin", "res": "ch_algo_1_res"}
  ]
}
```

| 段 | 说明 |
|---|---|
| `nodes` | 流程实例。`flow` = 项目流程名（`proCtrls[flow]`/`thCtrls[flow]`），任意流程无假设；`mode` = process/thread（缺省继承 run_mode）；其余参数原样注入节点 |
| `channels` | 数据通道。`kind="queue"` DataBus 队列 / `kind="shm"` DisplaySlot 内存映射（槽名=通道 id）；`to="ui"` 进显示系统 |
| `panes` | 显示窗格：`origin`/`res` 通道组合（勾选切换），`node` 关联结果信号源 |

### 2. 节点开发（业务代码，<30 行）

节点只写业务，通道由框架注入的**聚合通道**访问：

```python
# Flow/algo/等帧处理_a2.py —— 三步结构
frame = thData.channel_in.get(timeout=3)                        # ① 取输入
res, result = AlgoEngine.process(frame, thData.algo_load, ...)  # ② 算（真实检测数据）
thData.channel_out.write(res, throttle=thData.signal_divisor)   # ③ 推输出（降频）
signal_instance.algoResult.emit(thData.algo_key, result)        #    结果信号
```

- `channel_in`：聚合读（从第一个 in 通道 get）
- `channel_out`：聚合写（`put`=队列每帧 / `write(data, throttle=N)`=映射内部降频）
- 节点**不关心**通道类型/数量/id——拓扑全在配置

### 3. 双传输机制

| 数据 | 机制 | 频度 |
|---|---|---|
| 大图（原图/结果图） | 显示槽（共享内存覆盖写，seq 提交标记） | 写方自主（throttle），UI 定时器按 seq 变化读 |
| 小数据（检测结果/状态/事件） | SignalProgram relay（pipe 消息） | 降频消息 |

### 4. 运行模式（任意混搭）

| 组合 | 通道模式（自动推导） | 适用 |
|---|---|---|
| 全线程 | 线程队列（零拷贝） | 轻负载 fan-out 最快 |
| 全进程 | 共享内存 | 多相机重负载隔离 |
| 相机线程 + 算法进程 | 共享内存 | 相机快算法重 |
| 相机进程 + 算法线程 | 共享内存 | 相机采集吃 CPU、算法轻 |

通道模式规则：**任一方是进程 → 共享内存（跨进程安全）；双方线程 → 线程队列**。

## 快速开始

```bash
# 1. 环境依赖（HRVision 包 + hrfluentwidgets）
pip install -e d:/Python/frame/package/PyHRVision

# 2. 启动（窗口关闭优雅停止管线）
#    流程拓扑 Flow/*.ndjs 与模拟视频 Flow/videos/ 已随仓库提交，无需生成
python HRStar.py
```

### 配置工作流

```bash
python -c "from HRVision.HRFlowController import make_pipeline_spec, export_pipeline_spec; \
export_pipeline_spec(make_pipeline_spec({'grabber_1': {'flow':'camera','source':'videos/ccd1.avi'}}, \
{'algo_1': {'flow':'algo','algo_load':1}}), 'Flow/pipeline.json')"   # 导出默认配置
# 编辑 pipeline.json（拓扑/模式/通道/降频）→ 重启生效
```

代码里单步配置：

```python
from HRVision.HRFlowController import PipelineSpecBuilder, PipelineManager
spec = (PipelineSpecBuilder("process")
        .add_node("grabber_1", flow="camera", source="videos/ccd1.avi", mode="thread")
        .add_node("algo_1", flow="algo", algo_load=1, mode="process")
        .add_channel("ch_grabber_1_algo_1", "grabber_1", "algo_1", kind="queue")
        .add_channel("ch_grabber_1_origin", "grabber_1", "ui", kind="shm", slot="origin")
        .add_channel("ch_algo_1_res", "algo_1", "ui", kind="shm", slot="res")
        .add_pane("pane_algo_1", node="algo_1",
                  origin="ch_grabber_1_origin", res="ch_algo_1_res")
        .build())
pipeline = PipelineManager(gData, signal_instance, spec, gData.user)
pipeline.start()
```

## 项目结构

```
FlowDemo/
├── HRStar.py                 # 入口：纯框架装配（--flow --main → HRFlowController.main）
├── services/
│   ├── camera_driver.py      # VideoCamera 视频流驱动
│   ├── algo_engine.py        # 多阶段检测链（金字塔/模板匹配/形态学/连通域）+ 真实结果数据
│   └── ui.py                 # CameraView 窗格网格 + 结果消费（pane_nodes 路由）
└── Flow/
    ├── ProgramGlobalData.py  # ProgramData（全字段类型注解）+ SignalProgram + pipeline_spec 加载
    ├── pipeline.json         # 外部管线配置（拓扑/模式/通道/窗格）
    ├── main/                 # 主流程节点（启动管线 → 创建 UI → qApp.exec_）
    ├── camera/               # 相机流程节点（抓帧 → channel_out 推）
    └── algo/                 # 算法流程节点（channel_in 取 → 算 → channel_out 推 + 结果信号）
```

## 框架能力（HRVision.HRFlowController）

| 组件 | 职责 |
|---|---|
| `build_processes` / `_Controller` | 流程构建（.ndjs 解密 + 图装配） |
| `ProcessStartor.python_exe` | **指定解释器跑进程流程**：节点参数或 spec 顶层 `python_exe` 配目标环境 python（如 `D:/AIProgram/python.exe`），该节点子进程用目标环境拉起（目标环境须能 import HRVision，cp 版本匹配）；未配则当前环境 spawn |
| `DataBus` | 消息队列（thread/process 双模式，大对象 uid 槽，槽位自适应） |
| `_FrameBuffer` / `DisplaySlot` | 帧共享内存 / 显示槽封装（命名/reshape/seq/共享） |
| `PipelineManager` | 通用图解释器：任意流程 + 声明式通道 + 节点级运行模式 |
| `PipelineSpecBuilder` | spec 单步配置（add_node/add_channel/add_pane → build） |
| `make/export/load/validate_pipeline_spec` | 配置工具（JSON） |
| `Monitor` | 槽 seq FPS 统计 + 子进程 MEM + 线程栈 |
| `_SignalRelay` / `_SignalProxy` | 子进程信号 → 主进程真实 emit |

## 性能实测（4K 3840×2160，load=1 多阶段检测链）

| 配置 | 结果 |
|---|---|
| 全进程 1:1 | FPS 3.4/窗格，0 错误 |
| 相机线程+算法进程 | FPS 3.9，0 错误 |
| 相机进程+算法线程 | FPS 3.4，0 错误 |
| 8 算法 fan-out（旧 1×8） | 每算法 1-2 FPS，聚合 ~27（相机端瓶颈） |

- 相机端瓶颈：4K 解码 20ms + 24.9MB shm 写 ≈ 37ms/帧
- 关键调优：`cv2.setNumThreads(1)`（进程模式多消费者线程池爆炸的修复）、显示槽 throttle 降频、UI seq 变化才刷新

## 发布流程（框架更新）

```
ProcessTest（框架源码）→ Nuitka 编译 → pyd
  → 复制 site-packages/HRVision + PyHRVision/HRVision（两处）
  → pip install --force-reinstall d:/Python/frame/package/PyHRVision（环境）
  → git commit + push（PyHRVision main → GitHub）
```
