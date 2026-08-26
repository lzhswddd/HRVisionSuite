# TriggerPlc —— 单相机触发拍照 + 算法 + OK/NG 发送 PLC

基于 HRFlowController 框架的 **触发式检测 + PLC 通信** 例程：
PLC 触发（线圈/地址上升沿）→ 拍照一帧 → 判定 OK/NG → 结果写 PLC → UI 显示。

## 结构

```
TriggerPlc/
├── HRStar.py                  # 入口（纯框架装配）
├── services/
│   ├── camera_driver.py       # 相机驱动（视频文件 / usb:N）
│   ├── algo_engine.py         # 判定算法（ROI 模板匹配，首帧校准 → OK/NG）
│   ├── plc.py                 # PLC 通信（cModule/PLCInterface 库）+ mock 模拟 PLC
│   └── ui.py                  # 判定窗格 + 触发/PLC 状态栏
└── Flow/
    ├── ProgramGlobalData.py   # ProgramData + triggerFired/triggerResult 信号
    ├── pipeline.json          # 拓扑/参数（触发地址、OK/NG 地址、协议…）
    ├── main/ camera/ algo/    # 流程节点（等待触发 → 拍照 → 判定 → 回传）
    └── *.ndjs                 # 流程拓扑（编辑器导出，已入库）
```

## PLC 通信（cModule/PLCInterface）

- **通信全部走 PLCInterface 库**（PLCDevice.dll + HslCommunication.dll）：
  `d:/Python/cModule/PLCInterface/build/bin/Release/`（可用环境变量 `PLC_LIB_DIR` 覆盖）
- 支持协议：`Modbus` / `ModbusRtu` / `Profinet_Siemens_S200Smart` / `Profinet_Melsec_Mc` 等
- 地址语义（HslCommunication）：`"0".."n"` Modbus 线圈/寄存器；`"M100"`/`"D100"` 按 PLC 而定
- `mock` 模式：本机内置 Modbus TCP 从站**模拟 PLC 设备**（无硬件演示用，外部工具可连）

## 配置（Flow/pipeline.json）

| 节点 | 参数 | 说明 |
|---|---|---|
| `grab_0` (camera) | `plc_mode` | `mock`（内置模拟 PLC）/ `tcp`（真实 PLC） |
| | `plc_type` | 协议（Modbus / Profinet_* 等） |
| | `plc_host` / `plc_port` | PLC 地址 / 端口 |
| | `trigger_addr` / `ok_addr` / `ng_addr` | 触发 / OK / NG 地址 |
| | `auto_trigger_ms` | 自动触发间隔（0=只等 PLC 触发） |
| `algo_1` (algo) | `judge_threshold` | OK/NG 判定阈值（模板匹配分） |

## 运行

```bash
cd d:/Python/frame/Flow/example/TriggerPlc
python HRStar.py
```

## 验证

- 状态栏：`触发拍照 #N` + `判定 OK/NG（score）| PLC: OK→地址`
- 控制台：`[grab_0] 触发拍照 #N`、`[algo_1] 判定 NG score=… NG→2`
- **外部触发**：Modbus 工具（ModbusPoll 等）连 `127.0.0.1:8000` 写触发地址 1 → 立即触发一次
- **结果回读**：触发后读 ok/ng 地址，能看到结果线圈状态
- 实测（mock 模式 + 1s 自动触发）：触发/判定/PLC 写入循环 0 错误
