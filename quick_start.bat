@echo off
chcp 65001 >nul
title 人员基本信息系统 - 快速启动
cd /d "%~dp0"

echo ============================================
echo        人员基本信息系统 - 快速启动
echo ============================================
echo.

echo [1/4] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo [错误] 未找到 Python！请先安装 Python 3.9+
    pause
    exit /b 1
)

echo.
echo [2/4] 安装后端依赖...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 依赖安装可能失败，继续尝试启动...
)

echo.
echo [3/4] 启动后端服务 (端口 8000)...
start "后端服务 - 人员信息系统" cmd /k "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd ..

echo 等待后端启动...
timeout /t 5 /nobreak >nul

echo.
echo [4/4] 启动前端服务 (端口 5173)...
cd frontend
if not exist "node_modules" (
    echo [提示] 首次运行，正在安装前端依赖...
    call npm install
)
start "前端服务 - 人员信息系统" cmd /k "npm run dev"
cd ..

echo.
echo ============================================
echo  系统启动完成！
echo ============================================
echo.
echo  前端地址: http://127.0.0.1:5173
echo  后端API:  http://127.0.0.1:8000/docs
echo  默认账号: admin
echo  默认密码: admin123
echo.
echo  请在新打开的窗口中查看服务运行状态
echo  关闭窗口即可停止对应服务
echo.
pause