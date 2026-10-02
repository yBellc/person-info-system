"""下载并测试 BAAI/bge-small-zh-v1.5 中文 Embedding 模型"""
import os, time, json
import torch
from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
SAVE_DIR = os.path.join(os.path.dirname(__file__), "storage", "models", "bge-small-zh-v1.5")

print("=" * 60)
print(f"下载/加载模型: {MODEL_NAME}")
print("=" * 60)

# 1) 下载或加载缓存
t0 = time.time()
if os.path.exists(SAVE_DIR) and os.listdir(SAVE_DIR):
    print(f"从本地缓存加载: {SAVE_DIR}")
    tokenizer = AutoTokenizer.from_pretrained(SAVE_DIR)
    model = AutoModel.from_pretrained(SAVE_DIR)
else:
    print(f"从 HuggingFace 下载 (首次需要联网，约130MB)...")
    os.makedirs(SAVE_DIR, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(SAVE_DIR)
    model.save_pretrained(SAVE_DIR)
    print(f"模型已保存到: {SAVE_DIR}")

model.eval()
t1 = time.time()
print(f"模型加载完成: {t1 - t0:.1f}s")

# 2) 编码函数
def encode(texts, normalize=True):
    """将文本列表编码为向量矩阵"""
    if isinstance(texts, str):
        texts = [texts]
    inputs = tokenizer(
        texts, padding=True, truncation=True, max_length=512,
        return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(**inputs)
        # CLS token embedding（bge 推荐使用 CLS）
        embeddings = outputs.last_hidden_state[:, 0, :]
        if normalize:
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings.cpu().numpy()

# 3) 中文语义相似度测试
print("\n" + "=" * 60)
print("中文语义相似度测试")
print("=" * 60)

test_pairs = [
    # (query, doc_text, expected: similar)
    ("请假流程", "员工请假需提前申请，3天以内由部门主管审批", True),
    ("请假流程", "公司规定迟到15分钟以上视为旷工半天", False),
    ("报销标准", "一线城市住宿费标准为500元/天", True),
    ("报销标准", "员工入职需提供身份证和学历证明", False),
    ("密码过期", "密码有效期为90天，到期前系统强制修改", True),
    ("密码过期", "系统支持指纹和密码两种登录方式", False),
    ("离职流程", "员工离职需提前30天提交书面申请", True),
    ("离职流程", "员工年度体检由单位统一组织", False),
    ("公章使用", "公章使用需填写申请表并经领导审批", True),
    ("公章使用", "办公用品每月25日前报下月需求", False),
    ("谁能审批5000元", "5000元以下支出由部门主管终审，财务科付款", True),
    ("谁能审批5000元", "单位一把手负责10万元以上支出审批", False),
]

correct = 0
for q, doc, expected_sim in test_pairs:
    v_q = encode(q)
    v_d = encode(doc)
    sim = float((v_q[0] * v_d[0]).sum())  # cosine similarity (已归一化)
    # 判断：相似度 > 0.3 认为相关
    predicted = sim > 0.3
    ok = predicted == expected_sim
    if ok:
        correct += 1
    print(f"  Q: {q:<20} | 文档: {doc:<35} | 相似度={sim:.3f} | 预测={'相关' if predicted else '无关':<4} | 期望={'相关' if expected_sim else '无关':<4} | {'✓' if ok else '✗'}")

print(f"\n准确率: {correct}/{len(test_pairs)} = {correct/len(test_pairs)*100:.1f}%")

# 4) 与旧 ONNX 模型做对比
print("\n" + "=" * 60)
print("与旧 ONNX (all-MiniLM-L6-v2) 模型对比")
print("=" * 60)

try:
    from chromadb.utils import embedding_functions
    onnx_ef = embedding_functions.ONNXMiniLM_L6_V2()
    print("\nONNX 模型测试:")
    for q, doc, _ in test_pairs[:6]:
        v_q2 = onnx_ef([q])[0]
        v_d2 = onnx_ef([doc])[0]
        import numpy as np
        sim2 = float(np.dot(v_q2, v_d2) / (np.linalg.norm(v_q2) * np.linalg.norm(v_d2) + 1e-9))
        print(f"  Q: {q:<20} | 文档: {doc:<35} | 相似度={sim2:.3f}")
except Exception as e:
    print(f"ONNX 对比失败: {e}")

# 5) 编码速度测试
print("\n" + "=" * 60)
print("编码速度测试")
print("=" * 60)

test_texts = [
    "员工请假流程", "差旅费报销标准", "密码过期处理", "公章使用规定",
    "离职申请流程", "办公用品采购", "考勤管理制度", "绩效考核办法",
    "涉密信息管理", "合同审批流程",
] * 5  # 50 texts

t0 = time.time()
with torch.no_grad():
    for i in range(0, len(test_texts), 10):
        batch = test_texts[i:i+10]
        encode(batch)
t1 = time.time()
print(f"编码 {len(test_texts)} 条文本耗时: {t1-t0:.3f}s ({len(test_texts)/(t1-t0):.1f} 条/秒)")

print("\n✓ 模型测试完成")
