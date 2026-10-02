@echo off
REM ====== DEPLOY TOOL F :: 放行 Windows 防火墙 8000 端口（内网其他机器访问必备） ======
REM 需要以管理员身份运行；本脚本会自动尝试提权
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 goto admin

cls
echo.
echo ================================================================
echo  This script needs ADMINISTRATOR privileges to configure firewall.
echo  Trying to elevate automatically ...
echo ================================================================
echo.
powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
exit /b

:admin
title Firewall Config - Allow Port 8000
color 0A
echo.
echo ================================================================
echo  Opening Windows Firewall - Allow incoming TCP 8000
echo ================================================================
echo.

REM 先删除旧规则（同名则重建）
netsh advfirewall firewall delete rule name="PersonInfo 8000 TCP In" >nul 2>&1
netsh advfirewall firewall delete rule name="PersonInfo 8000 TCP Out" >nul 2>&1

REM 入站规则（内网客户端访问服务器）
netsh advfirewall firewall add rule name="PersonInfo 8000 TCP In" ^
    dir=in action=allow protocol=TCP localport=8000 profile=any enable=yes

REM 出站规则（通常不需要，但加上保证双向都不被拦）
netsh advfirewall firewall add rule name="PersonInfo 8000 TCP Out" ^
    dir=out action=allow protocol=TCP remoteport=8000 profile=any enable=yes

echo.
echo ================================================================
echo  Done. Port 8000 is now open on all network profiles.
echo  Clients on the intranet can now access:
echo      http://THIS_SERVER_IP:8000
echo ================================================================
echo.
pause
