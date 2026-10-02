@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo Restart Server - Killing old processes and starting fresh
echo ============================================================
echo.
"D:\python\python.exe" "%~dp0RESTART_SERVER.py"
echo.
echo Press any key to close...
pause >nul
