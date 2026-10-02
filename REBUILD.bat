@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo Building Frontend (Military Theme)
echo ============================================================
echo.
"D:\python\python.exe" "%~dp0REBUILD.py"
echo.
echo Press any key to close...
pause >nul
