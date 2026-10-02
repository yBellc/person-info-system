"""测试 ctransformers 加载本地 GGUF 模型"""
from ctransformers import AutoModelForCausalLM
from transformers import AutoTokenizer
import time
import os

model_path = r"e:\工作工作\text\person-info-system\backend\storage\models\qwen2-0_5b-instruct-q4_k_m.gguf"
print(f"1. 加载模型: {os.path.basename(model_path)} ({os.path.getsize(model_path)/1024/1024:.1f}MB)")

# 加载模型
start = time.time()
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    model_type="qwen2",
    max_new_tokens=200,
    temperature=0.7,
    context_length=2048,
    gpu_layers=0,  # CPU only
)
load_time = time.time() - start
print(f"   ✅ 加载成功! ({load_time:.1f}s)")

# 加载 tokenizer
print("\n2. 加载 tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-0.5B-Instruct")
    print("   ✅ tokenizer 加载成功!")
except Exception as e:
    print(f"   ⚠️ tokenizer 加载失败: {e}")
    print("   使用简单格式化代替...")
    tokenizer = None

# 测试对话
print("\n3. 测试对话:")
messages = [
    {"role": "system", "content": "你是人员信息管理系统的AI助手，请简洁回答。"},
    {"role": "user", "content": "你好，用一句话介绍你自己。"},
]

if tokenizer:
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
else:
    text = f"<|im_start|>system\n{messages[0]['content']}<|im_end|>\n<|im_start|>user\n{messages[1]['content']}<|im_end|>\n<|im_start|>assistant\n"

start = time.time()
response = model(text, max_new_tokens=100)
elapsed = time.time() - start
print(f"   回答: {response}")
print(f"   耗时: {elapsed:.1f}s, 速度: {len(response)/elapsed:.1f} 字/秒")

# 测试 RAG
print("\n4. 测试 RAG 场景:")
context = """
知识库内容：
1. 员工入职流程：HR登录系统，进入人员名单，填写基本信息（姓名、性别、身份证号、学历）。
2. 账号创建：建档后系统自动生成初始账号，首次登录需修改密码。
3. 涉密分级：分为公开(0)、内部(1)、秘密(2)、机密(3)四级，用户只能查看自己密级以下的数据。
"""

question = "新员工入职需要哪些步骤？"
messages2 = [
    {"role": "system", "content": f"根据以下知识库内容回答问题。如果知识库中有相关内容，请基于知识库回答。\n{context}"},
    {"role": "user", "content": question},
]

if tokenizer:
    text2 = tokenizer.apply_chat_template(messages2, tokenize=False, add_generation_prompt=True)
else:
    text2 = f"<|im_start|>system\n{messages2[0]['content']}<|im_end|>\n<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"

start = time.time()
response2 = model(text2, max_new_tokens=200)
elapsed2 = time.time() - start
print(f"   问题: {question}")
print(f"   回答: {response2}")
print(f"   耗时: {elapsed2:.1f}s, 速度: {len(response2)/elapsed2:.1f} 字/秒")

print("\n✅ ctransformers 测试完成!")
