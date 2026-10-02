@echo off
chcp 65001 >nul
title 创建测试账号
cd /d "%~dp0"
echo ============================================
echo   创建测试账号（所有账号密码：test123）
echo ============================================
echo.
python 创建测试账号.py
if errorlevel 1 (
    echo.
    echo [错误] 执行失败，尝试使用完整路径...
    D:\python\python.exe 创建测试账号.py
)
pause
