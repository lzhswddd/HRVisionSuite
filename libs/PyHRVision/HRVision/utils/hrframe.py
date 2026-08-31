# -*- coding: utf-8 -*-
"""HRFrame v1 —— 语言无关帧协议（公开 API 薄封装）。

协议单源在 HRFlowController.pyd/.so/.py 内（帧通道 DataBus 与之配套），
本模块仅 re-export 并附使用文档，**不加业务逻辑**（改动协议须改源头 +
include/hrframe.h 同步）。

字节布局（小端，48B 头）：
    [0:4]  magic "HFRM"    [4:8]  version=1
    [8:12] format          [12:16] width    [16:20] height
    [20:24] row_stride（0=紧凑 width*bpp//8）
    [24:32] frame_id(u64)  [32:40] ts_ns(u64)
    [40:44] bpp（冗余）    [44:48] reserved=0
    [48:]   像素数据区（row_stride*height；紧凑时 width*height*bpp//8）

跨语言用法：
    Python ：从 any 帧源构造 → Databus.put_frame_raw / 直接进共享内存对象槽；
             解析 hrframe_parse / hrframe_to_array（零拷贝只读视图）。
    C/C++  ：HRVision/include/hrframe.h（header-only：hrframe_t 结构 +
             hframe_* 辅助，cv::Mat 一行构造）。
    C#/Java：按本协议表小端解析 48B 头 + 拷贝数据区。

格式枚举（ndarray 自动推断：u8 1/3/4ch→Mono8/BGR8/BGRA8，u16 1ch→Mono16，
f32 1ch→GrayF32；Bayer/planar 须显式 fmt）。
"""
from HRVision.HRFlowController import (
    HFRAME_HEADER,
    HFRAME_MAGIC,
    HFRAME_VERSION,
    HFRAME_FMT_MONO8,
    HFRAME_FMT_MONO16,
    HFRAME_FMT_BAYER_RG8,
    HFRAME_FMT_BAYER_GB8,
    HFRAME_FMT_BAYER_GR8,
    HFRAME_FMT_BAYER_BG8,
    HFRAME_FMT_BGR8,
    HFRAME_FMT_RGB8,
    HFRAME_FMT_BGRA8,
    HFRAME_FMT_GRAYF32,
    HFRAME_FMT_RGB_PLANAR8,
    HFRAME_FMT_BGR_PLANAR8,
    hrframe_formats,
    hrframe_make_header,
    hrframe_from_array,
    hrframe_parse,
    hrframe_to_array,
    hrframe_load,
)

__all__ = [
    "HFRAME_HEADER", "HFRAME_MAGIC", "HFRAME_VERSION",
    "HFRAME_FMT_MONO8", "HFRAME_FMT_MONO16",
    "HFRAME_FMT_BAYER_RG8", "HFRAME_FMT_BAYER_GB8",
    "HFRAME_FMT_BAYER_GR8", "HFRAME_FMT_BAYER_BG8",
    "HFRAME_FMT_BGR8", "HFRAME_FMT_RGB8", "HFRAME_FMT_BGRA8",
    "HFRAME_FMT_GRAYF32", "HFRAME_FMT_RGB_PLANAR8", "HFRAME_FMT_BGR_PLANAR8",
    "hrframe_formats", "hrframe_make_header", "hrframe_from_array",
    "hrframe_parse", "hrframe_to_array", "hrframe_load",
]
