#ifndef HRVISION_HRFRAME_H
#define HRVISION_HRFRAME_H
/* ============================================================================
 * HRFrame v1 —— 语言无关帧协议（C/C++ 侧参考实现，header-only）
 *
 * 与 py 端 HRFlowController 内嵌协议 / utils/hrframe.py 同源。帧数据可经
 * _ShmQueue 共享内存对象槽、命名管道、文件或网络传输——任何语言只需按
 * 本布局解析 48B 头 + 拷贝像素区即可，不依赖 pickle/numpy。
 *
 * 字节布局（全部小端，固定宽度；共 48B 头）：
 *   [0:4]  magic "HFRM"     [4:8]  version=1
 *   [8:12] format           [12:16] width      [16:20] height
 *   [20:24] row_stride（0=紧凑 width*bpp/8）
 *   [24:32] frame_id(uint64)[32:40] ts_ns(uint64)
 *   [40:44] bpp（每像素位深：Mono8=8 BGR8=24 BGRA8=32，跨语言免查表）
 *   [44:48] reserved=0
 *   [48:]   像素数据区，长度 = row_stride*height（紧凑时 width*height*bpp/8）
 *
 * 格式枚举（与 Python HFRAME_FMT_* 一一对应）：
 *   0 Mono8(u8)  1 Mono16(u16)  2-5 BayerRG8/GB8/GR8/BG8(u8 单通道原始)
 *   6 BGR8(u8 3ch,OpenCV 惯例)  7 RGB8  8 BGRA8(u8 4ch)  9 GrayF32(f32)
 *   10 RGB-planar8(RRRGGGBBB)  11 BGR-planar8(BBBGGGRRR)
 *
 * 注意：共享内存对象槽中帧块首字节在 12B 槽头之后（非 8B 对齐），
 *       严禁 reinterpret_cast 读头——一律 load_header()（memcpy）。
 * ========================================================================== */
#include <cstdint>
#include <cstddef>
#include <cstring>

namespace hrframe {

static const uint32_t kMagic = 0x4d524648u;   /* "HFRM" 小端 */
static const uint32_t kVersion = 1u;
static const size_t   kHeaderSize = 48;

enum Format : uint32_t {
    kMono8       = 0,
    kMono16      = 1,
    kBayerRG8    = 2,
    kBayerGB8    = 3,
    kBayerGR8    = 4,
    kBayerBG8    = 5,
    kBGR8        = 6,
    kRGB8        = 7,
    kBGRA8       = 8,
    kGrayF32     = 9,
    kRGBPlanar8  = 10,
    kBGRPlanar8  = 11,
};

/* 头字段精确对齐（48B，无 padding：24B 后紧接 u64，起始偏移已 8 对齐） */
struct Header {
    uint32_t magic;        /* kMagic */
    uint32_t version;      /* 1 */
    uint32_t format;       /* Format */
    uint32_t width;
    uint32_t height;
    uint32_t row_stride;   /* 0 = 紧凑（width*bpp/8） */
    uint64_t frame_id;
    uint64_t ts_ns;
    uint32_t bpp;          /* 每像素位深（跨语言免查表）：width*bpp/8 = 紧凑行字节 */
    uint32_t reserved;     /* 0 */
};
static_assert(sizeof(Header) == 48, "hrframe header must be 48 bytes");

/* 从任意字节指针加载头（对象槽/管道/文件；数据可能非对齐，memcpy 是唯一合法读法） */
inline void load_header(const uint8_t *p, Header &out) {
    std::memcpy(&out, p, kHeaderSize);
    /* 扩展：大端平台需按字节序交换字段（x86/ARM64 LE 无需处理） */
}

inline size_t frame_size(const Header &h);   /* 前置声明（见下） */

/* 校验帧块（p 指向含头的完整帧块，n 为块长度）；成功时输出头 */
inline bool validate(const uint8_t *p, size_t n, Header *h_out = nullptr) {
    if (p == nullptr || n < kHeaderSize) return false;
    Header h;
    load_header(p, h);
    if (h.magic != kMagic || h.version != kVersion) return false;
    if (h.format > kBGRPlanar8) return false;
    if (frame_size(h) > n) return false;   /* frame_size 定义见下（先声明使用） */
    if (h_out) *h_out = h;
    return true;
}

/* 每行字节数（紧凑时按 bpp 推导） */
inline size_t row_bytes(const Header &h) {
    return h.row_stride ? size_t(h.row_stride) : (size_t(h.width) * h.bpp) / 8;
}

/* 帧块总长 = 48 + row_bytes*height */
inline size_t frame_size(const Header &h) {
    return kHeaderSize + row_bytes(h) * size_t(h.height);
}

/* 像素数据区指针 */
inline const uint8_t *data_ptr(const Header &h, const uint8_t *raw) {
    (void)h;
    return raw + kHeaderSize;
}

/* 格式名（日志/调试用） */
inline const char *format_name(uint32_t fmt) {
    switch (fmt) {
        case kMono8:       return "Mono8";
        case kMono16:      return "Mono16";
        case kBayerRG8:    return "BayerRG8";
        case kBayerGB8:    return "BayerGB8";
        case kBayerGR8:    return "BayerGR8";
        case kBayerBG8:    return "BayerBG8";
        case kBGR8:        return "BGR8";
        case kRGB8:        return "RGB8";
        case kBGRA8:       return "BGRA8";
        case kGrayF32:     return "GrayF32";
        case kRGBPlanar8:  return "RGB-planar8";
        case kBGRPlanar8:  return "BGR-planar8";
        default:           return "<unknown>";
    }
}

/* ---- 可选 OpenCV 互转（include <opencv2/core/mat.hpp> + 本宏后可用）--- */
#ifdef HFRAME_HAVE_OPENCV
#include <opencv2/core/mat.hpp>
#include <vector>

/* HRFrame → cv::Mat（引用帧块内存，不拷贝；帧块生命周期需覆盖 Mat 使用期）。
   Bayer/planar 不支持（需颜色转换，返回空 Mat）。 */
inline cv::Mat to_mat(const Header &h, const uint8_t *raw) {
    int type = -1;
    switch (h.format) {
        case kMono8:  type = CV_8UC1;  break;
        case kMono16: type = CV_16UC1; break;
        case kBGR8:   type = CV_8UC3;  break;
        case kRGB8:   type = CV_8UC3;  break;   /* 通道顺序以数据为准 */
        case kBGRA8:  type = CV_8UC4;  break;
        case kGrayF32:type = CV_32FC1; break;
        default: return cv::Mat();
    }
    return cv::Mat(int(h.height), int(h.width), type,
                   const_cast<uint8_t *>(data_ptr(h, raw)), row_bytes(h));
}

/* cv::Mat（连续）→ HRFrame 帧块（含 48B 头；u8 1/3/4ch、u16 1ch、f32 1ch）。
   其余类型返回空。 */
inline std::vector<uint8_t> from_mat(const cv::Mat &m, uint64_t frame_id = 0,
                                     uint64_t ts_ns = 0) {
    uint32_t fmt = 0xFFFFFFFFu;
    switch (m.type()) {
        case CV_8UC1:  fmt = kMono8;   break;
        case CV_8UC3:  fmt = kBGR8;    break;
        case CV_8UC4:  fmt = kBGRA8;   break;
        case CV_16UC1: fmt = kMono16;  break;
        case CV_32FC1: fmt = kGrayF32; break;
        default: return {};
    }
    if (!m.isContinuous()) return {};
    Header h;
    h.magic = kMagic; h.version = kVersion; h.format = fmt;
    h.width = uint32_t(m.cols); h.height = uint32_t(m.rows);
    h.row_stride = 0; h.frame_id = frame_id; h.ts_ns = ts_ns;
    h.bpp = uint32_t(m.elemSize() * 8);   /* 每像素位深 */
    h.reserved = 0;
    std::vector<uint8_t> blob(kHeaderSize + m.total() * m.elemSize());
    std::memcpy(blob.data(), &h, kHeaderSize);
    std::memcpy(blob.data() + kHeaderSize, m.data, blob.size() - kHeaderSize);
    return blob;
}
#endif /* HFRAME_HAVE_OPENCV */

} /* namespace hrframe */
#endif /* HRVISION_HRFRAME_H */
