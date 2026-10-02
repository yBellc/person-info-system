@echo off
cd /d "%~dp0"
"D:\python\python.exe" "%~dp0get_build_error.py"
echo.
echo Press any key to close...
pause >nul
