"""下载 Qwen2-0.5B-Instruct GGUF 模型"""
import os
import requests

# 尝试多个下载源
urls = [
    ("HuggingFace", "https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_k_m.gguf"),
    ("HF Mirror", "https://hf-mirror.com/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_k_m.gguf"),
]

output_dir = r"e:\工作工作\text\person-info-system\backend\storage\models"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "qwen2-0_5b-instruct-q4_k_m.gguf")

# 断点续传
downloaded = os.path.getsize(output_path) if os.path.exists(output_path) else 0
if downloaded > 0:
    print(f"已有下载: {downloaded / 1024 / 1024:.1f}MB")

for name, url in urls:
    print(f"\n尝试下载源: {name}")
    print(f"URL: {url}")
    
    headers = {}
    if downloaded > 0:
        headers["Range"] = f"bytes={downloaded}-"
    
    try:
        with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
            if r.status_code in (200, 206):
                # 获取总大小
                content_range = r.headers.get('Content-Range', '')
                if '/' in content_range:
                    total_size = int(content_range.split('/')[-1])
                else:
                    total_size = int(r.headers.get('Content-Length', 0))
                
                print(f"总大小: {total_size / 1024 / 1024:.1f}MB")
                
                mode = "ab" if downloaded > 0 and r.status_code == 206 else "wb"
                if r.status_code == 200:
                    downloaded = 0
                    mode = "wb"
                
                with open(output_path, mode) as f:
                    chunk_count = 0
                    for chunk in r.iter_content(chunk_size=512*1024):
                        if chunk:
                            f.write(chunk)
                            chunk_count += 1
                            if chunk_count % 100 == 0:
                                current = os.path.getsize(output_path)
                                percent = current * 100 // total_size if total_size > 0 else 0
                                print(f"  进度: {percent}% ({current/1024/1024:.1f}MB)")
                
                final_size = os.path.getsize(output_path)
                if total_size == 0 or final_size >= total_size:
                    print(f"\n✅ 下载完成! {final_size/1024/1024:.1f}MB")
                    print(f"   路径: {output_path}")
                    exit(0)
                else:
                    print(f"\n⚠️ 不完整: {final_size/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB")
                    downloaded = final_size
            else:
                print(f"   HTTP {r.status_code}")
    except Exception as e:
        print(f"   失败: {e}")
        if os.path.exists(output_path):
            downloaded = os.path.getsize(output_path)
            print(f"   已下载: {downloaded/1024/1024:.1f}MB")

print("\n❌ 所有下载源都失败")
