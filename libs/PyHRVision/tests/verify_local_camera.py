"""LocalCamera 重构回归验证：重构前后行为一致（不依赖 pytest，直接 python 运行）"""
import os
import sys
import tempfile
import types

# 包未安装时保证 tests/ 下脚本可独立运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        # gain 后处理（加法后帧类型变为浮点）
        cam.SetGain(10.0)
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and frames[0].dtype != numpy.uint8
        cam.SetGain(0.0)
        # camera_type 守卫：非 File 类型禁止取帧
        cam.ChangeType("Video")
        assert cam.GetCameraBuffer()[0] is False
        cam.ChangeType("File")
        assert cam.GetCameraBuffer()[0] is True
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
