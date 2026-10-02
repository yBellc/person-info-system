"""从 ModelScope 下载 Qwen2-0.5B-Instruct（国内加速）"""
import os
import requests

local_dir = r"e:\工作工作\text\person-info-system\backend\storage\models\Qwen2-0.5B-Instruct"
os.makedirs(local_dir, exist_ok=True)

# ModelScope 文件 URL 模板
ms_base = "https://modelscope.cn/api/v1/models/qwen/Qwen2-0.5B-Instruct/repo?Revision=master&FilePath="

files = {
    "model.safetensors": 0,  # 最大文件，优先下载
    "config.json": 0,
    "generation_config.json": 0,
    "tokenizer.json": 0,
    "tokenizer_config.json": 0,
    "vocab.json": 0,
    "merges.txt": 0,
    "special_tokens_map.json": 0,
}

for fname in files:
    output = os.path.join(local_dir, fname)
    
    # 如果文件已完整，跳过（model.safetensors 除外，需要验证大小）
    if os.path.exists(output) and fname != "model.safetensors":
        if os.path.getsize(output) > 100:
            print(f"  ✅ {fname}: 已存在 ({os.path.getsize(output)/1024:.1f}KB)")
            continue
    
    # 断点续传
    downloaded = os.path.getsize(output) if os.path.exists(output) else 0
    headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}
    url = ms_base + fname
    
    print(f"下载 {fname} (已下载: {downloaded/1024/1024:.1f}MB)...")
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
                    chunk_count = 0
                    for chunk in r.iter_content(chunk_size=512*1024):
                        if chunk:
                            f.write(chunk)
                            chunk_count += 1
                            if chunk_count % 100 == 0:
                                current = os.path.getsize(output)
                                if total_size > 0:
                                    percent = current * 100 // total_size
                                    print(f"    {fname}: {percent}% ({current/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB)")
                                else:
                                    print(f"    {fname}: {current/1024/1024:.1f}MB")
                
                final_size = os.path.getsize(output)
                print(f"  ✅ {fname}: {final_size/1024/1024:.1f}MB")
            else:
                print(f"  ❌ {fname}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ {fname}: {e}")

print("\n✅ 下载完成")
