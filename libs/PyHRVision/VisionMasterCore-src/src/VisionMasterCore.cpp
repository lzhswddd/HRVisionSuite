// windows.h 必须在标准库头之后包含（保证 std::byte 已声明时规避 C2872 歧义），
// 且 byte 宏改名：Windows SDK 的 typedef byte 与 std::byte 冲突的经典处理。
#include <string>
#include <mutex>
#include <vector>
#include <filesystem>

#define byte win_byte_override
#include <windows.h>   // 定义 _AMD64_（winnt.h 依赖）并声明 MultiByteToWideChar 等
#undef byte

#include "VisionMasterCore.h"
#include "OutputDispatcher.h"
#include "IVmSolution.h"
#include "IVmProcedure.h"
#include "VMException.h"
#include "IVmImageSource.h"
#include <IVmSaveImage.h>
#include "iMVS-6000PlatformSDKDefine.h"
#include "IVmCommManager.h"

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// 流程名编码兼容层（2026-08-27 联调实测）：
// pybind11 按 PYBIND11_STRINGS_UTF8 把 Python str 编码为 UTF-8 传入，
// 但 SDK 内部流程名按系统 ANSI(中文系统=GBK) 比较/索引，UTF-8 中文名会找不到。
// 因此：输入是合法 UTF-8 时先生成 [ANSI 转换名, 原名] 候选逐一匹配；
// 输入本身不是 UTF-8（调用方已传 GBK 字节）则直接用原样。
// ---------------------------------------------------------------------------
static std::string utf8_to_ansi(const std::string &utf8)
{
    if (utf8.empty()) return utf8;
    // 查询长度（含终止符），再按不含终止符的长度填充，避免 std::string 带尾 '\0'
    int wlen = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    if (wlen <= 0) return utf8;
    std::wstring wstr(wlen, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, wstr.data(), wlen);
    int alen = WideCharToMultiByte(CP_ACP, 0, wstr.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (alen <= 0) return utf8;
    std::string astr(alen - 1, '\0');   // 去掉终止符
    WideCharToMultiByte(CP_ACP, 0, wstr.c_str(), -1, astr.data(), alen, nullptr, nullptr);
    return astr;
}

static bool is_valid_utf8(const std::string &s)
{
    if (s.empty()) return true;
    return MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s.c_str(), -1, nullptr, 0) > 0;
}

static std::vector<std::string> name_candidates(const std::string &name)
{
    std::vector<std::string> out;
    if (is_valid_utf8(name))
    {
        std::string ansi = utf8_to_ansi(name);
        if (ansi != name)
        {
            out.push_back(ansi);   // ANSI 转换名优先（SDK 内部编码）
        }
    }
    out.push_back(name);           // 原样兜底（已是 ANSI 字节/纯 ASCII）
    return out;
}

// 在方案流程列表中按候选名匹配，返回 SDK 侧的名字（空串=未找到）
static std::string find_procedure_name(VisionMasterSDK::VmSolution::IVmSolution *pVmSol,
                                       ProcessInfoList__ *procedureList,
                                       const std::string &inProcedureName)
{
    if (procedureList == nullptr)
    {
        return "";
    }
    for (const auto &cand : name_candidates(inProcedureName))
    {
        for (int i = 0; i < (int)procedureList->nNum; i++)
        {
            if (cand == procedureList->astProcessInfo[i].strProcessName)
            {
                return procedureList->astProcessInfo[i].strProcessName;
            }
        }
    }
    return "";
}

using namespace VisionMasterSDK;
using namespace VisionMasterSDK::VmSolution;
using namespace VisionMasterSDK::ImageSourceModule;
using namespace VisionMasterSDK::VmProcedure;

int __stdcall CallBackModuRes(OUT OutputPlatformInfo *const pstOutputPlatformInfo, IN void *const pUser)
{
    VisionMasterCore *pVisionCore = (VisionMasterCore *)pUser;

    int nRet = IMVS_EC_UNKNOWN;

    nRet = pVisionCore->CallBackModuResFunc(pstOutputPlatformInfo, pUser, true);
    if (IMVS_EC_OK != nRet)
    {
        return nRet;
    }

    return IMVS_EC_OK;
}

/****************************************************************************
 * @fn           回调函数
 ****************************************************************************/
int VisionMasterCore::CallBackModuResFunc(IN OutputPlatformInfo *const pstOutputPlatformInfo, IN void *const pUser, bool bTime)
{
    if (IMVS_NULL == pstOutputPlatformInfo)
    {
        return 1;
    }
    if (IMVS_NULL == (pstOutputPlatformInfo->pData))
    {
        return 2;
    }
    // 多播给已注册的全局相机处理器（如 GlobalCameraCore）
    VMC::OutputDispatcher::dispatch(pstOutputPlatformInfo);
    VisionMasterCore *pVisionCore = (VisionMasterCore *)pUser;
    if (IMVS_ENUM_CTRLC_OUTPUT_PLATFORM_INFO_IMPORT_PROCESS_END == pstOutputPlatformInfo->nInfoType)
    {
        std::cout << "加载流程完成!!!!!" << std::endl;
        pVisionCore->isLoad = true;
        return 3;

    }
    return 0;
}

int VisionMasterCore::loadSolution(string inSolutionPath)
{
    fs::path absPath = fs::absolute(inSolutionPath);
    std::cout << "Absolute path: " << absPath.string() << std::endl;
    try
    {
        if (pVmSol != NULL)
        {
            DestroySolutionInstance(pVmSol);
            pVmSol = NULL;
        }
        // 加载方案，仅支持绝对路径，编码格式UTF-8
        pVmSol = LoadSolution(absPath.string().c_str(), "");
        if (NULL == pVmSol)
        {
            return IMVS_EC_NULL_PTR;
        }
        procedureList = pVmSol->GetAllProcedureList();
    }
    catch (CVmException vmex)
    {
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}

int64_t VisionMasterCore::getProcedure(string inProcedureName)
{
    try
    {
        if (inProcedureName != "" && pVmSol != NULL)
        {
            string matched = find_procedure_name(pVmSol, procedureList, inProcedureName);
            if (!matched.empty())
            {
                auto p_VmPro = static_cast<VisionMasterSDK::VmProcedure::IVmProcedure *>((*pVmSol)[matched.c_str()]);
                int64_t p_VmPro64 = reinterpret_cast<int64_t>(p_VmPro);
                return p_VmPro64;
            }
        }
    }
    catch (CVmException vmex)
    {
        std::cout << "setRenderProcedure error";
    }
    return NULL;
}

int64_t VisionMasterCore::getSolution()
{
    if (pVmSol != NULL)
    {
        return (int64_t)pVmSol;
    }
    return NULL;
}

int VisionMasterCore::createSolution()
{
    try
    {
        Py_BEGIN_ALLOW_THREADS
        pVmSol = CreateSolutionInstance();
        pVmSol->RegisterCallBack(CallBackModuRes, this);

        Py_END_ALLOW_THREADS
                std::cout
            << "createSolution success" << std::endl;
    }
    catch (CVmException vmex)
    {
        std::cout << "createSolution error" << vmex.GetErrorCode() << std::endl;
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}
std::mutex functionMutex;
int VisionMasterCore::loadProcedure(string inProcedurePath)
{
    isLoad = false;
    // std::lock_guard<std::mutex> lock(functionMutex);
    try
    {
        IVmProcedure *pPrcObjByPath = LoadProcedure(inProcedurePath.c_str());
        procedureList = pVmSol->GetAllProcedureList();
        if (NULL == pPrcObjByPath)
        {
            return IMVS_EC_NULL_PTR;
        }
    }
    catch (CVmException vmex)
    {
        std::cout << "loadProcedure error" << vmex.GetErrorCode() << std::endl;
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        std::cout << "loadProcedure unknown error" << std::endl;
        return IMVS_EC_UNKNOWN;
    }
    return 0;
}

bool VisionMasterCore::isLoadFinish()
{
    return isLoad;
}

void VisionMasterCore::getProcedureList()
{
    procedureList = pVmSol->GetAllProcedureList();
}

int VisionMasterCore::saveAllProcedure(string folderPath)
{
    try
    {
        if (pVmSol != NULL)
        {

            // 使用流程名称获取流程对象 = pVmSol->GetAllProcedureList();
            if (procedureList != nullptr)
            {
                for (int i = 0; i < (int)procedureList->nNum; i++)
                {
                    string procedureName = procedureList->astProcessInfo[i].strProcessName;
                    auto p_VmPro = static_cast<VisionMasterSDK::VmProcedure::IVmProcedure *>((*pVmSol)[procedureName.c_str()]);
                    if (folderPath != "")
                    {
                        string absolutePath = folderPath + "/" + procedureName + ".prc";
                        std::cout << "absolutePath: " << absolutePath << endl;
                        p_VmPro->SaveAsProcedure(absolutePath.c_str(), "");
                    }
                    else
                    {
                        fs::path absolute_path = fs::absolute(procedureName + ".prc");
                        string absolutePath = absolute_path.string();
                        std::cout << "absolutePath: " << absolutePath << endl;
                        p_VmPro->SaveAsProcedure(absolutePath.c_str(), "");
                    }
                }
            }
        }
    }
    catch (CVmException vmex)
    {
        // qDebug() << "saveAllProcedure error";
        std::cout << "saveAllProcedure error: " << vmex.GetErrorCode() << std::endl;
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        // qDebug() << "saveAllProcedure unknown error";
        std::cout << "saveAllProcedure unknown error" << std::endl;
        return IMVS_EC_UNKNOWN;
    }
    return 0;
}

int VisionMasterCore::saveProcedure(string inProcedureName, string folderPath)
{
    try
    {
        if (pVmSol != NULL)
        {
            string procedureName = find_procedure_name(pVmSol, procedureList, inProcedureName);
            if (!procedureName.empty())
            {
                std::cout << "saveProcedure " << procedureName << std::endl;
                auto p_VmPro = static_cast<VisionMasterSDK::VmProcedure::IVmProcedure *>((*pVmSol)[procedureName.c_str()]);
                if (folderPath != "")
                {

                    fs::path filePath = fs::absolute(folderPath + "/" + procedureName + ".prc");
                    string absolutePath = filePath.string();
                    std::cout << "absolutePath:" << absolutePath;
                    p_VmPro->SaveAsProcedure(absolutePath.c_str(), "");
                    //
                }
                else
                {
                    fs::path filePath = fs::absolute(procedureName + ".prc");
                    string absolutePath = filePath.string();
                    std::cout << "absolutePath:" << absolutePath;
                    p_VmPro->SaveAsProcedure(absolutePath.c_str(), "");
                }
            }
        }
    }
    catch (CVmException vmex)
    {
        std::cout << "saveProcedure error" << vmex.GetErrorCode() << std::endl;
    }
    return 0;
}

void VisionMasterCore::DestroyObj()
{
    try
    {
        DisposeResource();
    }
    catch (CVmException ex)
    {
        std::cout << "DisposeResource error: " << ex.GetErrorCode() << std::endl;
    }
    if (pVmSol != NULL)
    {
        DestroySolutionInstance(pVmSol);
        pVmSol = NULL;
    }
}

void VisionMasterCore::deleteAllProcedure()
{
    try
    {
        if (pVmSol != NULL)
        {

            // 使用流程名称获取流程对象 = pVmSol->GetAllProcedureList();
            if (procedureList != nullptr)
            {
                for (int i = 0; i < (int)procedureList->nNum; i++)
                {
                    auto p_VmPro = static_cast<VisionMasterSDK::VmProcedure::IVmProcedure *>((*pVmSol)[procedureList->astProcessInfo[i].strProcessName]);
                    DestroyProcedureInstance(p_VmPro);
                }
            }
        }
    }
    catch (CVmException vmex)
    {
        std::cout << "deleteAllProcedure error";
    }
}

void VisionMasterCore::deleteProcedure(string name)
{
    try
    {
        if (pVmSol != NULL)
        {
            string procedureName = find_procedure_name(pVmSol, procedureList, name);
            if (!procedureName.empty())
            {
                auto p_VmPro = static_cast<VisionMasterSDK::VmProcedure::IVmProcedure *>((*pVmSol)[procedureName.c_str()]);
                DestroyProcedureInstance(p_VmPro);
            }
        }
    }
    catch (CVmException vmex)
    {
        std::cout << "deleteProcedure error";
    }
}

void VisionMasterCore::closeSolution()
{
    DestroySolutionInstance(pVmSol);
}

/****************************************************************************
 * 设备通信接口：通信设备在 VM 软件"系统菜单→通信管理"中配置，
 * deviceId 为设备编号（0 起），通过通信管理全局模块按设备ID收发
 ****************************************************************************/
int VisionMasterCore::commSendBytes(int deviceId, py::bytes data)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return IMVS_EC_NULL_PTR;
        }
        std::string payload = data.cast<std::string>();
        commTool->SetBytes(deviceId, payload.data(), payload.size());
    }
    catch (CVmException vmex)
    {
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}

py::bytes VisionMasterCore::commRecvData(int deviceId, int maxLen)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return py::bytes();
        }
        std::vector<char> buffer(maxLen > 0 ? maxLen : 1024);
        size_t nLen = buffer.size();
        commTool->GetReadData(deviceId, buffer.data(), &nLen);
        return py::bytes(buffer.data(), nLen);
    }
    catch (CVmException vmex)
    {
        return py::bytes();
    }
    catch (...)
    {
        return py::bytes();
    }
}

int VisionMasterCore::commIsConnected(int deviceId)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return 0;
        }
        return commTool->bIsDeviceConnect(deviceId) ? 1 : 0;
    }
    catch (...)
    {
        return 0;
    }
}

int VisionMasterCore::commSetInt(int deviceId, py::list values)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return IMVS_EC_NULL_PTR;
        }
        std::vector<int> data;
        py::size_t n = py::len(values);
        for (py::size_t i = 0; i < n; i++)
        {
            data.push_back(values[i].cast<int>());
        }
        commTool->SetInt(deviceId, data.data(), (int)data.size());
    }
    catch (CVmException vmex)
    {
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}

int VisionMasterCore::commSetFloat(int deviceId, py::list values)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return IMVS_EC_NULL_PTR;
        }
        std::vector<float> data;
        py::size_t n = py::len(values);
        for (py::size_t i = 0; i < n; i++)
        {
            data.push_back(values[i].cast<float>());
        }
        commTool->SetFloat(deviceId, data.data(), (int)data.size());
    }
    catch (CVmException vmex)
    {
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}

int VisionMasterCore::commSetString(int deviceId, string strValue)
{
    try
    {
        CommManagerModule::CommManagerModuleTool *commTool = GetCommManagerToolInstance();
        if (commTool == NULL)
        {
            return IMVS_EC_NULL_PTR;
        }
        commTool->SetString(deviceId, strValue.c_str());
    }
    catch (CVmException vmex)
    {
        return vmex.GetErrorCode();
    }
    catch (...)
    {
        return IMVS_EC_UNKNOWN;
    }
    return IMVS_EC_OK;
}

