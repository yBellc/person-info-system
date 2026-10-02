@echo off
REM ================================================
REM  Auto Build Frontend (auto-install Node.js + Vite)
REM  Just double-click, everything is automatic
REM ================================================
cd /d "%~dp0"
title Personnel Info System - Frontend Auto Builder

echo ================================================
echo  Personnel Info System - Frontend Auto Builder
echo  (Auto-install Node.js + Vite build)
echo ================================================
echo.

"D:\python\python.exe" "%~dp0AUTO_BUILD.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed. Check messages above.
    echo Press any key to close...
    pause >nul
)
