#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "IVmExport.h"
using std::string;
namespace py = pybind11;
namespace VisionMasterSDK::VmSolution
{
    class IVmSolution;
};
struct ProcessInfoList__;

class VisionMasterCore
{
public:
    VisionMasterCore()= default;
    ~VisionMasterCore()= default;
    int loadSolution(string inSolutionPath);
    int64_t getProcedure(string inProcedureName);
    int64_t getSolution();

    int CallBackModuResFunc(IN OutputPlatformInfo *const pstOutputPlatformInfo, IN void *const pUser, bool bTime);
    int createSolution();
    int loadProcedure(string inProcedurePath);
    void getProcedureList();

    int saveAllProcedure(string folderPath = "");
    int saveProcedure(string inProcedureName, string folderPath = "");
    void DestroyObj();

    void deleteAllProcedure();
    void deleteProcedure(string name="");

    void closeSolution();
    bool isLoadFinish();

    // 设备通信接口：通信设备在 VM 软件"系统菜单→通信管理"中配置，deviceId 为设备编号（0 起），方案加载后即可收发
    int commSendBytes(int deviceId, py::bytes data);          // 发送原始字节
    py::bytes commRecvData(int deviceId, int maxLen = 1024);  // 接收数据（无数据/出错返回空 bytes）
    int commIsConnected(int deviceId);                        // 设备是否连接（1/0）
    int commSetInt(int deviceId, py::list values);            // 写整型数组
    int commSetFloat(int deviceId, py::list values);          // 写浮点数组
    int commSetString(int deviceId, string strValue);         // 写字符串

private:
    // 方案数据
    VisionMasterSDK::VmSolution::IVmSolution *pVmSol;
    // 方案流程列表
    ProcessInfoList__ *procedureList = nullptr;

    bool isLoad = false;

};

