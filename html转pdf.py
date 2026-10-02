# -*- coding: utf-8 -*-
"""将HTML使用手册转换为PDF，保存到桌面"""
import subprocess
import shutil
import os
from pathlib import Path

html_path = Path(__file__).parent / "docs" / "员工使用手册.html"
desktop = Path.home() / "Desktop"
pdf_path = desktop / "单位内部信息管理系统-员工使用手册.pdf"

# 尝试找到 Edge 或 Chrome
browsers = [
    # Edge
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    # Chrome
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv("USERNAME", "")),
]

browser_exe = None
for path in browsers:
    if Path(path).exists():
        browser_exe = path
        break

if not browser_exe:
    print("错误：未找到 Edge 或 Chrome 浏览器，请先安装。")
    input("按回车关闭...")
    exit(1)

print(f"使用浏览器: {browser_exe}")
print(f"HTML文件: {html_path}")
print(f"输出PDF: {pdf_path}")
print("正在生成PDF，请稍候...")

# 使用无头模式生成PDF
file_url = f"file:///{str(html_path).replace(os.sep, '/')}"
cmd = [
    browser_exe,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--print-to-pdf={}".format(str(pdf_path)),
    "--print-to-pdf-no-header",
    file_url,
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

if pdf_path.exists():
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    print(f"\n生成成功！文件大小: {size_mb:.1f} MB")
    print(f"保存位置: {pdf_path}")
    # 自动打开PDF
    os.startfile(str(pdf_path))
else:
    print("生成失败！")
    print(f"错误输出: {result.stderr}")
    input("按回车关闭...")
