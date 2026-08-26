# CameraBase + VideoCamera 设计文档

日期：2026-08-25
状态：已批准（用户确认设计方案）

## 背景与目标

`LocalCamera`（[HRVision/utils/local_camera.py](../HRVision/utils/local_camera.py)）是一个纯 Python 的"图片文件"相机实现，模拟官方 `Camera` 接口（定义于 [HRVision/HRCamera.pyi](../HRVision/HRCamera.pyi)，对应 C++ 后端 HRFlowController）。

目标：
1. 新增 `VideoCamera`：使用 OpenCV `cv2.VideoCapture` 读取视频流（视频文件 + RTSP/HTTP 网络流）的相机模块，遵循 `Camera` 接口。
2. 将 `LocalCamera` 与 `VideoCamera` 共有的接口抽象为基类 `CameraBase`，接口以 `HRCamera.pyi` 的 `Camera` 为权威基准。
3. `LocalCamera` 重构为继承基类，**行为完全不变**，调用方零影响。

## 接口基准：Camera（HRCamera.pyi）

基类方法集严格对齐以下 19 个方法（签名含 typing 注解风格一致）：

| 方法 | 签名 | 分类 |
|---|---|---|
| `ChangeType` | `(cameraType: str) -> bool` | 通用 |
| `Close` | `() -> tuple[bool, str]` | 抽象 |
| `GetCameraBuffer` | `(timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]` | 抽象 |
| `GetConfig` | `() -> dict` | 抽象 |
| `GetExposureTime` | `() -> tuple[float, str]` | 通用 |
| `GetGain` | `() -> tuple[float, str]` | 通用 |
| `GetValue` | `(key: str) -> tuple[typing.Any, str]` | 通用 |
| `Grab` | `() -> tuple[bool, str]` | 抽象 |
| `IsGrabbing` | `() -> tuple[bool, str]` | 抽象 |
| `IsOpened` | `() -> tuple[bool, str]` | 抽象 |
| `LoadConfig` | `(fileName: str) -> bool` | 通用 |
| `Open` | `() -> tuple[bool, str]` | 抽象 |
| `SaveConfig` | `(fileName: str) -> bool` | 通用 |
| `SetConfig` | `(config: dict) -> None` | 抽象 |
| `SetExposureTime` | `(timeMs: typing.SupportsFloat) -> tuple[bool, str]` | 通用 |
| `SetGain` | `(gain: typing.SupportsFloat) -> tuple[bool, str]` | 通用 |
| `SetReciveBufferCallback` | `(callback, context: typing.Any = None) -> None` | 抽象 |
| `SetValue` | `(key: str, value: typing.Any) -> tuple[bool, str]` | 通用 |
| `Stop` | `() -> tuple[bool, str]` | 抽象 |

注：`timeOut` 参数在拉取式语义下不参与阻塞，忽略（与 LocalCamera 现状一致）。

## 架构

```
HRVision/utils/
├── camera_base.py     ← 新增：CameraBase（abc.ABC）
├── local_camera.py    ← 重构：LocalCamera(CameraBase)，行为不变
├── video_camera.py    ← 新增：VideoCamera(CameraBase)
└── __init__.py        ← 追加导出 CameraBase、VideoCamera（现有导出不动）
```

## CameraBase 设计（camera_base.py）

- 继承 `abc.ABC`，禁止直接实例化。
- **共有状态**：`camera_type`（`__init__(self, cameraType: str = "opencv", **kwargs)`，默认值沿用 LocalCamera）、`exposure_time`、`gain`、`_param`。
- **通用实现（基类提供，子类复用）**：
  - `__init__`、`__del__`（调用 `Close()`）、`ChangeType`
  - `GetExposureTime/SetExposureTime`、`GetGain/SetGain`：存取 `exposure_time`/`gain` 属性
  - `GetValue/SetValue`：`exposure_time`/`gain` 走专用方法，其余存 `_param`
  - `LoadConfig/SaveConfig`：返回"不可用"（与 LocalCamera 现状一致）
- **抽象方法（`@abstractmethod`，子类必须实现）**：`Open`、`Close`、`Grab`、`Stop`、`GetCameraBuffer`、`GetConfig`、`SetConfig`、`IsGrabbing`、`IsOpened`、`SetReciveBufferCallback`。

## LocalCamera 重构（local_camera.py）

- `class LocalCamera(CameraBase)`，删除与基类重复的通用方法（`ChangeType`、`GetExposureTime`、`SetExposureTime`、`GetGain`、`SetGain`、`GetValue`、`SetValue`、`LoadConfig`、`SaveConfig` 中基类已覆盖的部分）。
- 保留 File 特有逻辑：`file_paths` 文件/目录扫描（图片后缀列表）、`image_paths` 索引推进与循环、`exposure_time/gain` 帧后处理、`user_callback` 调用、`_index/_reord_index` 状态机。
- `SetConfig/GetConfig` 保留 File 特有字段（`file_paths`、`image_paths`）。
- 签名、返回值格式、`cameraType="File"` 语义不变。

## VideoCamera 设计（video_camera.py）

`class VideoCamera(CameraBase)`，`cameraType="Video"`（默认在 `__init__` 中设为 "Video"）。

### 状态

- `file_paths: list`：视频文件路径（`.mp4/.avi/.mkv/.mov/.wmv` 等）或网络流（`rtsp://`、`http://`、`https://` 前缀）
- `_capture: cv2.VideoCapture | None`：当前源的读取句柄
- `_index`：当前源在 `file_paths` 中的位置（-1 = 未 Grab）；`_reord_index`：Stop 前位置，用于恢复
- 继承基类的 `exposure_time`、`gain`、`_param`

### 数据流

```
SetConfig({file_paths}) → Open() 校验源（不打开句柄）
    → Grab() 打开第一个源：cv2.VideoCapture(path)，检查 isOpened()
    → 循环 GetCameraBuffer()：
        capture.read() 成功 → 后处理（exposure/gain/user_callback）→ 返回 [frame]
        read 失败/到末尾 → 释放当前源，打开下一个源继续
        全部源耗尽 → 回到第一个源（循环）
    → Stop() 释放句柄，_index=-1；Close() = Stop + 清空
```

- 拉取式逐帧：每次 `GetCameraBuffer()` 推进一帧。
- 源切换时重新打开 `VideoCapture`，天然回到该源第一帧。
- 帧后处理与 LocalCamera 一致：`exposure_time > 0` 时 `image * (exposure_time / 1000.0)`；`gain > 0` 时 `image + gain`；`user_callback` 存在时 `image = user_callback(image, context)`。

### 方法实现要点

| 方法 | 行为 |
|---|---|
| `Open()` | `file_paths` 为空 → 返回失败；逐项校验：文件存在或带流前缀（rtsp://、http://、https://）；无效项跳过；全部无效 → 返回失败；否则成功 |
| `IsOpened()` | `len(file_paths) > 0` 且存在有效源 |
| `Grab()` | 从 `_reord_index` 或 0 开始，打开第一个有效源（失败则尝试下一个），全部失败 → 返回失败 |
| `Stop()` | `_reord_index = _index`，`_index = -1`，释放 `_capture` |
| `GetCameraBuffer()` | 见数据流；未 Grab → `"Camera is not Grabbing."` |
| `GetConfig()/SetConfig()` | `camera_type`、`file_paths`、`exposure_time`、`gain` |
| `SetReciveBufferCallback` | 空实现（拉取式不需要推送回调） |
| `Close()` | `Stop()` + 清空 `file_paths` |

### 错误处理

- 网络流断流（`read()` 返回 False）：若当前源是网络流（非本地文件），尝试重新打开该源一次；仍失败则切换下一源。
- 无并发线程，全同步。

## 测试与验证

1. `LocalCamera` 重构后：运行其 `__main__` 自测段，行为与重构前一致。
2. `VideoCamera`：`__main__` 自测段，用本地视频文件逐帧 `imshow` 验证；验证多源依次播放+循环、源到末尾自动切换。
3. `CameraBase` 因 `abc.ABC` 不可直接实例化（构造报 `TypeError`）——不写专门测试，靠抽象机制保证。
4. RTSP 网络流依赖外部设备，由用户运行期验证。

## 兼容性与风险

- 基类方法签名严格沿用 `LocalCamera` 现有签名与 `HRCamera.pyi` 定义。
- [HRVision/utils/__init__.py](../HRVision/utils/__init__.py) 现有导出（`LocalCamera`）不变，仅追加 `CameraBase`、`VideoCamera`。
- 不动 `HRCamera.pyi`、C++ 后端及 `HRVision/__init__.py` 中 `create_parameter_tree` 的使用方式。
- 命名 `CameraBase` 避开 `.pyi` 中的 `Camera`，不遮蔽 C++ 后端类。

## 非目标（YAGNI）

- 不做后台线程推送（`SetReciveBufferCallback` 保持空实现）。
- 不支持 USB 摄像头设备索引。
- 不做 seek/倍速/暂停控制。
- 不做配置文件的真实读写。
