@echo off
chcp 65001 >nul
title 单位内部信息管理系统
cd /d "%~dp0backend"

echo ============================================
echo   单位内部信息管理系统 - 启动中...
echo ============================================
echo.
echo 本机访问: http://127.0.0.1:8000
echo 内网访问: http://本机IP:8000
echo.
echo 测试账号:
echo   admin          admin123   (超级管理员)
echo   leader         test123    (超级管理员/张局长)
echo   admin_01       test123    (单位管理员/李主任)
echo   bgs_leader     test123    (部门领导/王科长)
echo   hr_01          test123    (人事/赵人事)
echo   cw_01          test123    (财务/孙会计)
echo   office_01      test123    (普通员工/周文员)
echo.
echo 按 Ctrl+C 可停止服务
echo.

REM 2秒后自动打开浏览器
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

D:\python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo 服务已停止
pause