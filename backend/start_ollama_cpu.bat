@echo off
REM Ollama CPU 模式启动脚本
set CUDA_VISIBLE_DEVICES=
set OLLAMA_NUM_GPU=0
set OLLAMA_NUM_THREAD=4
set OLLAMA_HOST=127.0.0.1:11434
"C:\Users\12408\AppData\Local\Programs\Ollama\ollama.exe" serve
