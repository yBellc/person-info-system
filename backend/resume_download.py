"""断点续传下载（不依赖 HEAD 请求）"""
import os
import requests

url = "https://ollama.com/download/OllamaSetup.exe"
output = r"C:\Users\12408\Downloads\OllamaSetup.exe"

# 已下载大小
downloaded = os.path.getsize(output) if os.path.exists(output) else 0
print(f"已下载: {downloaded / 1024 / 1024:.1f}MB")

# 用 Range 请求获取总大小
headers = {"Range": f"bytes={downloaded}-"}
print(f"开始续传...")

try:
    with requests.get(url, headers=headers, stream=True, timeout=600) as r:
        # 从 Content-Range 获取总大小: "bytes 1038-1492/1493"
        content_range = r.headers.get('Content-Range', '')
        print(f"Content-Range: {content_range}")
        
        if '/' in content_range:
            total_size = int(content_range.split('/')[-1])
        else:
            # 如果没有 Range 支持，重新下载
            print("服务器不支持断点续传，重新下载...")
            downloaded = 0
            r = requests.get(url, stream=True, timeout=600)
            total_size = int(r.headers.get('Content-Length', 1492*1024*1024))
        
        print(f"总大小: {total_size / 1024 / 1024:.1f}MB")
        print(f"剩余: {(total_size - downloaded) / 1024 / 1024:.1f}MB")
        
        mode = "ab" if downloaded > 0 else "wb"
        with open(output, mode) as f:
            chunk_count = 0
            for chunk in r.iter_content(chunk_size=512*1024):  # 512KB chunks
                if chunk:
                    f.write(chunk)
                    chunk_count += 1
                    if chunk_count % 100 == 0:
                        current = os.path.getsize(output)
                        percent = current * 100 // total_size
                        print(f"  进度: {percent}% ({current/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB)")
        
        final_size = os.path.getsize(output)
        if final_size == total_size:
            print(f"\n✅ 下载完成! {final_size/1024/1024:.1f}MB")
        else:
            print(f"\n⚠️ 不完整: {final_size/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB")
except Exception as e:
    print(f"\n❌ 失败: {e}")
    current = os.path.getsize(output)
    print(f"当前: {current/1024/1024:.1f}MB")
