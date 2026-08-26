# CameraBase + VideoCamera 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `CameraBase` 抽象基类（接口对齐 `HRCamera.pyi` 的 `Camera`）和基于 OpenCV `VideoCapture` 的 `VideoCamera` 视频流相机，并重构 `LocalCamera` 继承基类（行为不变）。

**Architecture:** 三文件结构：`camera_base.py`（abc.ABC 基类，19 个接口方法，通用方法给默认实现）、`local_camera.py`（重构继承，仅保留 File 特有逻辑）、`video_camera.py`（新实现：视频文件 + RTSP/HTTP 网络流，拉取式逐帧，多源依次播放+循环）。

**Tech Stack:** Python 3、OpenCV（cv2.VideoCapture/VideoWriter）、abc、numpy、typing。

**设计文档:** `docs/superpowers/specs/2026-08-25-camera-base-design.md`（已批准）

**环境注意事项（重要，先读）：**
- 本仓库 `HRVision/utils/__init__.py:4` 有 `from .TrainWatcherPrv import *`，依赖缺失的私有模块 `Ultralytics`。直接 `import HRVision.utils` 会报 `ModuleNotFoundError`。**这是预存在问题，不要修改 `TrainWatcherPrv` 相关文件**。所有验证脚本的开头通过注入空占位模块绕过（见下）。
- 运行命令在项目根目录 `d:\Python\frame\package\PyHRVision` 执行。
- 项目无 pytest 基础设施，验证脚本为纯 `assert` 脚本（`python tests/xxx.py` 直接运行，退出码 0 即通过）。
- 基类消息文本与 `LocalCamera` 原版有意的微小差异：去掉了消息中的 "local" 字样（如 `"Exposure time is not applicable for camera."`）。接口签名、返回值格式、语义不变。`LocalCamera.GetConfig()` 不含 `file_paths` 键（保持原样，不改）。
- 每个任务提交时只 `git add` 本任务涉及的文件（工作区有其他与本任务无关的未提交修改：`HRVision/bin/*.dll` 等，勿碰）。

**文件结构：**

| 文件 | 责任 | 动作 |
|---|---|---|
| `HRVision/utils/camera_base.py` | 抽象基类：19 个接口方法，通用方法默认实现 | 新建 |
| `HRVision/utils/local_camera.py` | 图片文件相机（File 语义），继承基类 | 重构 |
| `HRVision/utils/video_camera.py` | 视频流相机（Video 语义），继承基类 | 新建 |
| `HRVision/utils/__init__.py` | 追加导出 `CameraBase`、`VideoCamera` | 修改 |
| `tests/verify_camera_base.py` | 基类验证（抽象机制 + 通用方法） | 新建 |
| `tests/verify_local_camera.py` | LocalCamera 回归验证（重构前后行为一致） | 新建 |
| `tests/verify_video_camera.py` | VideoCamera 功能验证 | 新建 |

---

### Task 1: CameraBase 抽象基类

**Files:**
- Create: `HRVision/utils/camera_base.py`
- Test: `tests/verify_camera_base.py`

- [ ] **Step 1: 编写验证脚本（此时 camera_base.py 不存在，先确认失败路径）**

创建 `tests/verify_camera_base.py`：

```python
"""CameraBase 基类验证：抽象机制 + 通用方法（不依赖 pytest，直接 python 运行）"""
import sys
import types


def main():
    # 绕过 utils/__init__.py 中缺失的 TrainWatcherPrv.Ultralytics 私有模块
    stub = types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics')
    sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics', stub)

    from HRVision.utils.camera_base import CameraBase

    # 1. 抽象类不可直接实例化
    try:
        CameraBase()
        raise AssertionError("CameraBase 应不可实例化")
    except TypeError:
        pass

    # 2. 子类实现抽象方法后可实例化，通用方法行为正确
    class Dummy(CameraBase):
        def Open(self):
            return True, "open"

        def Close(self):
            return True, "close"

        def Grab(self):
            return True, "grab"

        def Stop(self):
            return True, "stop"

        def GetCameraBuffer(self, timeOut=1000):
            return True, [], "buffer"

        def GetConfig(self):
            return {}

        def SetConfig(self, config):
            pass

        def IsGrabbing(self):
            return False, ""

        def IsOpened(self):
            return False, ""

        def SetReciveBufferCallback(self, callback, context=None):
            pass

    cam = Dummy("Test")
    assert cam.camera_type == "Test"
    assert cam.ChangeType("X") is True and cam.camera_type == "X"
    assert cam.SetExposureTime(5.0) == (True, "Exposure time set to 5.0 ms.")
    assert cam.GetExposureTime()[0] == 5.0
    assert cam.SetGain(2.0) == (True, "Gain set to 2.0.")
    assert cam.GetGain()[0] == 2.0
    assert cam.SetValue("foo", 1)[0] is True
    assert cam.GetValue("foo")[0] == 1
    assert cam.GetValue("missing")[0] is None
    assert cam.GetValue("exposure_time")[0] == 5.0
    assert cam.LoadConfig("a.json")[0] is True
    assert cam.SaveConfig("a.json")[0] is True
    print("verify_camera_base: OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行验证脚本，确认失败**

Run: `python tests/verify_camera_base.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'HRVision.utils.camera_base'`

- [ ] **Step 3: 实现 CameraBase**

创建 `HRVision/utils/camera_base.py`（完整内容）：

```python
import abc
import collections.abc
import numpy
import typing

class CameraBase(abc.ABC):
    """
    相机抽象基类，接口对齐 HRCamera.pyi 中的 Camera。
    子类必须实现：Open、Close、Grab、Stop、GetCameraBuffer、GetConfig、
    SetConfig、IsGrabbing、IsOpened、SetReciveBufferCallback。
    """
    def __init__(self, cameraType: str = "opencv", **kwargs) -> None:
        """
        初始化相机
        """
        self.camera_type = cameraType
        self.exposure_time = kwargs.get("exposure_time", 0.0)
        self.gain = kwargs.get("gain", 0.0)
        self._param = {}

    def __del__(self) -> None:
        self.Close()

    def ChangeType(self, cameraType: str) -> bool:
        """
        更改相机类型
        """
        self.camera_type = cameraType
        return True

    def GetExposureTime(self) -> tuple[float, str]:
        """
        获取曝光时间
        """
        return self.exposure_time, "Exposure time is not applicable for camera."

    def GetGain(self) -> tuple[float, str]:
        """
        获取增益
        """
        return self.gain, "Gain is not applicable for camera."

    def GetValue(self, key: str) -> tuple[typing.Any, str]:
        """
        获取相机参数
        """
        if key == "exposure_time":
            return self.exposure_time, "Exposure time is not applicable for camera."
        elif key == "gain":
            return self.gain, "Gain is not applicable for camera."
        else:
            if key in self._param:
                return self._param[key], f"Parameter '{key}' retrieved successfully."
            else:
                return None, f"Unknown parameter: {key}"

    def LoadConfig(self, fileName: str) -> bool:
        """
        加载相机配置
        """
        return True, "Loading configuration is not applicable for camera."

    def SaveConfig(self, fileName: str) -> bool:
        """
        保存相机配置
        """
        return True, "Saving configuration is not applicable for camera."

    def SetExposureTime(self, timeMs: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置曝光时间
        """
        self.exposure_time = timeMs
        return True, f"Exposure time set to {timeMs} ms."

    def SetGain(self, gain: typing.SupportsFloat) -> tuple[bool, str]:
        """
        设置增益
        """
        self.gain = gain
        return True, f"Gain set to {gain}."

    def SetValue(self, key: str, value: typing.Any) -> tuple[bool, str]:
        """
        设置相机参数
        """
        if key == "exposure_time":
            return self.SetExposureTime(value)
        elif key == "gain":
            return self.SetGain(value)
        else:
            self._param[key] = value
            return True, f"Parameter '{key}' set successfully."

    @abc.abstractmethod
    def Open(self) -> tuple[bool, str]:
        """
        打开相机
        """

    @abc.abstractmethod
    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """

    @abc.abstractmethod
    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据
        """

    @abc.abstractmethod
    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """

    @abc.abstractmethod
    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据
        """

    @abc.abstractmethod
    def GetConfig(self) -> dict:
        """
        获取相机配置
        """

    @abc.abstractmethod
    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """

    @abc.abstractmethod
    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """

    @abc.abstractmethod
    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """

    @abc.abstractmethod
    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调
        """
```

- [ ] **Step 4: 运行验证脚本，确认通过**

Run: `python tests/verify_camera_base.py`
Expected: PASS — 输出 `verify_camera_base: OK`，退出码 0

- [ ] **Step 5: 提交**

```bash
git add HRVision/utils/camera_base.py tests/verify_camera_base.py
git commit -m "feat: 添加 CameraBase 相机抽象基类"
```

---

### Task 2: LocalCamera 重构为继承 CameraBase

**Files:**
- Modify: `HRVision/utils/local_camera.py`（整体替换为下方代码）
- Test: `tests/verify_local_camera.py`

- [ ] **Step 1: 编写回归验证脚本（对重构前的 LocalCamera 先建立行为基线）**

创建 `tests/verify_local_camera.py`：

```python
"""LocalCamera 重构回归验证：重构前后行为一致（不依赖 pytest，直接 python 运行）"""
import os
import sys
import tempfile
import types


def main():
    # 绕过 utils/__init__.py 中缺失的 TrainWatcherPrv.Ultralytics 私有模块
    stub = types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics')
    sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics', stub)

    import cv2
    import numpy
    from HRVision.utils.local_camera import LocalCamera

    # 构造 3 张测试图片
    tmp_dir = tempfile.mkdtemp()
    paths = []
    for i in range(3):
        p = os.path.join(tmp_dir, f"img_{i}.png")
        cv2.imwrite(p, numpy.full((32, 32, 3), i * 50, numpy.uint8))
        paths.append(p)

    try:
        cam = LocalCamera(cameraType="File")
        cam.SetConfig({"file_paths": [tmp_dir]})
        # Open：扫描目录得到 3 张图
        ok, _ = cam.Open()
        assert ok is True
        assert cam.IsOpened()[0] is True
        # 未 Grab 时取帧失败
        assert cam.GetCameraBuffer()[0] is False
        # Grab 后逐帧读取，3 张后循环
        cam.Grab()
        assert cam.IsGrabbing()[0] is True
        first_frame = None
        for _ in range(3):
            ok, frames, _ = cam.GetCameraBuffer()
            assert ok and len(frames) == 1
            if first_frame is None:
                first_frame = frames[0]
        # 第 4 次回到第一张
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and numpy.array_equal(frames[0], first_frame)
        # 曝光/增益后处理（乘系数后帧类型变为浮点）
        cam.SetExposureTime(2000.0)
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and frames[0].dtype != numpy.uint8
        cam.SetExposureTime(0.0)
        # 基类通用方法可用：ChangeType / SetValue 自定义参数 + user_callback
        assert cam.ChangeType("File") is True
        cam.SetValue("user_callback", lambda img, ctx: img)
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok
        # Stop 后停止取帧，Grab 恢复
        cam.Stop()
        assert cam.IsGrabbing()[0] is False
        assert cam.GetCameraBuffer()[0] is False
        cam.Grab()
        assert cam.IsGrabbing()[0] is True
        # 配置读写
        cfg = cam.GetConfig()
        assert cfg["camera_type"] == "File"
        assert len(cfg["image_paths"]) == 3
        # 关闭
        assert cam.Close()[0] is True
        assert cam.IsOpened()[0] is False
        print("verify_local_camera: OK")
    finally:
        for p in paths:
            os.remove(p)
        os.rmdir(tmp_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行回归脚本，确认重构前基线通过**

Run: `python tests/verify_local_camera.py`
Expected: PASS — 输出 `verify_local_camera: OK`，退出码 0（断言针对现有行为，验证脚本与基类无关）

- [ ] **Step 3: 重构 LocalCamera**

将 `HRVision/utils/local_camera.py` 整体替换为（完整内容，行为与原版一致，删除与基类重复的通用方法）：

```python
import collections.abc
from pathlib import Path
import numpy
import typing
import cv2
import os
from .camera_base import CameraBase

class LocalCamera(CameraBase):
    def __init__(self, cameraType: str = "opencv", **kwargs) -> None:
        """
        初始化相机
        """
        super().__init__(cameraType, **kwargs)
        self.file_paths = kwargs.get("file_paths", [])
        self.image_paths = kwargs.get("image_paths", [])
        self.index = -1
        self.reord_index = -1

    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """
        self.Stop()
        self.image_paths = []
        return True, "Camera closed successfully."

    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据
        """
        if self.camera_type != "File" or not self.image_paths:
            return False, [], "Camera type is not 'File' or no image paths provided."

        if self.index < 0:
            return False, [], "Camera is not Grabbing."

        if self.index >= len(self.image_paths):
            return False, [], "No more images to read."

        try:
            with open(self.image_paths[self.index], 'rb') as f:
                data = numpy.frombuffer(f.read(), numpy.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
            if image is None:
                return False, [], f"Failed to decode image. {self.image_paths[self.index]}"

            if self.exposure_time > 0:
                image = image * (self.exposure_time / 1000.0)
            if self.gain > 0:
                image = image + self.gain

            user_callback = self._param.get("user_callback", None)
            if user_callback and callable(user_callback):
                image = user_callback(image, self._param.get("context", None))

            self.index += 1
            if self.index >= len(self.image_paths):
                self.index = 0
            return True, [image], "Image read successfully."
        except Exception as e:
            return False, [], f"Failed to read image: {self.image_paths[self.index]} - {str(e)}"

    def GetConfig(self) -> dict:
        """
        获取相机配置
        """
        return {
            "camera_type": self.camera_type,
            "image_paths": self.image_paths,
            "exposure_time": self.exposure_time,
            "gain": self.gain
        }

    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据
        """
        if self.index < 0:
            if self.reord_index >= 0:
                self.index = self.reord_index
            else:
                self.index = 0
        return True, "Grabbing is not applicable for local camera."

    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """
        return self.index >= 0, "Grabbing is not applicable for local camera."

    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """
        return len(self.image_paths) > 0, "Camera is always open in local mode."

    def Open(self) -> tuple[bool, str]:
        """
        打开相机
        """
        self.image_paths = []
        for path in self.file_paths:
            image_suffix_list = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.raw']
            if os.path.isfile(path):
                if Path(path).suffix.lower() in image_suffix_list:
                    self.image_paths.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(tuple(image_suffix_list)):
                            self.image_paths.append(os.path.join(root, file))
        return self.IsOpened()

    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """
        if "camera_type" in config:
            self.camera_type = config["camera_type"]
        if "file_paths" in config:
            self.file_paths = config["file_paths"]
        if "image_paths" in config:
            self.image_paths = config["image_paths"]
        if "exposure_time" in config:
            self.exposure_time = config["exposure_time"]
        if "gain" in config:
            self.gain = config["gain"]

    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调
        """
        pass

    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """
        self.reord_index = self.index
        self.index = -1
        return True, "Camera stopped successfully."

if __name__ == "__main__":
    camera = LocalCamera(cameraType="File")
    camera.SetConfig({
        "file_paths": [r"C:\Users\public\Documents\MVTec\HALCON-20.11-Steady\examples\images"],
    })
    camera.Open()
    camera.Grab()
    while True:
        success, images, message = camera.GetCameraBuffer()
        if success:
            for img in images:
                cv2.imshow("Image", img)
                cv2.waitKey(33)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        else:
            print(message)
```

重构要点：
- `class LocalCamera(CameraBase)`；`__init__` 调用 `super().__init__(cameraType, **kwargs)`（基类接管 `exposure_time`/`gain`/`_param`/`camera_type`），子类继续设 `file_paths`/`image_paths`/`index`/`reord_index`。
- 删除的重复方法：`__del__`、`ChangeType`、`GetExposureTime`、`GetGain`、`GetValue`、`LoadConfig`、`SaveConfig`、`SetExposureTime`、`SetGain`、`SetValue`（均由基类提供）。
- `__main__` 自测段原样保留。

- [ ] **Step 4: 运行回归脚本，确认重构后仍通过**

Run: `python tests/verify_local_camera.py`
Expected: PASS — 输出 `verify_local_camera: OK`，退出码 0

- [ ] **Step 5: 提交**

```bash
git add HRVision/utils/local_camera.py tests/verify_local_camera.py
git commit -m "refactor: LocalCamera 重构为继承 CameraBase"
```

---

### Task 3: VideoCamera 视频流相机

**Files:**
- Create: `HRVision/utils/video_camera.py`
- Test: `tests/verify_video_camera.py`

- [ ] **Step 1: 编写验证脚本（video_camera.py 尚不存在，确认失败路径）**

创建 `tests/verify_video_camera.py`：

```python
"""VideoCamera 功能验证：多源依次播放+循环、后处理、无效源过滤（不依赖 pytest）"""
import os
import sys
import tempfile
import types


def main():
    # 绕过 utils/__init__.py 中缺失的 TrainWatcherPrv.Ultralytics 私有模块
    stub = types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics')
    sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics', stub)

    import cv2
    import numpy
    from HRVision.utils.video_camera import VideoCamera

    # 生成两个测试视频：A=10帧(亮度50) B=5帧(亮度150)
    tmp_dir = tempfile.mkdtemp()
    video_a = os.path.join(tmp_dir, "a.avi")
    video_b = os.path.join(tmp_dir, "b.avi")

    def make_video(path, frames, brightness):
        w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 64))
        for _ in range(frames):
            w.write(numpy.full((64, 64, 3), brightness, numpy.uint8))
        w.release()

    make_video(video_a, 10, 50)
    make_video(video_b, 5, 150)

    try:
        cam = VideoCamera(cameraType="Video")
        # 无效源被 Open 过滤
        cam.SetConfig({"file_paths": [video_a, os.path.join(tmp_dir, "missing.avi"), video_b]})
        ok, _ = cam.Open()
        assert ok is True
        assert len(cam.file_paths) == 2
        assert cam.IsOpened()[0] is True
        # 未 Grab 时取帧失败
        assert cam.GetCameraBuffer()[0] is False
        # 全部无效时 Open 失败
        cam.SetConfig({"file_paths": [os.path.join(tmp_dir, "missing.avi")]})
        ok, _ = cam.Open()
        assert ok is False
        # 恢复有效源
        cam.SetConfig({"file_paths": [video_a, video_b]})
        assert cam.Open()[0] is True
        # Grab 后依次读取 15 帧（10 + 5）
        cam.Grab()
        assert cam.IsGrabbing()[0] is True
        for _ in range(15):
            ok, frames, _ = cam.GetCameraBuffer()
            assert ok and len(frames) == 1
        # 全部播完后循环：第 16 帧回到第一个源第一帧（亮度 50）
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 50
        # 源切换：第 11 帧来自源 B（亮度 150）
        cam.Stop()
        cam.Grab()
        for _ in range(10):
            cam.GetCameraBuffer()
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 150
        # 曝光后处理生效（乘系数后帧类型变为浮点）
        cam.SetExposureTime(1000.0)
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and frames[0].dtype != numpy.uint8
        cam.SetExposureTime(0.0)
        # Stop 停止；Grab 恢复
        cam.Stop()
        assert cam.IsGrabbing()[0] is False
        assert cam.GetCameraBuffer()[0] is False
        cam.Grab()
        assert cam.IsGrabbing()[0] is True
        # Close 释放
        assert cam.Close()[0] is True
        assert cam.IsOpened()[0] is False
        print("verify_video_camera: OK")
    finally:
        for p in (video_a, video_b):
            os.remove(p)
        os.rmdir(tmp_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行验证脚本，确认失败**

Run: `python tests/verify_video_camera.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'HRVision.utils.video_camera'`

- [ ] **Step 3: 实现 VideoCamera**

创建 `HRVision/utils/video_camera.py`（完整内容）：

```python
import collections.abc
import os
import numpy
import typing
import cv2
from .camera_base import CameraBase

class VideoCamera(CameraBase):
    """
    基于 OpenCV VideoCapture 的视频流相机（视频文件 / RTSP·HTTP 网络流）。
    拉取式逐帧读取；多源依次播放，全部播完后循环；网络流断流时自动重连一次。
    """
    def __init__(self, cameraType: str = "Video", **kwargs) -> None:
        """
        初始化相机
        """
        super().__init__(cameraType, **kwargs)
        self.file_paths = kwargs.get("file_paths", [])
        self._capture = None
        self.index = -1
        self.reord_index = -1

    def _is_network_stream(self, path) -> bool:
        return isinstance(path, str) and path.lower().startswith(("rtsp://", "http://", "https://"))

    def _is_valid_source(self, path) -> bool:
        """
        文件存在，或为网络流地址
        """
        return self._is_network_stream(path) or (isinstance(path, str) and os.path.isfile(path))

    def Close(self) -> tuple[bool, str]:
        """
        关闭相机
        """
        self.Stop()
        self.file_paths = []
        return True, "Camera closed successfully."

    def GetCameraBuffer(self, timeOut: typing.SupportsInt = 1000) -> tuple[bool, list[numpy.ndarray], str]:
        """
        获取相机数据（每次调用读取下一帧，源结束自动切换，全部结束循环）
        """
        if self._capture is None or self.index < 0:
            return False, [], "Camera is not Grabbing."

        ret, frame = self._capture.read()
        if not ret:
            # 网络流断流时尝试重连一次
            if self._is_network_stream(self.file_paths[self.index]):
                ret, frame = self._try_reconnect_frame()
        if not ret:
            if not self._switch_to_next_source():
                return False, [], "No more video sources available."
            ret, frame = self._capture.read()
            if not ret:
                return False, [], "Failed to read frame from video source."

        if self.exposure_time > 0:
            frame = frame * (self.exposure_time / 1000.0)
        if self.gain > 0:
            frame = frame + self.gain

        user_callback = self._param.get("user_callback", None)
        if user_callback and callable(user_callback):
            frame = user_callback(frame, self._param.get("context", None))
        return True, [frame], "Frame read successfully."

    def GetConfig(self) -> dict:
        """
        获取相机配置
        """
        return {
            "camera_type": self.camera_type,
            "file_paths": self.file_paths,
            "exposure_time": self.exposure_time,
            "gain": self.gain
        }

    def Grab(self) -> tuple[bool, str]:
        """
        推送相机数据（打开第一个有效视频源）
        """
        if self.index >= 0:
            return True, "Camera is already grabbing."
        start = self.reord_index if self.reord_index >= 0 else 0
        for i in range(start, len(self.file_paths)):
            cap = cv2.VideoCapture(self.file_paths[i])
            if cap.isOpened():
                self._capture = cap
                self.index = i
                return True, f"Grabbing started from source {i}."
            cap.release()
        return False, "Failed to open any video source."

    def IsGrabbing(self) -> tuple[bool, str]:
        """
        检查相机是否在推送数据
        """
        return self.index >= 0, "Grabbing is not applicable for video camera."

    def IsOpened(self) -> tuple[bool, str]:
        """
        检查相机是否打开
        """
        valid = any(self._is_valid_source(p) for p in self.file_paths)
        return valid, "Camera is opened in video mode."

    def Open(self) -> tuple[bool, str]:
        """
        打开相机（校验视频源，不打开句柄）
        """
        valid_paths = [p for p in self.file_paths if self._is_valid_source(p)]
        if not valid_paths:
            return False, "No valid video sources provided."
        self.file_paths = valid_paths
        return True, "Camera opened successfully."

    def SetConfig(self, config: dict) -> None:
        """
        设置相机配置
        """
        if "camera_type" in config:
            self.camera_type = config["camera_type"]
        if "file_paths" in config:
            self.file_paths = config["file_paths"]
        if "exposure_time" in config:
            self.exposure_time = config["exposure_time"]
        if "gain" in config:
            self.gain = config["gain"]

    def SetReciveBufferCallback(self, callback: typing.Callable[[collections.abc.Sequence[numpy.ndarray], typing.Any], None], context: typing.Any = None) -> None:
        """
        设置接收数据回调（拉取式语义，无需回调，保留接口）
        """
        pass

    def Stop(self) -> tuple[bool, str]:
        """
        停止相机推送
        """
        self.reord_index = self.index
        self.index = -1
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        return True, "Camera stopped successfully."

    def _switch_to_next_source(self) -> bool:
        """
        切换到下一个可打开的视频源（循环）
        """
        n = len(self.file_paths)
        for step in range(1, n + 1):
            idx = (self.index + step) % n
            cap = cv2.VideoCapture(self.file_paths[idx])
            if cap.isOpened():
                if self._capture is not None:
                    self._capture.release()
                self._capture = cap
                self.index = idx
                return True
            cap.release()
        return False

    def _try_reconnect_frame(self) -> tuple[bool, numpy.ndarray]:
        """
        重新打开当前网络流并读取一帧
        """
        if self._capture is not None:
            self._capture.release()
        self._capture = cv2.VideoCapture(self.file_paths[self.index])
        if self._capture.isOpened():
            return self._capture.read()
        return False, None

if __name__ == "__main__":
    import tempfile
    # 生成一个临时测试视频
    tmp_dir = tempfile.gettempdir()
    video_path = os.path.join(tmp_dir, "hrvision_demo_video.avi")
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (320, 240))
    for i in range(30):
        frame = numpy.zeros((240, 320, 3), numpy.uint8)
        cv2.putText(frame, f"frame {i}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()

    camera = VideoCamera(cameraType="Video")
    camera.SetConfig({"file_paths": [video_path]})
    camera.Open()
    camera.Grab()
    while True:
        success, frames, message = camera.GetCameraBuffer()
        if success:
            for frame in frames:
                cv2.imshow("Video", frame)
                cv2.waitKey(33)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        else:
            print(message)
            break
    camera.Close()
    os.remove(video_path)
```

- [ ] **Step 4: 运行验证脚本，确认通过**

Run: `python tests/verify_video_camera.py`
Expected: PASS — 输出 `verify_video_camera: OK`，退出码 0

- [ ] **Step 5: 提交**

```bash
git add HRVision/utils/video_camera.py tests/verify_video_camera.py
git commit -m "feat: 添加基于 OpenCV VideoCapture 的 VideoCamera 视频流相机"
```

---

### Task 4: 导出 CameraBase / VideoCamera 并做总回归

**Files:**
- Modify: `HRVision/utils/__init__.py:1-4`
- Test: `tests/verify_camera_base.py`、`tests/verify_local_camera.py`、`tests/verify_video_camera.py`

- [ ] **Step 1: 修改 utils/__init__.py 追加导出**

将 `HRVision/utils/__init__.py` 的完整内容替换为：

```python
from .camera_base import CameraBase
from .folder_monitor import (FolderMonitor)
from .local_camera import (LocalCamera)
from .train_watcher import (TrainWatcher, GenerateTrainWatcher, GetTrainWatcherList)
from .TrainWatcherPrv import *
from .video_camera import VideoCamera
```

- [ ] **Step 2: 验证包级导出可用**

Run:

```bash
python -c "
import sys, types
stub = types.ModuleType('HRVision.utils.TrainWatcherPrv.Ultralytics')
sys.modules.setdefault('HRVision.utils.TrainWatcherPrv.Ultralytics', stub)
from HRVision.utils import CameraBase, LocalCamera, VideoCamera
assert CameraBase.__name__ == 'CameraBase'
assert issubclass(LocalCamera, CameraBase)
assert issubclass(VideoCamera, CameraBase)
assert LocalCamera().camera_type == 'opencv'
assert VideoCamera().camera_type == 'Video'
print('export OK')
"
```

Expected: PASS — 输出 `export OK`，退出码 0

- [ ] **Step 3: 运行全部验证脚本**

Run:
```bash
python tests/verify_camera_base.py
python tests/verify_local_camera.py
python tests/verify_video_camera.py
```
Expected: 三个脚本全部输出 `verify_*: OK`，退出码均为 0

- [ ] **Step 4: 提交**

```bash
git add HRVision/utils/__init__.py
git commit -m "feat: 导出 CameraBase 和 VideoCamera"
```

---

## 自审记录

- **规格覆盖检查**：接口基准 19 方法 ✓（Task 1 基类全量）；LocalCamera 重构行为不变 ✓（Task 2 + 回归脚本）；VideoCamera 数据流/后处理/断流重连/多源循环 ✓（Task 3）；错误处理（未 Grab、无有效源、读帧失败）✓（Task 3 验证脚本）；导出 ✓（Task 4）。非目标（USB 索引、线程推送、seek）未实现 ✓。
- **占位符检查**：无 TBD/TODO；所有步骤含完整代码与命令。
- **类型一致性**：`_try_reconnect_frame`（Task 3 实现）与 `GetCameraBuffer` 调用处返回类型 `(bool, ndarray)` 一致；`SetConfig`/`GetConfig` 键名（`camera_type`/`file_paths`/`exposure_time`/`gain`）在 LocalCamera 与 VideoCamera 间一致；`CameraBase.__init__` 默认参数 `cameraType="opencv"` 与 `LocalCamera` 原默认一致。
- **验证环境**：cv2 4.13.0、VideoWriter MJPG 生成/读回 10 帧已验证；`LocalCamera` 经 stub 注入后 import 已验证。
