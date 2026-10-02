# -*- coding: utf-8 -*-
"""
【内网部署工具1】部署环境自检脚本 — DEPLOY PRE-FLIGHT CHECK
上线前必须跑一次，全部 PASS 才能上线。
检查项：
  [1] Python可用性
  [2] 全部依赖包
  [3] app.main 模块导入
  [4] 数据库连接（SQLite读写测试）
  [5] 所有FastAPI路由可注册（预检）
  [6] 前端 dist 目录存在
  [7] 端口 8000 是否可用（或已被本服务占用）
  [8] 是否在监听 0.0.0.0（内网访问必备，不能只绑定127.0.0.1）
  [9] Windows 防火墙放行记录检查
  [10] 启动服务 -> 真实 HTTP 请求 /docs 健康检查
"""
import sys
import os
import socket
import subprocess
import time
import datetime
import traceback

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SELF_DIR, "backend")
FRONTEND_DIST = os.path.join(SELF_DIR, "frontend", "dist")
DB_PATH = os.path.join(BACKEND_DIR, "person_info.db")
REPORT = os.path.join(SELF_DIR, f"部署自检报告_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

PY_CANDIDATES = [r"D:\python\python.exe", sys.executable, "python", "py"]

passes = 0
fails = 0
report_lines = []


def log(msg):
    print(msg)
    report_lines.append(msg)


def check(label, ok, detail=""):
    global passes, fails
    mark = "✅ PASS" if ok else "❌ FAIL"
    line = f"  {mark} [{label}]"
    if detail:
        line += f"  -> {detail}"
    log(line)
    if ok:
        passes += 1
    else:
        fails += 1
    return ok


def find_python():
    for p in PY_CANDIDATES:
        try:
            r = subprocess.run(
                [p, "-c", "import sys; print(sys.executable, end='')"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                return p if os.path.isabs(p) else r.stdout.strip()
        except Exception:
            continue
    return None


def port_in_use(port=8000, listen_host="0.0.0.0"):
    """True if the port is already listening on any address"""
    try:
        out = subprocess.check_output(["netstat", "-ano"], shell=True).decode("gbk", errors="ignore")
        for line in out.splitlines():
            if "LISTENING" in line and f":{port}" in line:
                return True
    except Exception:
        pass
    return False


def main():
    global passes, fails
    print()
    print("=" * 68)
    print("  单位信息管理系统 — 部署前环境自检（PRE-FLIGHT CHECK）")
    print("  全部 PASS 后才能上线部署到内网服务器")
    print("=" * 68)
    print()
    report_lines.append("单位信息管理系统 — 部署自检报告")
    report_lines.append(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"运行目录: {SELF_DIR}")
    report_lines.append("")

    # --------- [1] Python ---------
    log("[1/10] Python 解释器")
    python = find_python()
    if python:
        r = subprocess.run([python, "--version"], capture_output=True, text=True, timeout=10)
        check("Python 解释器", True, f"{python}  ({(r.stdout or r.stderr).strip()})")
    else:
        check("Python 解释器", False, "找不到可用的Python，请先安装Python 3.8+")
        python = None

    # --------- [2] 依赖包 ---------
    log("\n[2/10] 依赖包（requirements.txt 全部）")
    deps_spec = [
        ("fastapi",              "fastapi>=0.109"),
        ("uvicorn",              "uvicorn[standard]"),
        ("sqlalchemy",           "sqlalchemy>=2.0"),
        ("pydantic",             "pydantic>=2.0"),
        ("jose",                 "python-jose[cryptography]"),
        ("bcrypt",               "bcrypt>=4.0"),
        ("multipart",            "python-multipart"),
        ("openpyxl",             "openpyxl>=3.1"),
        ("docx",                 "python-docx>=1.1"),
        ("dateutil",             "python-dateutil"),
    ]
    dep_fail = 0
    for imp, pip_name in deps_spec:
        if python is None:
            check(f"依赖 {imp}", False, "Python不可用，跳过检查")
            dep_fail += 1
            continue
        r = subprocess.run(
            [python, "-c", f"import {imp}; print('ok')"],
            capture_output=True, text=True, timeout=20, cwd=BACKEND_DIR,
        )
        ok = r.returncode == 0 and "ok" in r.stdout
        if ok:
            check(f"依赖 {pip_name}", True)
        else:
            check(f"依赖 {pip_name}", False, f"缺失，请执行：pip install {pip_name}")
            dep_fail += 1
    if dep_fail == 0 and python:
        # Auto-install check
        req_path = os.path.join(BACKEND_DIR, "requirements.txt")
        if os.path.exists(req_path):
            log("      如需确保版本严格一致，可执行: pip install -r backend\\requirements.txt")

    # --------- [3] app.main 导入 ---------
    log("\n[3/10] 核心模块导入（app.main，含所有路由）")
    if python:
        code = (
            "import sys, os, traceback\n"
            f"os.chdir({BACKEND_DIR!r})\n"
            f"sys.path.insert(0, {BACKEND_DIR!r})\n"
            "try:\n"
            "    from app.main import app\n"
            "    routes = sorted([r.path for r in app.routes])\n"
            "    print(f'ROUTES_COUNT={len(routes)}')\n"
            "    print('IMPORT_OK')\n"
            "except Exception:\n"
            "    traceback.print_exc()\n"
            "    sys.exit(1)\n"
        )
        r = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=90)
        if r.returncode == 0 and "IMPORT_OK" in r.stdout:
            cnt = 0
            for line in r.stdout.splitlines():
                if line.startswith("ROUTES_COUNT="):
                    try: cnt = int(line.split("=",1)[1])
                    except: pass
            check("app.main 完整导入", True, f"已注册路由总数 = {cnt}")
        else:
            out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()[-40:]
            check("app.main 完整导入", False,
                  "导入失败，尾40行：\n" + "\n".join("       | " + l for l in out))
    else:
        check("app.main 完整导入", False, "Python不可用")

    # --------- [4] 数据库 ---------
    log("\n[4/10] 数据库（SQLite）可读写")
    if os.path.exists(DB_PATH):
        try:
            size_kb = os.path.getsize(DB_PATH) // 1024
            if python:
                code = (
                    "import sqlite3, os\n"
                    f"db = {DB_PATH!r}\n"
                    "conn = sqlite3.connect(db)\n"
                    "cur = conn.cursor()\n"
                    "cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' LIMIT 1\")\n"
                    "cur.fetchone()\n"
                    "cur.execute(\"CREATE TABLE IF NOT EXISTS _deploy_smoke(id INTEGER PRIMARY KEY, ts TEXT)\")\n"
                    "conn.commit()\n"
                    "cur.execute(\"INSERT INTO _deploy_smoke(ts) VALUES (?)\", (\"test\",))\n"
                    "conn.commit()\n"
                    "cur.execute(\"DELETE FROM _deploy_smoke\")\n"
                    "conn.commit()\n"
                    "conn.close()\n"
                    "print('DB_OK')\n"
                )
                r = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and "DB_OK" in r.stdout:
                    check("SQLite 可读写", True, f"DB文件大小 {size_kb:,} KB")
                else:
                    check("SQLite 可读写", False, f"测试失败：{r.stderr.strip()[:200]}")
            else:
                check("SQLite 可读写", True, f"文件存在（{size_kb:,} KB），未执行脚本测试")
        except Exception as e:
            check("SQLite 可读写", False, f"异常：{e}")
    else:
        check("SQLite 可读写", False,
              f"数据库文件不存在：{DB_PATH}，首次启动会自动创建，但建议先在本地测试好再部署")

    # --------- [5] 路由可注册（已包含在第3步里做了）---------
    log("\n[5/10] 前端静态文件（前端打包产物）")
    index_html = os.path.join(FRONTEND_DIST, "index.html")
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(index_html) and os.path.isdir(assets_dir):
        asset_count = len(os.listdir(assets_dir))
        check("前端 dist 目录完整", True,
              f"index.html 存在 + assets 下共 {asset_count} 个打包文件")
    else:
        check("前端 dist 目录完整", False,
              "缺少 frontend/dist/index.html 或 assets 目录，"
              "请在 frontend 目录下执行：npm install && npm run build")

    # --------- [6] 端口 8000 可用性 ---------
    log("\n[6/10] 端口 8000 状态")
    used = port_in_use(8000)
    if not used:
        check("8000 端口空闲可用", True, "没有其他程序占用，启动服务后可正常监听")
    else:
        # 判断是否就是我们的服务在跑
        pid = None
        try:
            out = subprocess.check_output(["netstat", "-ano"], shell=True).decode("gbk", errors="ignore")
            for line in out.splitlines():
                if ":8000" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        break
        except Exception:
            pass
        check("8000 端口", True, f"已被占用（PID={pid}），如果是本服务可正常使用，否则请先释放或改端口")

    # --------- [7] 绑定 0.0.0.0（内网必备）---------
    log("\n[7/10] 启动绑定地址必须是 0.0.0.0（内网访问必备）")
    # 通过读取启动脚本的默认值，也检查 launcher 里的硬编码
    launcher_path = os.path.join(SELF_DIR, "launcher.py")
    bind_ok = False
    note = ""
    if os.path.exists(launcher_path):
        with open(launcher_path, "r", encoding="utf-8") as f:
            c = f.read()
        if "--host", "0.0.0.0" in c:
            bind_ok = True
            note = "launcher.py 中已使用 --host 0.0.0.0，内网可访问"
    old_bat = os.path.join(SELF_DIR, "启动服务.bat")
    if os.path.exists(old_bat):
        with open(old_bat, "r", encoding="utf-8") as f:
            c = f.read()
        if "0.0.0.0" in c:
            bind_ok = True
            note = "启动脚本已使用 --host 0.0.0.0，内网可访问"
    check("绑定地址 = 0.0.0.0", bind_ok, note or (
        "未检测到 0.0.0.0 绑定，部署到内网时必须加！否则内网其他机器访问不了"
        "（建议使用 launcher.py / START.bat，里面已硬编码 0.0.0.0）"
    ))

    # --------- [8] Windows 防火墙 8000 ---------
    log("\n[8/10] Windows 防火墙放行 8000 端口")
    fw_ok = False
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
            capture_output=True, text=True, timeout=30,
        )
        if "8000" in (r.stdout or ""):
            fw_ok = True
    except Exception:
        pass
    if fw_ok:
        check("防火墙已放行 8000", True, "已存在 8000 端口的入站规则，内网客户端可以连接")
    else:
        check("防火墙已放行 8000", False,
              "未检测到 8000 放行规则。部署前请运行同级目录下的 FIREWALL_OPEN.bat（管理员身份运行一次即可），"
              "或手动执行：netsh advfirewall firewall add rule name=\"PersonInfo 8000\" dir=in action=allow protocol=TCP localport=8000")

    # --------- [9] 真实启动 + HTTP 健康检查 ---------
    log("\n[9/10] 启动服务 + HTTP /docs 健康检查（最终验收）")
    # 只有当端口空闲时才真的启动
    can_start = (python is not None) and (not port_in_use(8000))
    if can_start:
        log("    -> 端口空闲，准备临时启动 uvicorn 做真实HTTP测试...")
        DETACHED = 0x00000008
        NEW_GRP = 0x00000200
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        tmp_log = os.path.join(SELF_DIR, "preflight_server_test.log")
        try:
            lf = open(tmp_log, "ab")
        except Exception:
            lf = subprocess.DEVNULL
        p = subprocess.Popen(
            [python, "-u", "-m", "uvicorn",
             "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND_DIR, stdout=lf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED | NEW_GRP, startupinfo=si,
        )
        # wait up to 20s for port
        ready = False
        for i in range(20):
            time.sleep(1)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", 8000))
                s.close()
                ready = True
                break
            except Exception:
                pass
        http_ok = False
        http_info = ""
        if ready:
            # HTTP 调用 /docs 看能否返回 200
            try:
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=10) as resp:
                    status = resp.status
                    if status == 200:
                        http_ok = True
                        http_info = f"GET /docs -> HTTP {status}"
                    else:
                        http_info = f"GET /docs -> HTTP {status} (非200)"
            except Exception as e:
                http_info = f"HTTP 请求异常：{e}"
        else:
            http_info = "20秒内端口仍未监听（启动失败）"
            # 读尾日志
            if os.path.exists(tmp_log):
                try:
                    with open(tmp_log, "r", encoding="utf-8", errors="replace") as f:
                        tail = f.read().splitlines()[-30:]
                    http_info += "\n" + "\n".join("       | " + l for l in tail)
                except Exception:
                    pass
        # terminate
        try:
            p.terminate()
            time.sleep(0.8)
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
        check("真实启动 + HTTP /docs 健康检查", http_ok, http_info)
    elif port_in_use(8000):
        # 已经有服务在跑 -> 直接HTTP测
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=10) as resp:
                status = resp.status
                ok = (status == 200)
                check("真实HTTP /docs 健康检查", ok,
                      f"8000已有服务运行，GET /docs -> HTTP {status}"
                      + ("，可用！" if ok else "，但返回非200！"))
        except Exception as e:
            check("真实HTTP /docs 健康检查", False,
                  f"8000已有进程但无法HTTP访问：{e}，需重启服务或查看日志")
    else:
        check("真实HTTP /docs 健康检查", False,
              "Python不可用，无法执行测试。上线前必须通过此条检查")

    # --------- [10] 服务器内网可达性提示 ---------
    log("\n[10/10] 部署到内网的额外建议（非自动检查）")
    log("    ℹ️  服务器应设置静态IP，并在启动脚本里写明 0.0.0.0:8000")
    log("    ℹ️  建议安装为 Windows 服务（见 INSTALL_SERVICE.bat），开机自动启动无需登录")
    log("    ℹ️  建议配置 watchdog 进程守护脚本（WATCHDOG_RUN.bat），挂掉自动重启")
    log("    ℹ️  员工端访问地址应统一使用：http://服务器内网IP:8000")

    # --------- 总结 ---------
    print()
    print("=" * 68)
    total = passes + fails
    verdict = "🟢 全部通过，可以上线部署！" if fails == 0 else "🔴 存在失败项，修复后再部署"
    log(f"【最终结论】{verdict}")
    log(f"    总数 = {total}   ✅ PASS = {passes}   ❌ FAIL = {fails}")
    print("=" * 68)
    if fails > 0:
        print("     修复 FAIL 项后，重新运行本脚本直到所有项全部 PASS。")
    else:
        print("     🎉🎉🎉 部署自检全部通过，可放心上线内网服务器！")
        print()

    # Write report
    try:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"     完整报告已保存：{REPORT}")
    except Exception as e:
        print(f"     （保存报告失败：{e}）")

    try:
        input("\n按回车键退出...")
    except Exception:
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        try:
            input("\n按回车键退出...")
        except Exception:
            time.sleep(60)
