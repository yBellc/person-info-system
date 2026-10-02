"""测试 ctransformers 用英文路径加载 Qwen2"""
from ctransformers import AutoModelForCausalLM
import os
import time

model_path = r"C:\models\qwen2-0_5b.gguf"
print(f"模型路径: {model_path} ({os.path.getsize(model_path)/1024/1024:.1f}MB)")

# 尝试不同的 model_type
for model_type in ["qwen2", "llama", "qwen"]:
    print(f"\n尝试 model_type='{model_type}'...")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            model_type=model_type,
            max_new_tokens=50,
            gpu_layers=0,
        )
        print(f"   ✅ 成功! model_type='{model_type}'")
        
        # 快速测试
        response = model("<|im_start|>user\n你好，用一句话介绍自己。<|im_end|>\n<|im_start|>assistant\n", max_new_tokens=50)
        print(f"   回答: {response}")
        break
    except Exception as e:
        print(f"   ❌ 失败: {e}")
