# -*- coding: utf-8 -*-
"""
【内网部署工具3】安装/卸载 Windows 服务（开机自启、服务器不用登录也能跑）
- 安装：双击 INSTALL_SERVICE.bat（会自动用管理员权限跑）
- 卸载：运行 UNINSTALL_SERVICE.bat
- 核心逻辑：利用 Windows 自带的「计划任务」做开机启动（无需nssm等第三方工具）
            优点：Windows原生、无额外依赖、任何Windows机器都能装
"""
import sys
import os
import subprocess
import ctypes
import argparse

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_NAME = "PersonInfoSystem_WebService"
WATCHDOG_TASK = "PersonInfoSystem_Watchdog"
LAUNCHER_BAT = os.path.join(SELF_DIR, "START.bat")
WATCHDOG_BAT = os.path.join(SELF_DIR, "WATCHDOG_RUN.bat")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def elevate_self():
    """重新用管理员权限启动同一个python脚本"""
    params = " ".join(f'"{x}"' for x in sys.argv)
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        return ret > 32  # <=32 表示失败
    except Exception:
        return False


def run(cmd_list):
    print(f">>> {' '.join(cmd_list)}")
    try:
        r = subprocess.run(cmd_list, capture_output=True, text=True, timeout=60)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        print(out.strip()[:2000])
        print(f"    exit = {r.returncode}\n")
        return r.returncode == 0
    except Exception as e:
        print(f"    执行异常: {e}\n")
        return False


def task_exists(name):
    r = subprocess.run(
        ["schtasks", "/Query", "/TN", name, "/FO", "CSV"],
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode == 0


def install():
    print("=" * 60)
    print("安装单位信息管理系统 开机自启任务")
    print("=" * 60)
    # 先删除旧任务（存在就重建）
    for t in (TASK_NAME, WATCHDOG_TASK):
        if task_exists(t):
            print(f"\n旧任务 [{t}] 已存在，先删除...")
            run(["schtasks", "/Delete", "/TN", t, "/F"])
            time.sleep(0.5)

    # 任务1：主服务启动（开机触发 + 1分钟后重试确保环境就绪）
    print("\n--- 创建主服务启动任务 ---")
    ok1 = run([
        "schtasks", "/Create", "/SC", "ONSTART", "/TN", TASK_NAME,
        "/TR", f'cmd /c ""{LAUNCHER_BAT}""',
        "/RL", "HIGHEST", "/F",
    ])
    # 任务2：watchdog守护进程（开机触发）
    print("\n--- 创建 Watchdog 守护任务 ---")
    ok2 = run([
        "schtasks", "/Create", "/SC", "ONSTART", "/TN", WATCHDOG_TASK,
        "/TR", f'cmd /c ""{WATCHDOG_BAT}""',
        "/RL", "HIGHEST", "/F",
    ])

    print()
    if ok1 and ok2:
        print("✅ 安装成功！")
        print(f"    - [{TASK_NAME}] 开机自动启动Web服务（http://0.0.0.0:8000）")
        print(f"    - [{WATCHDOG_TASK}] 开机自动启动进程守护（挂掉自动重启）")
        print()
        print("👉 现在立即启动主服务运行一次（无需重启机器）：")
        r = subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME],
                           capture_output=True, text=True, timeout=30)
        print("   ", (r.stdout or r.stderr).strip().replace("\n", " | "))
        r = subprocess.run(["schtasks", "/Run", "/TN", WATCHDOG_TASK],
                           capture_output=True, text=True, timeout=30)
        print("   ", (r.stdout or r.stderr).strip().replace("\n", " | "))
        print()
        print("✅ 开机自启 + 进程守护都安装好了，下次重启服务器也不会断。")
    else:
        print("❌ 部分任务创建失败，请查看上方的错误输出。")
    return (ok1 and ok2)


def uninstall():
    print("=" * 60)
    print("卸载单位信息管理系统 开机自启任务")
    print("=" * 60)
    for t in (TASK_NAME, WATCHDOG_TASK):
        if task_exists(t):
            print(f"\n删除任务 [{t}]...")
            run(["schtasks", "/Delete", "/TN", t, "/F"])
        else:
            print(f"\n[{t}] 不存在，跳过")
    print("\n✅ 卸载完成（仅删除了开机自启任务，不会影响任何数据和代码）。")
    return True


def status():
    print("=" * 60)
    print("当前系统服务状态")
    print("=" * 60)
    for t in (TASK_NAME, WATCHDOG_TASK):
        if task_exists(t):
            print(f"\n任务 [{t}] — 已安装")
            run(["schtasks", "/Query", "/TN", t, "/V", "/FO", "LIST"])
        else:
            print(f"\n任务 [{t}] — 未安装")
    # 端口状态
    print("\n--- 端口 8000 状态 ---")
    try:
        out = subprocess.check_output(["netstat", "-ano"], shell=True).decode("gbk", errors="ignore")
        found = False
        for line in out.splitlines():
            if ":8000" in line and "LISTENING" in line:
                print("    ", line.strip())
                found = True
        if not found:
            print("     未监听，服务未启动")
    except Exception as e:
        print(f"    查询失败: {e}")
    return True


def main():
    parser = argparse.ArgumentParser(description="单位信息管理系统 - Windows自启服务安装器")
    parser.add_argument("action", nargs="?", default="install",
                        choices=["install", "uninstall", "status"],
                        help="install=安装自启  uninstall=卸载  status=查看状态")
    args = parser.parse_args()

    print()
    if not is_admin():
        print("⚠️  此脚本需要【管理员权限】才能操作Windows计划任务。")
        print("    正在尝试自动以管理员身份重新启动...")
        ok = elevate_self()
        if not ok:
            print("❌ 自动提权失败，请右键点击脚本 -> 【以管理员身份运行】")
        # 无论成功与否，都退出让新的实例跑
        input("\n按回车键退出...")
        sys.exit(0)

    if args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    else:
        status()

    try:
        input("\n按回车键退出...")
    except Exception:
        pass


if __name__ == "__main__":
    import time  # noqa
    main()
