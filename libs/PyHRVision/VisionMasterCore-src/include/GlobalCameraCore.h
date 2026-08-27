#pragma once
#include <cstdint>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <string>
#include <utility>
#include <vector>

#include <pybind11/pybind11.h>
#include "OutputDispatcher.h"
#include "iMVS-6000PlatformSDKDefine.h"

namespace py = pybind11;

namespace VisionMasterSDK::GlobalCameraModule
{
    class GlobalCameraModuleTool;
    class GlobalCameraParams;
}

// 内部工具：MVS 像素格式编码 → (numpy dtype 字符串, 通道数)。
// 未知格式抛 std::invalid_argument（pybind 映射为 ValueError）。
// 供绑定层注册 _mvs_pixel_info 与帧转 numpy 使用。
std::pair<std::string, int> mvsPixelInfo(int pixelFormat);

class GlobalCameraCore : public VMC::OutputHandler
{
public:
    // 名称 = 方案中配置的全局相机名称；找不到抛 std::invalid_argument。构造时自动执行出图不触发流程(SetTriggerProcessEnable(false))
    // 生命周期：SDK 工具实例归已加载方案所有——重新 loadSolution 前必须先销毁所有 GlobalCameraCore 实例
    explicit GlobalCameraCore(const std::string &inName);
    ~GlobalCameraCore() override;
    GlobalCameraCore(const GlobalCameraCore &) = delete;
    GlobalCameraCore &operator=(const GlobalCameraCore &) = delete;

    // ---- 取图 ----
    py::object grabImage(int timeoutMs);        // 阻塞等下一帧；超时返回None。timeoutMs<=0 时立即返回（有未返回新帧则返回帧，否则None）。同一实例多线程并发调用会各自返回同一序列的帧（latest-wins，非队列）
    py::object getLatestImage();                // 立即返回最新帧；无帧返回 None
    void softwareTrigger();                     // 发一次软触发

    // ---- 参数控制 ----
    void setExposureTime(double us);
    double getExposureTime();
    void setGain(double db);
    double getGain();
    void setTriggerSource(int source);
    int getTriggerSource();
    void setTriggerDelay(double us);
    double getTriggerDelay();
    int getWidth();
    int getHeight();
    int getPixelFormat();
    void setPixelFormat(int fmt);

    // ---- 相机管理 ----
    py::list getCameraList();                   // [{name, sn}, ...]
    void setChosenCameraSN(const std::string &sn);
    std::string getChosenCameraSN();

    // ---- 连接与流程联动 ----
    bool isConnected();
    void setTriggerProcessEnable(bool enable);
    bool getTriggerProcessEnable();

private:
    // VMC::OutputHandler
    bool onOutput(OutputPlatformInfo *info) noexcept override;

    void parseModuleResult(IMVS_PF_MODULE_RESULT_INFO_LIST *pstList) noexcept;
    struct Frame;  // 前向声明：定义见下方"帧缓冲"（成员声明参数列表非 complete-class context，须先声明后使用）
    // 帧 → numpy；frameToNumpy 为成员以访问私有 Frame 类型
    static py::object frameToNumpy(const Frame &frame);

    std::string m_name;
    // m_tool/m_params 由 SDK 方案对象拥有，访问无需 m_mtx 同步（SDK 内部自行串行化）；m_mtx 只保护帧缓冲
    VisionMasterSDK::GlobalCameraModule::GlobalCameraModuleTool *m_tool;
    VisionMasterSDK::GlobalCameraModule::GlobalCameraParams *m_params;

    // 帧缓冲（回调线程写，用户线程读）
    // 注意：回调内 pData 仅在回调期间有效，parseModuleResult 必须在 onOutput 内拷贝图像字节，不得保留指针
    struct Frame
    {
        int width = 0;
        int height = 0;
        int pixelFormat = 0;
        uint64_t counter = 0;                  // nExecuteCount
        std::vector<uint8_t> data;
    };
    std::mutex m_mtx;
    std::condition_variable m_cv;
    std::shared_ptr<Frame> m_latest;           // 最新一帧
    uint64_t m_lastReturned = UINT64_MAX;      // 上次 grabImage 已返回的计数（仅限 m_mtx 下访问）；初始 UINT64_MAX 确保首帧（含计数0）不被跳过；谓词用 != 比较以兼容 SDK 计数回绕（32位 nExecuteCount）
};
