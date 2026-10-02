@echo off
title 后端服务 - 人员信息系统 (端口8000)
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
echo.
echo 后端已停止。按任意键关闭。
pause
