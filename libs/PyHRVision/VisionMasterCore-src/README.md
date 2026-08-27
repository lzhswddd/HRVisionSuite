# VisionMasterCore 源码（含流程名编码兼容补丁）

pybind11 包装 VisionMasterCore / GlobalCameraCore 的 C++ 源码。

## 相对共享源的改动（2026-08-27）

**流程名编码兼容层**（`src/VisionMasterCore.cpp`）：pybind11 按 PYBIND11_STRINGS_UTF8
把 Python str 编码为 UTF-8 传入，而 SDK 内部流程名按系统 ANSI(GBK) 比较/索引，
UTF-8 中文流程名找不到。补丁在 `getProcedure` / `saveProcedure` / `deleteProcedure`
中先做 UTF-8→ANSI 转换再匹配，双候选兜底（转换名优先、原样其次），
中文流程名可直接传 str，旧调用方式（传 GBK 字节）仍兼容。

实现要点：
- 编码转换用 `MultiByteToWideChar(CP_UTF8)` + `WideCharToMultiByte(CP_ACP)`
- **转换结果必须去掉尾部 '\0'**（`-1` 查询长度含终止符，否则 std::string
  末尾带 null 导致 `"流程1\0" != "流程1"` 匹配失败）
- windows.h 须在标准库头之后包含（`_AMD64_` 由 windows.h 定义，winnt.h 依赖），
  且 `#define byte win_byte_override` 规避 C2872（SDK 的 byte 与 std::byte 冲突）

## 编译

```bat
build_pyd.bat
```
需要 VS2022 + D:/Python/pybind11 + D:/Anaconda3/envs/HRVision + VM SDK 开发库。
产物：`build/bin/VisionMasterCore.pyd`（拷贝到 HRVision 包目录即可）。

## 实测结论（2026-08-27，加密狗联调）

- `getProcedure('静态标定')` 直传 UTF-8 str 可用；GBK 字节仍兼容
- 同一进程只能创建一个 VisionMasterCore 实例
- 加载 .sol / .prc 均异步（loadProcedure 后轮询 getProcedure 至非 0）
