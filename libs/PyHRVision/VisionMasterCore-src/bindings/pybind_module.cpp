#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include "VisionMasterCore.h"
#include "GlobalCameraCore.h"  // mvsPixelInfo 声明（内部工具：像素格式映射）
namespace py = pybind11;

PYBIND11_MODULE(VisionMasterCore, m)
{
    m.doc() = "VisionMasterCore模块";
    m.attr("__version__") = "0.1.0";
    m.attr("__author__") = "HRVision";
    m.attr("__description__") = "VisionMasterCore模块";
    m.attr("__copyright__") = "Copyright (c) 2023 HRVision";
    m.attr("__license__") = "MIT License";

    // 内部工具：MVS 像素格式 → (numpy dtype, 通道数)；测试与帧转换共用
    m.def("_mvs_pixel_info", &mvsPixelInfo, "MVS像素格式转(dtype,通道数)", py::arg("pixelFormat"));

    py::class_<VisionMasterCore>(m, "VisionMasterCore")
        .def(py::init<>())
        .def("loadSolution", &VisionMasterCore::loadSolution, "加载方案文件", py::arg("inSolutionPath"))
        .def("getProcedure", &VisionMasterCore::getProcedure, "获取流程对象", py::arg("inProcedureName"))
        .def("getSolution", &VisionMasterCore::getSolution, "获取方案对象")
        .def("createSolution", &VisionMasterCore::createSolution, "创建方案对象")
        .def("loadProcedure", &VisionMasterCore::loadProcedure, "加载流程文件", py::arg("inProcedurePath"))
        .def("getProcedureList", &VisionMasterCore::getProcedureList, "获取流程列表")
        .def("saveAllProcedure", &VisionMasterCore::saveAllProcedure, "保存所有流程", py::arg("folderPath") = "")
        .def("saveProcedure", &VisionMasterCore::saveProcedure, "保存指定流程", py::arg("inProcedureName"), py::arg("folderPath") = "")
        .def("DestroyObj", &VisionMasterCore::DestroyObj, "销毁对象")
        .def("deleteAllProcedure", &VisionMasterCore::deleteAllProcedure, "删除所有流程")
        .def("deleteProcedure", &VisionMasterCore::deleteProcedure, "删除指定流程", py::arg("name") = "")
        .def("closeSolution", &VisionMasterCore::closeSolution, "关闭方案")
        .def("isLoadFinish", &VisionMasterCore::isLoadFinish, "判断是否加载完成")
        .def("commSendBytes", &VisionMasterCore::commSendBytes, "发送数据到通信设备(设备ID, bytes)", py::arg("deviceId"), py::arg("data"))
        .def("commRecvData", &VisionMasterCore::commRecvData, "从通信设备接收数据(设备ID, 最大长度)", py::arg("deviceId"), py::arg("maxLen") = 1024)
        .def("commIsConnected", &VisionMasterCore::commIsConnected, "通信设备是否连接(设备ID)", py::arg("deviceId"))
        .def("commSetInt", &VisionMasterCore::commSetInt, "向通信设备写整型数组(设备ID, 列表)", py::arg("deviceId"), py::arg("values"))
        .def("commSetFloat", &VisionMasterCore::commSetFloat, "向通信设备写浮点数组(设备ID, 列表)", py::arg("deviceId"), py::arg("values"))
        .def("commSetString", &VisionMasterCore::commSetString, "向通信设备写字符串(设备ID, 字符串)", py::arg("deviceId"), py::arg("strValue"))
        .def("__repr__", [](const VisionMasterCore &c) {
            return "<VisionMasterCore.VisionMasterCore>";
        })
        .def("__str__", [](const VisionMasterCore &c) {
            return "<VisionMasterCore.VisionMasterCore>";
        });

    py::class_<GlobalCameraCore>(m, "GlobalCameraCore",
                                 "全局相机控制类：不经流程直接从相机取图。名称 = 方案中配置的全局相机名；构造前须已 loadSolution，重新 loadSolution 前必须销毁（del/离开作用域）所有 GlobalCameraCore 实例，否则 SDK 工具指针悬空。构造时自动执行出图不触发流程(SetTriggerProcessEnable(false))，可用 setTriggerProcessEnable 改回")
        .def(py::init<const std::string &>(), "创建全局相机实例", py::arg("name"))
        .def("grabImage", &GlobalCameraCore::grabImage, "阻塞等待下一帧图像，超时返回None；timeout_ms<=0 立即返回", py::arg("timeout_ms") = 5000)
        .def("getLatestImage", &GlobalCameraCore::getLatestImage, "立即返回最新帧，无帧返回None")
        .def("softwareTrigger", &GlobalCameraCore::softwareTrigger, "发一次软触发")
        .def("setExposureTime", &GlobalCameraCore::setExposureTime, "设置曝光时间(微秒)", py::arg("us"))
        .def("getExposureTime", &GlobalCameraCore::getExposureTime, "获取曝光时间(微秒)")
        .def("setGain", &GlobalCameraCore::setGain, "设置增益(dB)", py::arg("db"))
        .def("getGain", &GlobalCameraCore::getGain, "获取增益(dB)")
        .def("setTriggerSource", &GlobalCameraCore::setTriggerSource, "设置触发源(0=硬触发 1=软触发)", py::arg("source"))
        .def("getTriggerSource", &GlobalCameraCore::getTriggerSource, "获取触发源")
        .def("setTriggerDelay", &GlobalCameraCore::setTriggerDelay, "设置触发延迟(微秒)", py::arg("us"))
        .def("getTriggerDelay", &GlobalCameraCore::getTriggerDelay, "获取触发延迟(微秒)")
        .def("getWidth", &GlobalCameraCore::getWidth, "获取图像宽度")
        .def("getHeight", &GlobalCameraCore::getHeight, "获取图像高度")
        .def("getPixelFormat", &GlobalCameraCore::getPixelFormat, "获取像素格式(MVS编码)")
        .def("setPixelFormat", &GlobalCameraCore::setPixelFormat, "设置像素格式(MVS编码)", py::arg("fmt"))
        .def("getCameraList", &GlobalCameraCore::getCameraList, "枚举可用相机列表[{name,sn}]")
        .def("setChosenCameraSN", &GlobalCameraCore::setChosenCameraSN, "切换全局相机绑定的相机SN", py::arg("sn"))
        .def("getChosenCameraSN", &GlobalCameraCore::getChosenCameraSN, "获取当前绑定相机SN")
        .def("isConnected", &GlobalCameraCore::isConnected, "相机是否连接")
        .def("setTriggerProcessEnable", &GlobalCameraCore::setTriggerProcessEnable, "出图是否触发流程运行", py::arg("enable"))
        .def("getTriggerProcessEnable", &GlobalCameraCore::getTriggerProcessEnable, "出图是否触发流程运行")
        .def("__repr__", [](const GlobalCameraCore &c) { return "<VisionMasterCore.GlobalCameraCore>"; });
}
