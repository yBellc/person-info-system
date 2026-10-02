"""下载最新版 Ollama 安装包"""
import urllib.request
import os

url = "https://ollama.com/download/OllamaSetup.exe"
output = r"C:\Users\12408\Downloads\OllamaSetup.exe"

print(f"下载: {url}")
print(f"保存到: {output}")

# 创建目录
os.makedirs(os.path.dirname(output), exist_ok=True)

# 下载
def progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100, downloaded * 100 // total_size)
        mb_down = downloaded / 1024 / 1024
        mb_total = total_size / 1024 / 1024
        if block_num % 200 == 0:
            print(f"  进度: {percent}% ({mb_down:.1f}MB / {mb_total:.1f}MB)")

try:
    urllib.request.urlretrieve(url, output, reporthook=progress)
    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"\n✅ 下载完成: {size_mb:.1f}MB")
    print(f"   路径: {output}")
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
    # 检查部分文件
    if os.path.exists(output):
        size = os.path.getsize(output)
        print(f"   部分文件: {size/1024/1024:.1f}MB")
