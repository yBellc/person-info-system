"""直接下载 Qwen2-0.5B-Instruct 模型文件（断点续传）"""
import os
import requests
import json

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

model_name = "Qwen/Qwen2-0.5B-Instruct"
local_dir = r"e:\工作工作\text\person-info-system\backend\storage\models\Qwen2-0.5B-Instruct"
os.makedirs(local_dir, exist_ok=True)

# 需要下载的文件列表
files = [
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "license.txt",
]

base_url = f"https://hf-mirror.com/{model_name}/resolve/main"

for fname in files:
    url = f"{base_url}/{fname}"
    output = os.path.join(local_dir, fname)
    
    # 断点续传
    downloaded = os.path.getsize(output) if os.path.exists(output) else 0
    headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}
    
    try:
        with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
            if r.status_code in (200, 206):
                content_range = r.headers.get('Content-Range', '')
                total_size = int(content_range.split('/')[-1]) if '/' in content_range else int(r.headers.get('Content-Length', 0))
                
                mode = "ab" if r.status_code == 206 else "wb"
                if r.status_code == 200:
                    downloaded = 0
                    mode = "wb"
                
                with open(output, mode) as f:
                    for chunk in r.iter_content(chunk_size=512*1024):
                        if chunk:
                            f.write(chunk)
                
                final_size = os.path.getsize(output)
                if total_size == 0 or final_size >= total_size:
                    print(f"  ✅ {fname}: {final_size/1024/1024:.1f}MB")
                else:
                    print(f"  ⚠️ {fname}: {final_size/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB")
            else:
                print(f"  ❌ {fname}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ {fname}: {e}")

print(f"\n模型文件保存在: {local_dir}")
print("✅ 下载完成")
