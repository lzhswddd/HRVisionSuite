# VmDemo —— VM 调用相机 + 算法 + 返回结果 + VM 通信结果

基于 HRFlowController 框架的 **VM（VisionMaster）集成** 例程：
VM 调用相机采图 → 调用算法（VM 方案处理 / 本地算法）→ 返回结果 → 经 **VM 通信设备**发送。

## 结构

```
VmDemo/
├── HRStar.py                  # 入口（纯框架装配）
├── services/
│   ├── vm_bridge.py           # VM 桥接：grab() 采图 / process() 算法 / send_result() 通信
│   └── ui.py                  # 处理窗格 + VM 模式/通信状态栏
└── Flow/
    ├── ProgramGlobalData.py   # ProgramData + vmResult 信号
    ├── pipeline.json          # 拓扑/参数（vm_mode、方案、通信设备 id…）
    ├── main/ camera/ algo/    # 流程节点（收图 → 等帧处理 → 通信回传）
    └── *.ndjs                 # 流程拓扑（编辑器导出，已入库）
```

## 双模式（vm_mode）

| 模式 | 采图（调用相机） | 算法 | 通信结果 |
|---|---|---|---|
| `vm`（真实） | `createSolution/loadSolution` 加载方案 → `runProcedure()`（**方案相机 = VM 全局相机**） | `processProcedure(img, resourceModule)` 推图进 VM 方案处理 | `VisionMasterCore.commSendBytes` + `commSetInt(deviceId, [ok])` |
| `sim`（模拟） | 本地视频流（`sim_fps` 限速模拟相机） | 本地轻量检测链（模板匹配 OK/NG） | 打印 + 计入结果数据（演示全链路） |

> **方案相机使用 VM 的全局相机**：在 VM 软件「设置-全局相机」中注册相机设备，
> 方案内相机模块（ImageSource）配置为引用该全局相机（跨方案复用）；
> 流程端只需 `vm_solution` 指定方案文件（绝对路径可直接用，如
> `D:/Python/frame/ProcessTest/Flow/test.sol`），`runProcedure()` 即按方案从全局相机采图。
>
> 真实模式依赖 PyHRVision 自带模块：`HRVision.VisionMasterProcess`（方案/流程）与
> `HRVision.VisionMasterCore`（方案对象 + 通信设备）。本机未装 VM SDK 时 VisionMasterCore
> 导入会缺 DLL —— 用 `sim` 模式跑通流程，接真实 VM 时改 `vm_mode: "vm"` + 配方案路径。

## 配置（Flow/pipeline.json）

| 节点 | 参数 | 说明 |
|---|---|---|
| `grab_0` (camera) | `vm_mode` | `sim` / `vm` |
| | `sim_source` / `sim_fps` | 模拟视频源 / 模拟帧率 |
| | `vm_procedure` | VM 方案路径（空=默认） |
| `algo_1` (algo) | `vm_procedure` / `vm_resource_module` | 方案 / 推图资源模块名 |
| | `vm_device_id` | VM 通信设备 id（commSendBytes/commSetInt 目标） |

## 运行

```bash
cd d:/Python/frame/Flow/example/VmDemo
python HRStar.py
```

## 验证

- 状态栏：`VM 结果 OK/NG（ms）| SIM 通信: OK (device 1)` 或真实 `VM 通信发送 bytes=… int=…`
- 控制台：`[algo_1] VM 结果 OK | SIM 通信: OK (device 1)`
- 实测（sim 模式 25fps）：收图 → 判定 → 通信回传循环，FPS ≈ 12（结果图降频 2），0 错误
