"""启动 Ollama 并强制 CPU 模式，测试不同模型"""
import os
import sys
import time
import subprocess
import requests

OLLAMA_EXE = r"C:\Users\12408\AppData\Local\Programs\Ollama\ollama.exe"

# 1. 停止现有 Ollama
print("1. 停止现有 Ollama...")
subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
time.sleep(3)

# 2. 启动 Ollama（强制 CPU 模式）
print("\n2. 启动 Ollama (强制 CPU 模式)...")
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = ""        # 隐藏 GPU，强制 CPU
env["OLLAMA_NUM_GPU"] = "0"             # 不使用 GPU 层
env["OLLAMA_NUM_THREAD"] = "4"          # CPU 线程数

proc = subprocess.Popen(
    [OLLAMA_EXE, "serve"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

# 3. 等待启动
print("   等待启动...", end=" ")
for i in range(15):
    time.sleep(2)
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            print(f"OK ({i*2+2}s)")
            break
    except:
        sys.stdout.write(".")
        sys.stdout.flush()
else:
    print("FAIL")
    # 读取输出
    proc.terminate()
    out = proc.stdout.read(2000).decode('utf-8', errors='replace') if proc.stdout else ""
    print("   输出:", out)
    sys.exit(1)

# 4. 列出已有模型
r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
models = [m["name"] for m in r.json().get("models", [])]
print(f"\n3. 已有模型: {models}")

# 5. 测试 nomic-embed-text（CPU 模式）
print("\n4. 测试 nomic-embed-text (CPU 模式):")
try:
    r = requests.post(
        "http://127.0.0.1:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": "人员档案管理测试"},
        timeout=120,
    )
    if r.status_code == 200:
        emb = r.json().get("embedding", [])
        print(f"   ✅ 成功! 维度={len(emb)}")
    else:
        print(f"   ❌ 失败: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 6. 拉取小模型 qwen2.5:1.5b（1GB，CPU 友好）
print("\n5. 拉取 qwen2.5:1.5b (1.0GB, CPU 友好)...")
try:
    result = subprocess.run(
        [OLLAMA_EXE, "pull", "qwen2.5:1.5b"],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    print(f"   拉取完成: rc={result.returncode}")
    if result.returncode != 0:
        print(f"   输出: {result.stdout[-300:]}")
        print(f"   错误: {result.stderr[-300:]}")
except subprocess.TimeoutExpired:
    print("   ⏰ 拉取超时(10分钟)，可能网络慢")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 7. 测试对话
print("\n6. 测试 qwen2.5:1.5b 对话 (CPU 模式):")
try:
    r = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": "qwen2.5:1.5b",
            "messages": [{"role": "user", "content": "你好，用一句话介绍自己"}],
            "stream": False,
        },
        timeout=180,
    )
    if r.status_code == 200:
        answer = r.json()["message"]["content"]
        print(f"   ✅ 成功! 回答: {answer[:200]}")
    else:
        print(f"   ❌ 失败: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 8. 最终模型列表
r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
models = [(m["name"], round(m.get("size", 0)/1024/1024)) for m in r.json().get("models", [])]
print(f"\n7. 最终模型列表: {models}")

print("\n✅ 测试完成! Ollama 进程保持在后台运行")
print(f"   PID: {proc.pid}")
