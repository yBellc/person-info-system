# -*- coding: utf-8 -*-
"""彻底重启后端服务 - 杀掉旧进程 + 重新启动"""
import subprocess
import time
import sys
import os

print("=" * 60)
print("彻底重启后端服务")
print("=" * 60)

# Step 1: 杀掉占用 8000 端口的进程（只杀监听 8000 的，不杀自己）
print("\n[1/3] 正在杀掉占用 8000 端口的进程...")

# 用 netstat 找到占用 8000 端口的 PID
try:
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True, text=True, timeout=10
    )
    pids_to_kill = set()
    for line in result.stdout.splitlines():
        if ':8000' in line and 'LISTENING' in line:
            parts = line.strip().split()
            pid = parts[-1]
            pids_to_kill.add(pid)
            print(f"  发现占用端口的 PID: {pid}")
    
    if pids_to_kill:
        for pid in pids_to_kill:
            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
            print(f"  已杀掉 PID {pid}")
        time.sleep(2)
    else:
        print("  没有进程占用 8000 端口")
except Exception as e:
    print(f"  杀进程时出错: {e}")

# Step 2: 启动新的后端服务（用 DETACHED_PROCESS 脱离终端）
print("\n[2/3] 启动新的后端服务...")
backend_dir = r"e:\工作工作\text\person-info-system\backend"

# 用 python -m uvicorn 启动
cmd = [
    r"D:\python\python.exe",
    "-m", "uvicorn", "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--log-level", "info",
    "--access-log",
]

# 在后台启动（DETACHED_PROCESS 让它独立运行）
proc = subprocess.Popen(
    cmd,
    cwd=backend_dir,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.DETACHED_PROCESS,
)
print(f"  进程已启动 (PID: {proc.pid})")

# Step 3: 等待服务就绪并检查路由
print("\n[3/3] 等待服务就绪并检查路由...")
import urllib.request
import json

for i in range(30):
    time.sleep(1)
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
        if resp.status == 200:
            print(f"  ✅ 服务已启动！")
            
            # 检查 expense 路由是否注册
            time.sleep(1)  # 多等一秒让路由完全注册
            try:
                resp2 = urllib.request.urlopen("http://127.0.0.1:8000/openapi.json", timeout=5)
                data = json.loads(resp2.read())
                paths = data.get("paths", {})
                
                # 检查 expense 相关路由
                expense_paths = [p for p in paths if any(kw in p for kw in ["attachment", "attachments", "invoice", "voucher"])]
                
                if expense_paths:
                    print(f"  ✅ Expense 路由已注册！({len(expense_paths)} 个路由)")
                    for p in sorted(expense_paths)[:5]:
                        methods = list(paths[p].keys())
                        print(f"    {methods} {p}")
                    if len(expense_paths) > 5:
                        print(f"    ... 还有 {len(expense_paths) - 5} 个路由")
                else:
                    print("  ❌ Expense 路由未注册！")
                    # 显示已有的路由
                    print("  当前可用的路由（部分）：")
                    for p in sorted(paths.keys())[:20]:
                        methods = list(paths[p].keys())
                        print(f"    {methods} {p}")
                    
                    # 尝试获取更详细的错误信息
                    print("\n  正在获取启动日志...")
                    log_file = os.path.join(backend_dir, "server.log")
                    if os.path.exists(log_file):
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                            # 显示最后 30 行
                            print("  启动日志最后 30 行：")
                            for line in lines[-30:]:
                                print(f"    {line.rstrip()}")
            except Exception as e:
                print(f"  ⚠️ 检查路由时出错: {e}")
            
            print("\n" + "=" * 60)
            print("服务已就绪")
            print("=" * 60)
            break
    except Exception as e:
        if i % 5 == 0:
            print(f"  ⏳ 等待中... ({i+1}/30) - {e}")
else:
    print("  ❌ 服务启动超时！")
    print("\n  可能的原因：")
    print("    1. 端口 8000 仍被占用")
    print("    2. Python 环境有问题")
    print("    3. 代码导入错误")
    print("\n  请检查 backend/server.log 获取详细错误信息")

print("\n按回车键退出...")
try:
    input()
except:
    pass
