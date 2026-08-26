"""CameraBase 基类验证：抽象机制 + 通用方法（不依赖 pytest，直接 python 运行）"""
import os
import sys
import types

# 以脚本方式运行（python tests/xxx.py）时 sys.path[0] 是 tests/ 目录，
# 需手动将仓库根目录加入 sys.path，否则无法导入 HRVision 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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

    # 3. SetValue 委派路径与 gain 键读取
    cam.SetValue("exposure_time", 5.0)
    assert cam.GetExposureTime()[0] == 5.0
    cam.SetValue("gain", 2.0)
    assert cam.GetGain()[0] == 2.0
    assert cam.GetValue("gain")[0] == 2.0
    print("verify_camera_base: OK")


if __name__ == "__main__":
    main()
