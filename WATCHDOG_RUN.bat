@echo off
REM ====== DEPLOY TOOL E :: 启动 Watchdog 进程守护（服务挂了自动重启） ======
cd /d "%~dp0"
title PersonInfo Watchdog Daemon

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
echo.
echo [Watchdog] Service monitoring started.
echo This window MUST STAY OPEN for watchdog to work.
echo Checks: every 15s  Auto-restart on 2 consecutive failures.
echo Log file: watchdog_log.txt
echo.
"%PY%" "%~dp0deploy_watchdog.py"
REM watchdog.py loops forever, so this .bat normally won't return;
REM but if it exits for whatever reason, wait 10s then restart itself.
echo Watchdog exited unexpectedly, restarting in 10s...
timeout /t 10 >nul
start "" "%~f0"
exit /b
