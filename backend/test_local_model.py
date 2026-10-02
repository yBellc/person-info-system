"""测试从本地路径加载 Qwen2-0.5B-Instruct 模型"""
import os
import time

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
print(f"1. PyTorch: {torch.__version__}")
print(f"   CUDA 可用: {torch.cuda.is_available()}")

import transformers
print(f"   transformers: {transformers.__version__}")

# 从本地路径加载
model_path = r"e:\工作工作\text\person-info-system\backend\storage\models\Qwen2-0.5B-Instruct"
print(f"\n2. 模型路径: {model_path}")
print(f"   文件列表:")
for f in os.listdir(model_path):
    size = os.path.getsize(os.path.join(model_path, f))
    print(f"     {f}: {size/1024/1024:.2f}MB")

# 加载模型
from transformers import AutoModelForCausalLM, AutoTokenizer

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n3. 加载模型 (设备: {device})...")

start = time.time()
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
print(f"   tokenizer 加载完成 ({time.time()-start:.1f}s)")

start = time.time()
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    trust_remote_code=True,
    low_cpu_mem_usage=False,
)
model = model.to(device)
load_time = time.time() - start
print(f"   ✅ 模型加载成功! ({load_time:.1f}s)")

# 测试对话
print("\n4. 测试对话:")
messages = [
    {"role": "system", "content": "你是人员信息管理系统的AI助手，请简洁回答。"},
    {"role": "user", "content": "你好，用一句话介绍你自己。"},
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(device)

start = time.time()
with torch.no_grad():
    outputs = model.generate(
        **inputs, max_new_tokens=100, temperature=0.7, do_sample=True,
        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
    )
elapsed = time.time() - start

response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print(f"   回答: {response}")
print(f"   耗时: {elapsed:.1f}s, 速度: {len(response)/elapsed:.1f} 字/秒")

# 测试 RAG
print("\n5. 测试 RAG 场景:")
context = """
知识库内容：
1. 员工入职流程：HR登录系统，进入人员名单，填写基本信息（姓名、性别、身份证号、学历）。
2. 账号创建：建档后系统自动生成初始账号，首次登录需修改密码。
3. 涉密分级：分为公开(0)、内部(1)、秘密(2)、机密(3)四级，用户只能查看自己密级以下的数据。
"""
question = "新员工入职需要哪些步骤？"

messages2 = [
    {"role": "system", "content": f"根据以下知识库内容回答问题。\n{context}"},
    {"role": "user", "content": question},
]
text2 = tokenizer.apply_chat_template(messages2, tokenize=False, add_generation_prompt=True)
inputs2 = tokenizer(text2, return_tensors="pt").to(device)

start = time.time()
with torch.no_grad():
    outputs2 = model.generate(
        **inputs2, max_new_tokens=200, temperature=0.7, do_sample=True,
        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
    )
elapsed2 = time.time() - start

response2 = tokenizer.decode(outputs2[0][inputs2["input_ids"].shape[1]:], skip_special_tokens=True)
print(f"   问题: {question}")
print(f"   回答: {response2}")
print(f"   耗时: {elapsed2:.1f}s, 速度: {len(response2)/elapsed2:.1f} 字/秒")

print("\n✅ 本地模型测试完成!")
