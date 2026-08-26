"""VideoCamera 功能验证：多源依次播放+循环、后处理、无效源过滤（不依赖 pytest）"""
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
    from HRVision.utils.video_camera import VideoCamera

    # 生成测试视频：A=10帧(亮度50) B=5帧(亮度150) Z=0帧(死源)
    tmp_dir = tempfile.mkdtemp()
    video_a = os.path.join(tmp_dir, "a.avi")
    video_b = os.path.join(tmp_dir, "b.avi")
    video_z = os.path.join(tmp_dir, "z.avi")

    def make_video(path, frames, brightness):
        w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (64, 64))
        for _ in range(frames):
            w.write(numpy.full((64, 64, 3), brightness, numpy.uint8))
        w.release()

    make_video(video_a, 10, 50)
    make_video(video_b, 5, 150)
    make_video(video_z, 0, 0)  # 死源：isOpened() 为 True 但 read() 永远失败

    cam = None
    cam_single = None
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
        # gain 后处理
        cam.SetGain(10.0)
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and frames[0].dtype != numpy.uint8
        cam.SetGain(0.0)
        # user_callback 生效
        cam.SetValue("user_callback", lambda img, ctx: numpy.full(img.shape, 7, numpy.uint8))
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 7
        cam.SetValue("user_callback", None)
        # Stop 停止；Grab 恢复
        cam.Stop()
        assert cam.IsGrabbing()[0] is False
        assert cam.GetCameraBuffer()[0] is False
        cam.Grab()
        assert cam.IsGrabbing()[0] is True

        # 场景1：抓取中收缩 file_paths 不应越界（Fix 1 回归）
        cam = VideoCamera("Video")
        cam.SetConfig({"file_paths": [video_a, video_b]})
        assert cam.Open()[0] is True
        cam.Grab()
        for _ in range(10):
            ok, frames, _ = cam.GetCameraBuffer()
            assert ok
        ok, frames, _ = cam.GetCameraBuffer()  # A 耗尽 → 切到 B，index=1
        assert ok and int(frames[0][0, 0, 0]) == 150
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok
        # 抓取中收缩 file_paths（index=1 越界）→ 必须优雅返回而非抛 IndexError
        cam.SetConfig({"file_paths": [video_a]})
        ok, frames, message = cam.GetCameraBuffer()
        assert ok is False
        assert "No more video sources" in message

        # 场景2：死源 Z 被跳过（Fix 2 回归）
        cam = VideoCamera("Video")
        cam.SetConfig({"file_paths": [video_a, video_z, video_b]})
        assert cam.Open()[0] is True
        cam.Grab()
        for _ in range(15):
            ok, frames, _ = cam.GetCameraBuffer()
            assert ok and len(frames) == 1
        # 第 16 帧：A(10)→跳过 Z→B(5)→循环回 A 第 1 帧（亮度 50）
        ok, frames, _ = cam.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 50

        # 场景3：USB 设备索引（int）作为有效源
        cam_usb = VideoCamera(cameraType="Video")
        cam_usb.SetConfig({"file_paths": [0]})
        ok, _ = cam_usb.Open()
        assert ok is True
        assert cam_usb.file_paths == [0]
        assert cam_usb.IsOpened()[0] is True
        # 负索引无效
        cam_usb.SetConfig({"file_paths": [-1]})
        ok, _ = cam_usb.Open()
        assert ok is False
        # 混合：视频文件 + 设备索引
        cam_usb.SetConfig({"file_paths": [video_a, 0]})
        ok, _ = cam_usb.Open()
        assert ok is True and len(cam_usb.file_paths) == 2
        cam_usb.Close()

        # 单源 n=1 循环：10 帧播完回到第一帧（亮度 50）
        cam_single = VideoCamera(cameraType="Video")
        cam_single.SetConfig({"file_paths": [video_a]})
        assert cam_single.Open()[0] is True
        assert cam_single.Grab()[0] is True
        ok, frames, _ = cam_single.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 50
        for _ in range(9):
            cam_single.GetCameraBuffer()
        ok, frames, _ = cam_single.GetCameraBuffer()
        assert ok and int(frames[0][0, 0, 0]) == 50
        cam_single.Close()

        # Close 释放
        assert cam.Close()[0] is True
        assert cam.IsOpened()[0] is False
        print("verify_video_camera: OK")
    finally:
        # 先关闭相机释放文件句柄，再删除视频文件（避免 PermissionError 掩盖真实失败）
        if cam is not None:
            cam.Close()
        if cam_single is not None:
            cam_single.Close()
        for p in (video_a, video_b, video_z):
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(tmp_dir)


if __name__ == "__main__":
    main()
