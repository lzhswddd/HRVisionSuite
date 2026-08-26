@echo off
REM 打包流程子进程 exe（PyInstaller onedir）：
REM   产物: dist\flow_worker\flow_worker.exe（配 pipeline.json 的 python_exe）
REM 说明:
REM   - bundle\HRVision 为精简框架包（pyd + ProcessIsolate + 精简 __init__，无 .py 源码）
REM   - Crypto/numpy/psutil 用 --collect-all（pyd 的 import 静态不可见，需显式收）
REM   - pkg_resources/setuptools/cffi 排除（PyInstaller 自动 hook 会带进 plistlib/expat 链）
REM   - Anaconda 环境的 DLL 依赖（ffi/expat/bz2/lzma/ssl）需 --add-binary
cd /d %~dp0
python -m PyInstaller --noconfirm --onedir --name flow_worker ^
    --paths bundle ^
    --collect-all HRVision --collect-all Crypto --collect-all numpy --collect-all psutil ^
    --exclude-module pkg_resources --exclude-module setuptools --exclude-module cffi ^
    --add-binary "%CONDA_PREFIX%\Library\bin\expat.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\ffi.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\libbz2.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\libexpat.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\liblzma.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\libcrypto-3-x64.dll;." ^
    --add-binary "%CONDA_PREFIX%\Library\bin\libssl-3-x64.dll;." ^
    flow_worker.py
echo 完成: dist\flow_worker\flow_worker.exe
