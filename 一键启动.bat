@echo off
chcp 65001 >nul
title 信息管理系统 - 一键启动
cd /d "%~dp0"

echo ============================================
echo    单位内部信息管理系统 - 一键启动
echo ============================================
echo.

set "PYTHON=D:\python\python.exe"
set "NODE_DIR=C:\Users\12408\.workbuddy\binaries\node\versions\22.22.2"

echo [1/4] 检查环境...
"%PYTHON%" --version 2>nul
if errorlevel 1 (
    echo [X] Python 不可用
    pause
    exit /b 1
)
if not exist "%NODE_DIR%\node.exe" (
    echo [X] Node.js 不可用
    pause
    exit /b 1
)
echo [OK] Python 和 Node.js 已就绪
echo.

echo [2/4] 检查后端依赖...
"%PYTHON%" -c "import fastapi" 2>nul
if errorlevel 1 (
    echo 正在安装后端依赖，请稍候...
    cd backend
    "%PYTHON%" -m pip install -r requirements.txt -q
    cd /d "%~dp0"
)
echo [OK] 后端依赖已就绪
echo.

echo [3/4] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo 正在安装前端依赖，首次可能需要几分钟...
    cd frontend
    set "PATH=%PATH%;%NODE_DIR%"
    call npm install
    cd /d "%~dp0"
)
echo [OK] 前端依赖已就绪
echo.

echo [4/4] 启动服务...

REM --- 写一个临时的后端启动脚本 ---
echo @echo off > _start_backend.cmd
echo cd /d "%~dp0backend" >> _start_backend.cmd
echo %PYTHON% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload >> _start_backend.cmd

REM --- 写一个临时的前端启动脚本 ---
echo @echo off > _start_frontend.cmd
echo set "PATH=%PATH%;%NODE_DIR%" >> _start_frontend.cmd
echo cd /d "%~dp0frontend" >> _start_frontend.cmd
echo call npm run dev >> _start_frontend.cmd

start "后端服务" cmd /k "%~dp0_start_backend.cmd"
timeout /t 4 /nobreak >nul
start "前端服务" cmd /k "%~dp0_start_frontend.cmd"
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo  启动完成！2秒后自动打开浏览器...
echo ============================================
echo.
echo  访问地址:  http://127.0.0.1:5173
echo  账号:      admin
echo  密码:      admin123
echo.
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5173
echo 如浏览器未自动打开，请手动访问 http://127.0.0.1:5173
echo.
pause
