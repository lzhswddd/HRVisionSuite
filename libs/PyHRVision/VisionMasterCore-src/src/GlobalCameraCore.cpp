#include "GlobalCameraCore.h"
#include "IVmGlobalCamera.h"
#include "VmModuleParamBase.h"
#include "VMException.h"
#include <pybind11/numpy.h>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <string>
#include <utility>

std::pair<std::string, int> mvsPixelInfo(int pixelFormat)
{
    // MvCameraControl 像素格式编码（GenICam SFNC / GigE Vision 标准值）
    switch (pixelFormat)
    {
    case 17301505:                       // Mono8     0x01080001
    case 17301512:                       // BayerGR8  0x01080008
    case 17301513:                       // BayerRG8  0x01080009
    case 17301514:                       // BayerGB8  0x0108000A
    case 17301515:                       // BayerBG8  0x0108000B
        return {"uint8", 1};
    case 17825795:                       // Mono10    0x01100003
    case 17825797:                       // Mono12    0x01100005
    case 17825799:                       // Mono14    0x01100007
    case 17825807:                       // Mono16    0x0110000F
        return {"uint16", 1};
    case 35127316:                       // RGB8      0x02180014
        return {"uint8", 3};
    default:
        throw std::invalid_argument("unsupported MVS pixel format: " + std::to_string(pixelFormat));
    }
}

namespace py = pybind11;
using namespace VisionMasterSDK::GlobalCameraModule;

GlobalCameraCore::GlobalCameraCore(const std::string &inName)
    : m_name(inName), m_tool(nullptr), m_params(nullptr)
{
    m_tool = GetGlobalCameraToolInstance(inName.c_str());
    if (m_tool == nullptr)
    {
        throw std::invalid_argument("global camera not found: " + inName);
    }
    m_params = m_tool->GetParamObj();
    if (m_params == nullptr)
    {
        throw std::invalid_argument("global camera param object is null: " + inName);
    }
    // 默认出图不触发流程；可通过 setTriggerProcessEnable 改回
    m_tool->SetTriggerProcessEnable(false);
    VMC::OutputDispatcher::registerHandler(this);
}

GlobalCameraCore::~GlobalCameraCore()
{
    // 等待在途 dispatch 结束（最多一个回调周期），确保销毁后不再被调用
    VMC::OutputDispatcher::unregisterHandler(this);
}

bool GlobalCameraCore::onOutput(OutputPlatformInfo *info) noexcept
{
    try
    {
        if (info == nullptr || info->pData == nullptr)
        {
            return false;
        }
        if (info->nInfoType != IMVS_ENUM_CTRLC_OUTPUT_PLATFORM_INFO_MODULE_RESULT)
        {
            return false;
        }
        auto *pstList = static_cast<IMVS_PF_MODULE_RESULT_INFO_LIST *>(info->pData);
        if (pstList->pstrModuleName == nullptr || m_name != pstList->pstrModuleName)
        {
            return false;    // 不是本实例的相机
        }
        parseModuleResult(pstList);
        return true;
    }
    catch (...)
    {
        return false;    // 回调内绝不抛异常
    }
}

void GlobalCameraCore::parseModuleResult(IMVS_PF_MODULE_RESULT_INFO_LIST *pstList) noexcept
{
    Frame frame;
    frame.counter = pstList->nExecuteCount;
    const char *imageData = nullptr;
    unsigned int imageLen = 0;
    bool hasImage = false, hasW = false, hasH = false, hasFmt = false;

    // nParamType: 4=图像值 3=字符串值 1=整型值（iMVS-6000PlatformSDKDefine.h 模块结果类型注释）
    if (pstList->pModuResInfo == nullptr)
    {
        return;    // 防御：结果数组缺失时丢弃，避免 SDK 线程崩溃
    }
    for (int i = 0; i < pstList->nResultNum; i++)
    {
        const IMVS_PF_MODULE_RESULT_INFO &r = pstList->pModuResInfo[i];
        if (r.nParamType == 4 && r.pstImageValue != nullptr)
        {
            imageData = r.pstImageValue->pData;
            imageLen = r.pstImageValue->nLen;
            hasImage = true;
        }
        else if (r.nParamType == 1 && r.pIntValue != nullptr && r.nValueNum >= 1)
        {
            std::string name(r.strParamName);
            if (name == "Width")      { frame.width = r.pIntValue[0]; hasW = true; }
            else if (name == "Height"){ frame.height = r.pIntValue[0]; hasH = true; }
            else if (name == "PixelFormat") { frame.pixelFormat = r.pIntValue[0]; hasFmt = true; }
        }
    }
    if (!hasImage || !hasW || !hasH || !hasFmt || imageData == nullptr)
    {
        return;    // 结果不完整，丢弃
    }
    // 回调内 pData 仅在回调期间有效：必须拷贝图像字节，不得保留指针
    frame.data.assign(imageData, imageData + imageLen);

    std::lock_guard<std::mutex> lock(m_mtx);
    m_latest = std::make_shared<Frame>(std::move(frame));
    m_cv.notify_all();
}

py::object GlobalCameraCore::frameToNumpy(const Frame &frame)
{
    auto info = mvsPixelInfo(frame.pixelFormat);    // 抛 invalid_argument
    const auto &[dtype, channels] = info;
    if (frame.data.empty() || frame.width <= 0 || frame.height <= 0)
    {
        throw std::runtime_error("invalid frame size");
    }
    py::array arr;
    if (channels == 1)
    {
        arr = py::array(py::dtype(dtype), {frame.height, frame.width});
    }
    else
    {
        arr = py::array(py::dtype(dtype), {frame.height, frame.width, channels});
    }
    size_t need = (size_t)frame.width * frame.height * channels * arr.itemsize();
    if (need != frame.data.size())
    {
        throw std::runtime_error("frame data size mismatch: need " + std::to_string(need)
                                 + " got " + std::to_string(frame.data.size()));
    }
    std::memcpy(arr.mutable_data(), frame.data.data(), frame.data.size());
    return arr;
}

py::object GlobalCameraCore::grabImage(int timeoutMs)
{
    Frame copy;
    bool got = false;
    {
        // 等帧期间释放 GIL：多相机在多个 Python 线程中并发等待时互不阻塞
        py::gil_scoped_release release;
        std::unique_lock<std::mutex> lock(m_mtx);
        const uint64_t target = m_lastReturned;
        // 用 != 比较（非 >）：nExecuteCount 为 32 位，回绕后仍正确
        got = m_cv.wait_for(lock, std::chrono::milliseconds(timeoutMs), [&] {
            return m_latest != nullptr && m_latest->counter != target;
        });
        if (got)
        {
            m_lastReturned = m_latest->counter;
            copy = *m_latest;
        }
    }
    if (!got)
    {
        return py::none();    // 超时
    }
    return frameToNumpy(copy);
}

py::object GlobalCameraCore::getLatestImage()
{
    Frame copy;
    {
        std::lock_guard<std::mutex> lock(m_mtx);
        if (m_latest == nullptr)
        {
            return py::none();
        }
        copy = *m_latest;
    }
    return frameToNumpy(copy);
}

void GlobalCameraCore::softwareTrigger()
{
    try
    {
        InputStringData data{};
        // 触发字符取值：先试空串；若真机不触发则改填方案配置的触发字符（设计文档验证项3）
        data.strValue[0] = '\0';
        m_params->SetInputString("TriggerString", &data, 1);
    }
    catch (CVmException &e)
    {
        throw std::runtime_error("softwareTrigger failed, err=" + std::to_string(e.GetErrorCode()));
    }
}

void GlobalCameraCore::setExposureTime(double us)
{
    try { m_params->SetExposureTime(us); }
    catch (CVmException &e)
    { throw std::runtime_error("setExposureTime failed, err=" + std::to_string(e.GetErrorCode())); }
}

double GlobalCameraCore::getExposureTime()
{
    try { return m_params->GetExposureTime(); }
    catch (CVmException &e)
    { throw std::runtime_error("getExposureTime failed, err=" + std::to_string(e.GetErrorCode())); }
}

void GlobalCameraCore::setGain(double db)
{
    try { m_params->SetGain(db); }
    catch (CVmException &e)
    { throw std::runtime_error("setGain failed, err=" + std::to_string(e.GetErrorCode())); }
}

double GlobalCameraCore::getGain()
{
    try { return m_params->GetGain(); }
    catch (CVmException &e)
    { throw std::runtime_error("getGain failed, err=" + std::to_string(e.GetErrorCode())); }
}

void GlobalCameraCore::setTriggerSource(int source)
{
    try { m_params->SetTriggerSource(source); }
    catch (CVmException &e)
    { throw std::runtime_error("setTriggerSource failed, err=" + std::to_string(e.GetErrorCode())); }
}

int GlobalCameraCore::getTriggerSource()
{
    try { return m_params->GetTriggerSource(); }
    catch (CVmException &e)
    { throw std::runtime_error("getTriggerSource failed, err=" + std::to_string(e.GetErrorCode())); }
}

void GlobalCameraCore::setTriggerDelay(double us)
{
    try { m_params->SetTriggerDelay(us); }
    catch (CVmException &e)
    { throw std::runtime_error("setTriggerDelay failed, err=" + std::to_string(e.GetErrorCode())); }
}

double GlobalCameraCore::getTriggerDelay()
{
    try { return m_params->GetTriggerDelay(); }
    catch (CVmException &e)
    { throw std::runtime_error("getTriggerDelay failed, err=" + std::to_string(e.GetErrorCode())); }
}

int GlobalCameraCore::getWidth()
{
    try { return m_params->GetWidth(); }
    catch (CVmException &e)
    { throw std::runtime_error("getWidth failed, err=" + std::to_string(e.GetErrorCode())); }
}

int GlobalCameraCore::getHeight()
{
    try { return m_params->GetHeight(); }
    catch (CVmException &e)
    { throw std::runtime_error("getHeight failed, err=" + std::to_string(e.GetErrorCode())); }
}

int GlobalCameraCore::getPixelFormat()
{
    try { return m_params->GetPixelFormat(); }
    catch (CVmException &e)
    { throw std::runtime_error("getPixelFormat failed, err=" + std::to_string(e.GetErrorCode())); }
}

void GlobalCameraCore::setPixelFormat(int fmt)
{
    try { m_params->SetPixelFormat(fmt); }
    catch (CVmException &e)
    { throw std::runtime_error("setPixelFormat failed, err=" + std::to_string(e.GetErrorCode())); }
}

py::list GlobalCameraCore::getCameraList()
{
    py::list result;
    try
    {
        CameraInfoList *pList = m_params->GetCameraInfoList();
        if (pList == nullptr)
        {
            return result;
        }
        for (unsigned int i = 0; i < pList->nNum; i++)
        {
            py::dict item;
            item["name"] = std::string(pList->astCameraInfo[i].strCameraName);
            item["sn"] = std::string(pList->astCameraInfo[i].strCameraSN);
            result.append(item);
        }
    }
    catch (CVmException &e)
    {
        throw std::runtime_error("getCameraList failed, err=" + std::to_string(e.GetErrorCode()));
    }
    return result;
}

void GlobalCameraCore::setChosenCameraSN(const std::string &sn)
{
    try { m_params->SetChosenCameraSN(sn.c_str()); }
    catch (CVmException &e)
    { throw std::runtime_error("setChosenCameraSN failed, err=" + std::to_string(e.GetErrorCode())); }
}

std::string GlobalCameraCore::getChosenCameraSN()
{
    try
    {
        const char *sn = m_params->GetChosenCameraSN();
        return sn == nullptr ? std::string() : std::string(sn);
    }
    catch (CVmException &e)
    { throw std::runtime_error("getChosenCameraSN failed, err=" + std::to_string(e.GetErrorCode())); }
}

bool GlobalCameraCore::isConnected()
{
    try { return m_tool->bIsCameraConnect(); }
    catch (...) { return false; }
}

void GlobalCameraCore::setTriggerProcessEnable(bool enable)
{
    try { m_tool->SetTriggerProcessEnable(enable); }
    catch (CVmException &e)
    { throw std::runtime_error("setTriggerProcessEnable failed, err=" + std::to_string(e.GetErrorCode())); }
}

bool GlobalCameraCore::getTriggerProcessEnable()
{
    try { return m_tool->GetTriggerProcessEnable(); }
    catch (CVmException &e)
    { throw std::runtime_error("getTriggerProcessEnable failed, err=" + std::to_string(e.GetErrorCode())); }
}
