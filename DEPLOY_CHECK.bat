@echo off
REM ====== DEPLOY TOOL A :: 部署前环境自检（必跑，全部PASS才能上线） ======
cd /d "%~dp0"
title Pre-flight Deployment Check

set PY=D:\python\python.exe
if exist "%PY%" goto found
set PY=python
where %PY% >nul 2>nul
if %ERRORLEVEL% EQU 0 goto found
set PY=py
where %PY% >nul 2>nul
if %ERRORLEVEL% EQU 0 goto found
echo.
echo [ERROR] Python not found
pause
exit /b 1
:found
echo Using Python: %PY%
echo Running preflight checks, please wait (takes 20-60 seconds)...
echo.
"%PY%" "%~dp0deploy_preflight.py"
pause
