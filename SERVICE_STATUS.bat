@echo off
REM ====== DEPLOY TOOL D :: 查看服务状态 ======
cd /d "%~dp0"
title Service Status

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
"%PY%" "%~dp0deploy_service.py" status
