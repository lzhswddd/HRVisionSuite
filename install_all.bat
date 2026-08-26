@echo off
REM ============================================================
REM HRVision Suite - one-click deploy
REM   installs: HRVision (framework) / HrFluentWidgets (UI) /
REM             HrMotionController (motion) / PLCInterface (PLC)
REM   copies examples (FlowDemo/UsbYolo/TriggerPlc/VmDemo) to %EXAMPLES_DIR%
REM usage: install_all.bat [python]
REM ============================================================
setlocal
set SUITE=%~dp0
if "%1"=="" (set PY=python) else (set PY=%1)
set EXAMPLES_DIR=D:\HRVisionExamples

echo [1/3] Installing libraries ...
%PY% -m pip install "%SUITE%libs\PyHRVision" "%SUITE%libs\HrFluentWidgets" ^
    "%SUITE%libs\HrMotionController" "%SUITE%libs\PLCInterface" "%SUITE%."
if errorlevel 1 goto :fail

echo [2/3] Deploying examples to %EXAMPLES_DIR% ...
if exist "%EXAMPLES_DIR%" rmdir /s /q "%EXAMPLES_DIR%"
robocopy "%SUITE%examples" "%EXAMPLES_DIR%" /E /XD .git __pycache__ logs /NFL /NDL /NJH /NJS /NP >nul

echo [3/3] Verifying imports ...
%PY% -c "import HRVision.HRFlowController, hrfluentwidgets, hrmotioncontroller, PLCInterface; print('ALL LIBRARIES OK')"
if errorlevel 1 goto :fail

echo.
echo DONE. Libraries installed; examples at %EXAMPLES_DIR%
echo   run: cd /d %EXAMPLES_DIR%\UsbYolo ^&^& %PY% HRStar.py
goto :eof

:fail
echo DEPLOY FAILED. Check output above.
exit /b 1
