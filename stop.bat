@echo off
title 人员基本信息系统 - 停止
cd /d "%~dp0"

echo ============================================
echo        人员基本信息系统 - 一键停止
echo ============================================
echo.
echo 正在停止服务...
echo.

set "FOUND=0"

REM ===== 停止后端 (端口 8000) =====
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo [OK] 停止后端进程 (PID: %%a)
    taskkill /F /PID %%a >nul 2>nul
)

REM ===== 停止前端 (端口 5173) =====
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo [OK] 停止前端进程 (PID: %%a)
    taskkill /F /PID %%a >nul 2>nul
)

if "%FOUND%"=="0" echo [i] 未发现运行中的服务

echo.
echo ============================================
echo  [OK] 完成
echo ============================================
echo.
pause
