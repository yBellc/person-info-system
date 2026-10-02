# -*- coding: utf-8 -*-
"""
自动安装 Node.js LTS 并构建前端 - 修复版
解决：zip损坏、编码乱码、下载失败等问题
"""
import sys
import os

# 修复Windows CMD下的编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import urllib.request
import zipfile
import subprocess
import shutil
import time

# ============ 配置 ============
NODE_VERSION = "20.18.0"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
NODE_INSTALL_DIR = os.path.join(PROJECT_DIR, "tools", "node")
ZIP_PATH = os.path.join(PROJECT_DIR, f"node-v{NODE_VERSION}-win-x64.zip")
# ================================

log_lines = []

def log(msg, tag="INFO"):
    line = f"[{tag}] {msg}"
    print(line)
    log_lines.append(line)

def delete_corrupted_zip():
    """删除损坏的zip文件"""
    if os.path.exists(ZIP_PATH):
        size = os.path.getsize(ZIP_PATH)
        if size < 1000000:  # Node.js zip 至少 40MB，小于1MB肯定是坏的
            log(f"Found corrupted zip (only {size} bytes). Deleting...", "WARN")
            os.remove(ZIP_PATH)
            return True
        else:
            log(f"Found existing zip ({size:,} bytes). Will verify integrity...", "INFO")
            # 验证是否真的是合法zip
            try:
                with zipfile.ZipFile(ZIP_PATH, "r") as zf:
                    # 列出文件验证
                    names = zf.namelist()
                    if len(names) > 100:
                        log(f"Zip verified OK ({len(names)} entries).", "OK")
                        return False
                    else:
                        log("Zip has too few entries, might be corrupted. Re-downloading...", "WARN")
                        os.remove(ZIP_PATH)
                        return True
            except Exception as e:
                log(f"Zip verification failed: {e}. Re-downloading...", "WARN")
                os.remove(ZIP_PATH)
                return True
    return False

def download_node():
    """下载 Node.js"""
    log(f"Downloading Node.js v{NODE_VERSION} ...")
    log(f"URL: {NODE_URL}")
    log("(Large file ~45MB, may take 1-3 minutes on first run)")

    # 进度条回调
    last_percent = [0]
    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, int(downloaded * 100 / total_size))
            if percent >= last_percent[0] + 10:
                last_percent[0] = percent
                print(f"  Downloading... {percent}% ({downloaded//1024//1024}MB / {total_size//1024//1024}MB)")

    try:
        urllib.request.urlretrieve(NODE_URL, ZIP_PATH, reporthook=progress)
        size = os.path.getsize(ZIP_PATH)
        log(f"Download complete! Size: {size:,} bytes", "OK")

        # 下载后再次验证
        try:
            with zipfile.ZipFile(ZIP_PATH, "r") as zf:
                test = zf.namelist()
                log(f"Zip integrity verified ({len(test)} entries).", "OK")
        except Exception as e:
            log(f"Zip still corrupted after download: {e}", "ERROR")
            return False

        return True
    except Exception as e:
        log(f"Download failed: {e}", "ERROR")
        log("Tips:", "HINT")
        log("  1. Check your internet connection", "HINT")
        log("  2. Try downloading manually from https://nodejs.org/", "HINT")
        log(f"  3. Then place the zip at: {ZIP_PATH}", "HINT")
        return False

def extract_node():
    """解压 Node.js"""
    log(f"Extracting to: {NODE_INSTALL_DIR}")

    # 清理旧的安装
    if os.path.exists(NODE_INSTALL_DIR):
        shutil.rmtree(NODE_INSTALL_DIR, ignore_errors=True)

    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zf.extractall(NODE_INSTALL_DIR)

        # 查找解压后的目录
        extracted_dir = None
        for item in os.listdir(NODE_INSTALL_DIR):
            full = os.path.join(NODE_INSTALL_DIR, item)
            if os.path.isdir(full) and "node" in item.lower():
                if os.path.exists(os.path.join(full, "node.exe")):
                    extracted_dir = full
                    break

        if extracted_dir is None:
            # 可能直接解压到 NODE_INSTALL_DIR 里了
            if os.path.exists(os.path.join(NODE_INSTALL_DIR, "node.exe")):
                log("Node.js extracted directly to install dir.", "OK")
                return True
            log("Cannot find node.exe after extraction!", "ERROR")
            # 显示目录内容帮助调试
            log(f"Contents of {NODE_INSTALL_DIR}:", "DEBUG")
            for item in os.listdir(NODE_INSTALL_DIR)[:20]:
                log(f"  {item}", "DEBUG")
            return False

        # 把解压目录里的内容移到上层
        log(f"Moving files from {extracted_dir} -> {NODE_INSTALL_DIR}")
        for item in os.listdir(extracted_dir):
            src = os.path.join(extracted_dir, item)
            dst = os.path.join(NODE_INSTALL_DIR, item)
            if os.path.isfile(src):
                shutil.move(src, dst)
            elif os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
        shutil.rmtree(extracted_dir)

        log("Node.js extraction complete!", "OK")
        return True
    except Exception as e:
        log(f"Extraction failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def build_frontend(node_exe):
    """构建前端"""
    os.chdir(FRONTEND_DIR)
    log(f"Working directory: {FRONTEND_DIR}")

    # 检查 vite
    vite_path = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
    if not os.path.exists(vite_path):
        log("Vite not found. Need to run npm install first.", "WARN")
        npm_cmd = os.path.join(NODE_INSTALL_DIR, "npm.cmd")
        if not os.path.exists(npm_cmd):
            npm_cmd = os.path.join(NODE_INSTALL_DIR, "npm")
        if not os.path.exists(npm_cmd):
            log("npm not found in Node.js installation!", "ERROR")
            return False
        log("Running npm install (this may take a while)...")
        env = os.environ.copy()
        env["PATH"] = NODE_INSTALL_DIR + os.pathsep + env.get("PATH", "")
        try:
            r = subprocess.run(
                [npm_cmd, "install"], capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=300, cwd=FRONTEND_DIR, env=env,
            )
            if r.returncode != 0:
                err_text = (r.stderr or "")[-500:] or (r.stdout or "")[-500:]
                log(f"npm install failed: {err_text}", "ERROR")
                return False
            log("npm install complete!", "OK")
        except Exception as e:
            log(f"npm install exception: {e}", "ERROR")
            return False

    # 检查 package.json
    pkg_path = os.path.join(FRONTEND_DIR, "package.json")
    if not os.path.exists(pkg_path):
        log("package.json not found in frontend directory!", "ERROR")
        return False

    log("Running Vite build...")
    env = os.environ.copy()
    env["PATH"] = NODE_INSTALL_DIR + os.pathsep + env.get("PATH", "")
    try:
        r = subprocess.run(
            [node_exe, vite_path, "build"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=120, cwd=FRONTEND_DIR, env=env,
        )

        if r.returncode != 0:
            log("Build FAILED!", "ERROR")
            err_text = (r.stderr or "")[-1000:] or (r.stdout or "")[-1000:]
            log(f"Error output:\n{err_text}", "ERROR")
            return False

        # 显示最后几行构建输出
        log("Build output:", "INFO")
        for line in (r.stdout or "").splitlines()[-15:]:
            log(f"  {line}", "INFO")
    except Exception as e:
        log(f"Vite build exception: {e}", "ERROR")
        return False

    # 检查 dist
    dist_dir = os.path.join(FRONTEND_DIR, "dist")
    if not os.path.isdir(dist_dir):
        log("dist/ directory not found!", "ERROR")
        return False

    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        count = sum(1 for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f)))
        log(f"Build SUCCESSFUL! {count} asset files generated in dist/assets/", "OK")
    else:
        log("No assets directory in dist/", "WARN")

    index_html = os.path.join(dist_dir, "index.html")
    if os.path.exists(index_html):
        log("index.html found in dist/", "OK")

    return True

def main():
    print()
    print("=" * 60)
    print("  Personnel Info System - Frontend Auto-Builder")
    print("  (Auto-install Node.js + Vite build)")
    print("=" * 60)
    print()

    os.makedirs(NODE_INSTALL_DIR, exist_ok=True)
    node_exe = os.path.join(NODE_INSTALL_DIR, "node.exe")

    # Step 1: Check if Node already installed
    if os.path.exists(node_exe):
        log(f"Node.js already installed: {node_exe}", "OK")
    else:
        # Step 1a: Clean corrupted zip
        delete_corrupted_zip()

        # Step 1b: Download
        if not os.path.exists(ZIP_PATH):
            if not download_node():
                input("\nPress Enter to exit...")
                return 1
        else:
            log("Using existing zip file.", "INFO")

        # Step 1c: Extract
        if not extract_node():
            input("\nPress Enter to exit...")
            return 1

        # Step 1d: Verify
        if not os.path.exists(node_exe):
            log(f"node.exe not found after extraction at: {node_exe}", "ERROR")
            log("Listing install directory contents:", "DEBUG")
            for item in os.listdir(NODE_INSTALL_DIR)[:30]:
                log(f"  {item}", "DEBUG")
            input("\nPress Enter to exit...")
            return 1

        # Clean up zip
        try:
            os.remove(ZIP_PATH)
        except Exception:
            pass

    # Step 2: Verify node works
    try:
        r = subprocess.run(
            [node_exe, "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        if r.returncode != 0:
            log(f"Node.js not working: {r.stderr or ''}", "ERROR")
            input("\nPress Enter to exit...")
            return 1
        log(f"Node.js version: {(r.stdout or '').strip()}", "OK")
    except Exception as e:
        log(f"Node.js verification failed: {e}", "ERROR")
        input("\nPress Enter to exit...")
        return 1

    # Step 3: Build
    if not build_frontend(node_exe):
        input("\nPress Enter to exit...")
        return 1

    # Step 4: Done
    print()
    print("=" * 60)
    print("  BUILD SUCCESSFUL!")
    print()
    print("  Next steps:")
    print("  1. Close the old START.bat window (stop backend)")
    print("  2. Double-click START.bat to restart backend")
    print("  3. Browser: Ctrl+F5 to force-refresh (clear cache)")
    print("  4. All new features are now live!")
    print("=" * 60)

    # Save log
    try:
        with open(os.path.join(PROJECT_DIR, "build_log.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        print(f"\nLog saved to: build_log.txt")
    except Exception:
        pass

    input("\nPress Enter to exit...")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        rc = 99
    sys.exit(rc or 0)
