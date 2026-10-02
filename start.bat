@echo off
REM =============================================================
REM  Person Info System - Launcher (ASCII-only wrapper, never garbled)
REM  Always keep this .bat free of Chinese characters to avoid CMD/GBK
REM  encoding issues. All user-facing messages live inside launcher.py
REM  which Python handles correctly as UTF-8 on all systems.
REM =============================================================
cd /d "%~dp0"
title Person Info System - Launcher

set PY=D:\python\python.exe
if exist "%PY%" goto found_py

set PY=python
where %PY% >nul 2>nul
if %ERRORLEVEL% EQU 0 goto found_py

set PY=py
where %PY% >nul 2>nul
if %ERRORLEVEL% EQU 0 goto found_py

echo.
echo [ERROR] Python not found! Expected D:\python\python.exe or python in PATH
echo.
pause
exit /b 1

:found_py
echo.
echo Using Python: %PY%
echo   Project dir: %cd%
echo   Starting launcher.py ...
echo.
"%PY%" "%~dp0launcher.py"
REM pause after launcher exits
echo.
pause
