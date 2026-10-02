@echo off
title 前端服务 - 人员信息系统 (端口5173)

REM 探测 node (与主脚本一致)
where npm >nul 2>nul
if not errorlevel 1 goto :fe_run
set "NODE_DIR="
if exist "%ProgramFiles%\nodejs\npm.cmd" set "NODE_DIR=%ProgramFiles%\nodejs"
if "%NODE_DIR%"=="" if exist "%ProgramFiles(x86)%\nodejs\npm.cmd" set "NODE_DIR=%ProgramFiles(x86)%\nodejs"
if "%NODE_DIR%"=="" if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "NODE_DIR=%LOCALAPPDATA%\Programs\nodejs"
if "%NODE_DIR%"=="" if exist "%USERPROFILE%\Z Code\bundled-node\win-x64\npm.cmd" set "NODE_DIR=%USERPROFILE%\Z Code\bundled-node\win-x64"
if not "%NODE_DIR%"=="" set "PATH=%PATH%;%NODE_DIR%"

:fe_run
cd /d "%~dp0frontend"
call npm run dev
echo.
echo 前端已停止。按任意键关闭。
pause
