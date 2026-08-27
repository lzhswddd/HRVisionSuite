@echo off
rem Build VisionMasterCore.pyd with VS2022 (UTF-8/ANSI name compat patch)
cd /d %~dp0
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
where cl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] vcvars64 failed, cl.exe not found
    exit /b 1
)
set NINJA=C:\Qt\Tools\Ninja\ninja.exe
if not exist build mkdir build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" -G Ninja -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM=%NINJA% .
if errorlevel 1 exit /b 1
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build build
if errorlevel 1 exit /b 1
echo BUILD OK: build\VisionMasterCore.pyd
