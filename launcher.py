# -*- coding: utf-8 -*-
"""
Person Info System - Launcher (ASCII filename version)
All Chinese strings live inside this .py file so that CMD/GBK encoding problems
in the .bat wrapper never affect us.
"""
import sys
import os
import socket
import subprocess
import time
import traceback

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SELF_DIR, "backend")
RUN_LOG = os.path.join(SELF_DIR, "launcher_log.txt")
SERVER_LOG = os.path.join(BACKEND_DIR, "server.log")
PID_FILE = os.path.join(BACKEND_DIR, "server.pid")

WELCOME = """
============================================================
   Person Info System - Smart Launcher
   (This window will NOT close on failure. See launcher_log.txt)
============================================================
"""

lines = []

def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    print(line)
    lines.append(line)

def flush():
    try:
        with open(RUN_LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass

def find_python():
    # 1. Hardcoded path (matches the project convention)
    for p in [r"D:\python\python.exe", sys.executable]:
        if not p:
            continue
        try:
            r = subprocess.run(
                [p, "-c", "import sys; print(sys.version, end='')"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                log(f"Python OK: {p}  (v{r.stdout.strip()})", "OK")
                return p
        except Exception:
            pass
    # 2. PATH-based (where, then python)
    import shutil
    for name in ["python", "py"]:
        path = shutil.which(name)
        if path:
            try:
                r = subprocess.run([path, "-V"], capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    log(f"Python OK: {path}  ({r.stdout.strip()})", "OK")
                    return path
            except Exception:
                pass
    return None

def check_port(port=8000):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def find_pid_by_port(port=8000):
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

def check_deps(python):
    deps = [
        ("fastapi",            "FastAPI"),
        ("uvicorn",            "Uvicorn"),
        ("sqlalchemy",         "SQLAlchemy"),
        ("pydantic",           "Pydantic"),
        ("jose",               "python-jose (JWT)"),
        ("bcrypt",             "bcrypt"),
        ("openpyxl",           "openpyxl (.xlsx)"),
        ("docx",               "python-docx (.docx)"),
    ]
    missing = []
    for imp, name in deps:
        r = subprocess.run(
            [python, "-c", f"import {imp}"],
            capture_output=True, text=True, timeout=20,
            cwd=BACKEND_DIR,
        )
        if r.returncode == 0:
            log(f"Dep OK: {name}", "OK")
        else:
            log(f"Dep MISSING: {name}", "WARN")
            missing.append((imp, name))
    return missing

def dry_import(python):
    # Run the import check in a subprocess to capture the real ImportError
    script = (
        "import sys, os, traceback\n"
        f"os.chdir({BACKEND_DIR!r})\n"
        f"sys.path.insert(0, {BACKEND_DIR!r})\n"
        "try:\n"
        "    import app.main\n"
        "    print('__IMPORT_OK__')\n"
        "except Exception:\n"
        "    traceback.print_exc()\n"
        "    sys.exit(1)\n"
    )
    r = subprocess.run(
        [python, "-c", script],
        capture_output=True, text=True, timeout=90,
    )
    if r.returncode == 0 and "__IMPORT_OK__" in r.stdout:
        return True, ""
    return False, ((r.stdout or "") + "\n" + (r.stderr or "")).strip()

def start_server(python):
    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        log_f = open(SERVER_LOG, "ab")
    except Exception:
        log_f = subprocess.DEVNULL
    try:
        p = subprocess.Popen(
            [python, "-u", "-m", "uvicorn",
             "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=BACKEND_DIR,
            stdout=log_f, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED | NEW_GROUP,
            startupinfo=si,
        )
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
        except Exception:
            pass
        log(f"Process launched PID={p.pid}. Waiting for port 8000...", "OK")
        return p
    except Exception as e:
        log(f"Popen failed: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def wait_port(timeout_s=25):
    for i in range(timeout_s):
        time.sleep(1)
        if check_port(8000):
            return True
        print(f"  waiting... {i+1}/{timeout_s}s", end="\r")
    print()
    return False

def main():
    print(WELCOME)
    try:
        # 1) Port already listening?
        log("Checking port 8000...")
        if check_port(8000):
            pid = find_pid_by_port(8000)
            log(f"PORT 8000 IS LISTENING. Server already running (PID={pid or 'unknown'})", "OK")
            log("  -> Please open: http://127.0.0.1:8000", "HINT")
            try:
                os.startfile("http://127.0.0.1:8000")
            except Exception:
                pass
            flush()
            return 0

        # 2) Locate python
        log("Locating Python interpreter...")
        python = find_python()
        if not python:
            log("FATAL: No usable Python found. Expected D:\\python\\python.exe", "ERROR")
            flush()
            return 2

        # 3) Dependencies
        log("Checking dependencies...")
        missing = check_deps(python)
        if missing:
            log(f"{len(missing)} deps missing. Trying pip install -r requirements.txt...", "WARN")
            req = os.path.join(BACKEND_DIR, "requirements.txt")
            if os.path.exists(req):
                r = subprocess.run(
                    [python, "-m", "pip", "install", "-r", req,
                     "--default-timeout=120", "--retries", "2"],
                    capture_output=True, text=True, timeout=900,
                    cwd=BACKEND_DIR,
                )
                log(f"pip exit={r.returncode}", "INFO")
                if r.returncode != 0:
                    tail = ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines()[-30:]
                    log("pip install failed. Last 30 lines:\n" + "\n".join(tail), "ERROR")
            still = check_deps(python)
            if still:
                log(f"Still missing {len(still)} deps after pip. Manual install required.", "ERROR")
        else:
            log("All dependencies present.", "OK")

        # 4) Import check (app.main)
        log("Running dry import-check for app.main...")
        ok, err = dry_import(python)
        if not ok:
            log("DRY IMPORT FAILED — see traceback below:", "ERROR")
            for line in err.splitlines()[-50:]:
                print(f"    | {line}")
                lines.append(f"    | {line}")
            log("Fix the errors above, then re-run launcher.", "HINT")
            flush()
            return 3
        log("Dry import PASSED.", "OK")

        # 5) Launch server
        log("Spawning uvicorn server...")
        p = start_server(python)
        if p is None:
            flush()
            return 4

        # 6) Wait
        ok = wait_port(25)
        if not ok:
            log("Port 8000 still NOT listening after 25s. Likely crashed.", "ERROR")
            if os.path.exists(SERVER_LOG):
                try:
                    with open(SERVER_LOG, "r", encoding="utf-8", errors="replace") as f:
                        tail = f.read().splitlines()[-60:]
                    log("=== LAST 60 lines of server.log ===", "INFO")
                    for line in tail:
                        print(f"    {line}")
                        lines.append(f"    {line}")
                except Exception as e:
                    log(f"Could not read server.log: {e}", "WARN")
            flush()
            return 5

        # 7) Success
        print()
        log("=" * 52, "OK")
        log("SERVER STARTED SUCCESSFULLY !", "OK")
        log("  Local:    http://127.0.0.1:8000", "OK")
        log("  Intranet: http://<YOUR_IP>:8000", "OK")
        log("=" * 52, "OK")
        try:
            os.startfile("http://127.0.0.1:8000")
            log("Tried to open browser automatically.", "INFO")
        except Exception:
            log("Please open http://127.0.0.1:8000 manually in your browser.", "HINT")

        flush()
        return 0

    except Exception as e:
        log(f"UNEXPECTED: {e}\n{traceback.format_exc()}", "FATAL")
        flush()
        return 99

if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        print(f"Top-level exception: {e}")
        rc = 99

    print()
    print("=" * 56)
    if rc == 0:
        print(f"[DONE] Exit code = {rc}. Closing this window will NOT stop the server.")
    else:
        print(f"[FAILED] Exit code = {rc}")
        print(f"         Check the output above, or read launcher_log.txt for details.")
        print(f"         If you cannot solve this, send launcher_log.txt to the developer.")
    print("=" * 56)
    try:
        input("\nPress ENTER to close this window... ")
    except Exception:
        time.sleep(45)
