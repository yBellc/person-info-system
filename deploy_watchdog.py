# -*- coding: utf-8 -*-
"""
【内网部署工具2】进程守护 Watchdog
每 15 秒检查一次 8000 端口是否在监听、是否能返回 HTTP 200；
任何一项失败，等待 10 秒重试，连续 2 次失败就自动杀掉旧进程并重新拉起服务。
同时写日志到 watchdog_log.txt，方便事后复盘。
建议：把 WATCHDOG_RUN.bat 放到【Windows启动文件夹】，开机自启守护进程。
"""
import sys
import os
import socket
import subprocess
import time
import datetime
import signal
import traceback

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SELF_DIR, "backend")
LOG = os.path.join(SELF_DIR, "watchdog_log.txt")
PID_FILE = os.path.join(BACKEND_DIR, "server.pid")

# 自定义Python路径
PY_CANDIDATES = [r"D:\python\python.exe", sys.executable, "python", "py"]

CHECK_INTERVAL_S = 15        # 常规检查间隔
RETRY_WAIT_S = 10            # 单次失败后的等待时间
FAIL_THRESHOLD = 2           # 连续失败 N 次才重启（避免偶发网络抖动误杀）
HTTP_TIMEOUT_S = 8

log_lines_buffer = []


def log(msg, tag="INFO"):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    log_lines_buffer.append(line)
    # 每10条 flush 一次到磁盘
    if len(log_lines_buffer) >= 10:
        _flush()


def _flush():
    global log_lines_buffer
    if not log_lines_buffer:
        return
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(log_lines_buffer) + "\n")
        log_lines_buffer = []
    except Exception:
        pass


def find_python():
    import shutil
    for p in PY_CANDIDATES:
        try:
            if p in ("python", "py"):
                p2 = shutil.which(p)
                if not p2:
                    continue
                p = p2
            r = subprocess.run(
                [p, "-c", "import sys"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None


def is_port_listening(port=8000):
    try:
        out = subprocess.check_output(["netstat", "-ano"], shell=True).decode("gbk", errors="ignore")
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                return True
    except Exception:
        pass
    return False


def http_healthcheck(port=8000):
    try:
        import urllib.request
        url = f"http://127.0.0.1:{port}/docs"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_pid_by_port(port=8000):
    try:
        out = subprocess.check_output(["netstat", "-ano"], shell=True).decode("gbk", errors="ignore")
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts and parts[-1].isdigit():
                    return int(parts[-1])
    except Exception:
        return None
    return None


def kill_pid(pid):
    if not pid:
        return False
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid), "/T"],
            capture_output=True, text=True, timeout=15
        )
        log(f"taskkill /PID {pid} -> {r.returncode} {r.stdout.strip()[:120]}")
        return True
    except Exception as e:
        log(f"taskkill 异常：{e}", "WARN")
        return False


def start_server(python):
    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    server_log = os.path.join(BACKEND_DIR, "server.log")
    try:
        lf = open(server_log, "ab")
    except Exception:
        lf = subprocess.DEVNULL
    try:
        p = subprocess.Popen(
            [python, "-u", "-m", "uvicorn",
             "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=BACKEND_DIR,
            stdout=lf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED | NEW_GROUP,
            startupinfo=si,
        )
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
        except Exception:
            pass
        log(f"服务已重新拉起，新PID={p.pid}", "OK")
        # 等3秒让它完成启动，避免下一轮循环还没起来就误判
        time.sleep(3)
        return True
    except Exception as e:
        log(f"启动失败: {e}\n{traceback.format_exc()}", "ERROR")
        return False


def stop_signalled(*_):
    log("Watchdog received stop signal, exiting...", "INFO")
    _flush()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, stop_signalled)
    signal.signal(signal.SIGTERM, stop_signalled)

    log("=" * 60)
    log("Watchdog 启动守护进程")
    log(f"检查间隔 = {CHECK_INTERVAL_S}s  重试等待 = {RETRY_WAIT_S}s  失败阈值 = {FAIL_THRESHOLD}")

    python = find_python()
    if not python:
        log("找不到可用Python解释器，Watchdog无法工作。", "FATAL")
        _flush()
        return 1
    log(f"使用 Python: {python}")

    consecutive_fails = 0

    while True:
        try:
            port_ok = is_port_listening(8000)
            http_ok = http_healthcheck(8000)

            if port_ok and http_ok:
                if consecutive_fails > 0:
                    log(f"[健康恢复] 服务恢复正常 port_ok={port_ok} http_ok={http_ok}", "OK")
                consecutive_fails = 0
                time.sleep(CHECK_INTERVAL_S)
                continue

            consecutive_fails += 1
            log(f"检测异常 第{consecutive_fails}/{FAIL_THRESHOLD}次  port_listen={port_ok}  http_200={http_ok}", "WARN")

            if consecutive_fails < FAIL_THRESHOLD:
                time.sleep(RETRY_WAIT_S)
                continue

            # ===== 达到阈值，强制重启 =====
            log("达到阈值，执行重启流程", "WARN")
            old_pid = get_pid_by_port(8000)
            if old_pid:
                log(f"旧进程 PID={old_pid}，强制终结...", "WARN")
                kill_pid(old_pid)
                time.sleep(2)
            else:
                log("端口无监听进程，无需kill", "INFO")

            # 启动新进程
            ok = start_server(python)
            if ok:
                # 等待服务完全起来
                for i in range(30):
                    time.sleep(1)
                    if is_port_listening(8000) and http_healthcheck(8000):
                        log("重启后服务恢复正常", "OK")
                        consecutive_fails = 0
                        break
                else:
                    log("重启后仍未进入健康状态，下轮循环继续尝试", "ERROR")
            # 即使失败也进入下一轮循环继续检测
            time.sleep(CHECK_INTERVAL_S)

        except Exception as e:
            log(f"Watchdog主循环异常: {e}\n{traceback.format_exc()}", "FATAL")
            time.sleep(5)
        finally:
            _flush()


if __name__ == "__main__":
    rc = main()
    _flush()
    sys.exit(rc or 0)
