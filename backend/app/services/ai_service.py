"""AI 服务：PyTorch 本地大模型 + RAG 知识库
支持优雅降级：大模型不可用时回退到知识库检索模式
v2: 替换 Embedding 为 BGE 中文优化模型 + 语义分块 + 查询改写
"""
import os
import json
import hashlib
import re
import time
from pathlib import Path
from typing import Optional, List

import requests
import numpy as np

# ============ 本地大模型配置 ============
# 使用 PyTorch + transformers 直接加载模型（GPU 加速）
# 绕过 Ollama 的 CUDA 兼容性问题
LOCAL_MODEL_PATH = os.environ.get(
    "LOCAL_MODEL_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "storage" / "models" / "Qwen2-0.5B-Instruct")
)

# Ollama 配置（保留作为备选）
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

KB_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "knowledge_base"
KB_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = KB_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# 已入库文件名记录（避免重复入库）
_KB_INDEX_FILE = KB_DIR / "kb_index.json"

# ============ 本地大模型（PyTorch + transformers）============
_local_model = None
_local_tokenizer = None
_local_device = None


def _load_local_model():
    """懒加载本地大模型（PyTorch + GPU）"""
    global _local_model, _local_tokenizer, _local_device

    if _local_model is not None:
        return True

    model_path = LOCAL_MODEL_PATH
    if not os.path.exists(model_path):
        # 检查 model.safetensors 是否存在
        print(f"[AI] 本地模型路径不存在: {model_path}")
        return False

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        _local_device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[AI] 加载本地模型: {model_path}")
        print(f"[AI] 设备: {_local_device}")

        start = time.time()
        _local_tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True
        )
        _local_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if _local_device == "cuda" else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=False,
        )
        _local_model = _local_model.to(_local_device)
        load_time = time.time() - start
        print(f"[AI] 模型加载完成 ({load_time:.1f}s)")

        if _local_device == "cuda":
            mem = torch.cuda.memory_allocated() / 1024 / 1024
            print(f"[AI] GPU 显存占用: {mem:.0f}MB")

        return True
    except Exception as e:
        print(f"[AI] 本地模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def local_chat(prompt: str, system_prompt: str = "") -> Optional[str]:
    """使用本地 PyTorch 模型进行对话"""
    if not _load_local_model():
        return None

    try:
        import torch

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        text = _local_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = _local_tokenizer(text, return_tensors="pt").to(_local_device)

        with torch.no_grad():
            outputs = _local_model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=_local_tokenizer.pad_token_id or _local_tokenizer.eos_token_id,
            )

        response = _local_tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return response.strip()
    except Exception as e:
        print(f"[AI] 本地模型对话失败: {e}")
        return None


def check_ollama() -> bool:
    """检查 Ollama 服务是否可用（兼容旧代码）"""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def list_ollama_models() -> list:
    """列出 Ollama 已安装的模型"""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def ollama_chat(prompt: str, system_prompt: str = "", model: str = None) -> Optional[str]:
    """调用 Ollama 进行对话（备选方案）"""
    if not check_ollama():
        return None
    model = model or DEFAULT_MODEL
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=180,
        )
        if r.status_code == 200:
            return r.json()["message"]["content"]
        elif r.status_code == 500:
            error_msg = r.json().get("error", "")
            print(f"[Ollama] 模型运行错误(500): {error_msg[:200]}")
    except Exception as e:
        print(f"[Ollama] 调用失败: {e}")
    return None


# ============ RAG 知识库 ============
# 2026-08 升级：使用 BAAI/bge-small-zh-v1.5 中文优化模型（384维）
# 本地 PyTorch 加载，编码速度 226条/秒，中文语义理解远优于 ONNX all-MiniLM-L6-v2

_vector_store = None
_bge_model = None
_bge_tokenizer = None
_bge_device = None
_bge_dim = 384
_embedding_backend = "未初始化"
BGE_MODEL_PATH = os.environ.get(
    "BGE_MODEL_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "storage" / "models" / "bge-small-zh-v1.5"),
)


class BGEEmbeddingFunction:
    """使用 BAAI/bge-small-zh-v1.5 生成中文 embeddings（384维）
    实现 ChromaDB EmbeddingFunction 接口
    """

    def name(self):
        return "bge-small-zh-v1.5"

    def __init__(self):
        _ensure_bge_loaded()

    def __call__(self, input):
        """兼容旧接口"""
        return self.embed_documents(input)

    def embed_documents(self, texts: list) -> list:
        """ChromaDB 文档嵌入接口：接收文本列表，返回 embedding 列表"""
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        return _bge_encode(texts)

    def embed_query(self, input) -> list:
        """ChromaDB 查询嵌入接口：兼容字符串和列表两种调用方式"""
        if isinstance(input, str):
            texts = [input]
        elif isinstance(input, list):
            texts = input
        else:
            texts = [str(input)]
        # 过滤空文本
        texts = [t for t in texts if t and t.strip()]
        if not texts:
            texts = ["查询"]
        return _bge_encode(texts)


def _ensure_bge_loaded():
    """懒加载 BGE 模型"""
    global _bge_model, _bge_tokenizer, _bge_device, _embedding_backend
    if _bge_model is not None:
        return True
    if not os.path.exists(BGE_MODEL_PATH):
        print(f"[AI] BGE 模型路径不存在: {BGE_MODEL_PATH}")
        _embedding_backend = "ONNX all-MiniLM-L6-v2（BGE缺失，降级）"
        return False
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
        _bge_device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[AI] 加载 BGE Embedding 模型: {BGE_MODEL_PATH} ({_bge_device})")
        _bge_tokenizer = AutoTokenizer.from_pretrained(BGE_MODEL_PATH)
        _bge_model = AutoModel.from_pretrained(BGE_MODEL_PATH)
        _bge_model = _bge_model.to(_bge_device)
        _bge_model.eval()
        _embedding_backend = f"bge-small-zh-v1.5（中文优化, {_bge_device}）"
        print(f"[AI] BGE 模型加载完成")
        return True
    except Exception as e:
        print(f"[AI] BGE 模型加载失败: {e}")
        _embedding_backend = "ONNX all-MiniLM-L6-v2（BGE加载失败，降级）"
        _bge_model = None
        return False


def _bge_encode(texts: list) -> list:
    """用 BGE 编码文本列表，返回 float32 向量列表"""
    if not _ensure_bge_loaded():
        return _fallback_onnx_encode(texts)
    try:
        import torch
        inputs = _bge_tokenizer(
            texts, padding=True, truncation=True, max_length=512,
            return_tensors="pt"
        )
        inputs = {k: v.to(_bge_device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = _bge_model(**inputs)
            # CLS token embedding + L2 归一化
            embeddings = outputs.last_hidden_state[:, 0, :]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        result = embeddings.cpu().numpy().astype(np.float32).tolist()
        return result
    except Exception as e:
        print(f"[AI] BGE 编码失败: {e}")
        return _fallback_onnx_encode(texts)


def _fallback_onnx_encode(texts: list) -> list:
    """降级：使用 ONNX all-MiniLM-L6-v2"""
    try:
        from chromadb.utils import embedding_functions
        ef = embedding_functions.ONNXMiniLM_L6_V2()
        return ef(texts)
    except Exception:
        return [[0.0] * _bge_dim] * len(texts)


def _get_vector_store():
    """懒加载 ChromaDB 向量存储（BGE 中文 Embedding + ONNX 降级）"""
    global _vector_store
    if _vector_store is None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(KB_DIR / "chromadb"))

            # 优先 BGE 中文优化 Embedding
            ef = None
            embed_dim = _bge_dim

            if _ensure_bge_loaded():
                ef = BGEEmbeddingFunction()
                print(f"[AI] 使用 BGE Embedding (bge-small-zh-v1.5, {_bge_dim}维, 中文优化)")
            else:
                # 降级 ONNX
                from chromadb.utils import embedding_functions
                ef = embedding_functions.ONNXMiniLM_L6_V2()
                embed_dim = 384
                print("[AI] 降级使用 ONNX Embedding (英文为主)")

            # 创建或获取 collection
            try:
                _vector_store = client.get_collection(
                    name="knowledge_base",
                    embedding_function=ef,
                )
                # 检查 embedding 维度是否匹配，不匹配则重建
                count = _vector_store.count()
                if count > 0:
                    try:
                        sample = _vector_store.peek(limit=1)
                        if sample and sample.get("embeddings") and len(sample["embeddings"][0]) != embed_dim:
                            print(f"[AI] embedding维度不匹配({len(sample['embeddings'][0])} vs {embed_dim})，重建知识库")
                            client.delete_collection("knowledge_base")
                            _vector_store = client.get_or_create_collection(
                                name="knowledge_base",
                                embedding_function=ef,
                            )
                    except Exception:
                        pass
            except Exception:
                _vector_store = client.get_or_create_collection(
                    name="knowledge_base",
                    embedding_function=ef,
                )

        except Exception as e:
            print(f"[AI] ChromaDB 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    return _vector_store


def add_to_knowledge_base(text: str, metadata: dict = None):
    """将文本分块后添加到知识库"""
    store = _get_vector_store()
    if not store:
        return 0

    chunks = _chunk_text(text)
    ids = []
    documents = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.md5(f"{chunk}_{i}".encode()).hexdigest()
        ids.append(doc_id)
        documents.append(chunk)
        meta = (metadata or {}).copy()
        meta["chunk_index"] = i
        metadatas.append(meta)

    if ids:
        store.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list:
    """语义分块：按标题/段落/表格行拆分，保持语义完整性
    优先级：Markdown标题 > 段落边界 > 固定长度
    """
    if not text:
        return []

    # 尝试按 Markdown 标题拆分（### / ## / # 开头的行）
    header_pattern = re.compile(r'^(#{1,4})\s+.+$', re.MULTILINE)
    headers = list(header_pattern.finditer(text))

    if headers and len(headers) >= 2:
        chunks = []
        for i, m in enumerate(headers):
            start = m.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            section = text[start:end].strip()
            # 如果某个section太长，再按段落拆分
            if len(section) > chunk_size * 2:
                chunks.extend(_split_by_paragraphs(section, chunk_size, overlap))
            elif section:
                chunks.append(section)
        # 文本开头到第一个标题之间的内容
        if headers[0].start() > 0:
            pre = text[:headers[0].start()].strip()
            if pre and len(pre) > 50:
                chunks = [pre] + chunks
        return chunks if chunks else _split_by_paragraphs(text, chunk_size, overlap)

    # 无标题：按段落拆分
    return _split_by_paragraphs(text, chunk_size, overlap)


def _split_by_paragraphs(text: str, chunk_size: int, overlap: int) -> list:
    """按段落（空行）拆分，段落过长再按句子拆分"""
    # 先按空行分段
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # 如果单段超长，按句子拆分
            if len(para) > chunk_size:
                sentence_chunks = _split_by_sentences(para, chunk_size, overlap)
                chunks.extend(sentence_chunks)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)
    return chunks


def _split_by_sentences(text: str, chunk_size: int, overlap: int) -> list:
    """按中文句号/感叹号/问号等句子边界拆分"""
    sentences = re.split(r'(?<=[。！？；\n])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) <= chunk_size:
            current = (current + sent).strip()
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    # 如果还是太长，回退到固定长度切分
    final = []
    for c in chunks:
        if len(c) <= chunk_size * 2:
            final.append(c)
        else:
            start = 0
            while start < len(c):
                end = min(start + chunk_size, len(c))
                final.append(c[start:end])
                if end >= len(c):
                    break
                start = end - overlap
    return final


def _expand_query(query: str) -> List[str]:
    """查询改写：把用户的自然语言问题扩展成多个检索关键词
    例如："帮我写一个请假审批条" → ["请假审批条", "请假审批流程", "请假申请", "请假制度", "假条模板"]
    """
    expanded = [query]

    # 规则1：去掉"帮我"、"如何"、"怎么"、"什么"等口语化前缀
    cleaned = re.sub(r'^(帮我|请|给我|我想|如何|怎么|怎样|什么是|什么叫|介绍下|介绍一下).{0,4}', '', query)
    # 去掉末尾的语气词和助词
    cleaned = re.sub(r'(呢|吗|啊|的|了|是|在|要|去).{0,3}$', '', cleaned)
    cleaned = cleaned.strip()
    if cleaned and cleaned not in expanded and len(cleaned) >= 2:
        expanded.append(cleaned)

    # 规则2：提取核心名词短语（2-4字，更精准）
    text = cleaned or query
    # 去掉疑问词、动词等，替换为空格以便分词
    text_cleaned = re.sub(r'(如何|怎么|怎样|什么|为什么|帮|给|我|想|写|做|生成|制作|画|设计|介绍|说|请|需要|想要|请问)', ' ', text)
    nouns = re.findall(r'[\u4e00-\u9fff]{2,4}', text_cleaned)
    # 去掉首尾的停用字
    stop_chars = set('是了的吗呢啊在要去不没怎么为把被让给对从向入需')
    filtered_nouns = []
    for n in nouns:
        n_clean = n
        while n_clean and n_clean[0] in stop_chars:
            n_clean = n_clean[1:]
        while n_clean and n_clean[-1] in stop_chars:
            n_clean = n_clean[:-1]
        if len(n_clean) >= 2 and n_clean not in expanded and n_clean not in filtered_nouns:
            filtered_nouns.append(n_clean)
    expanded.extend(filtered_nouns)

    # 规则3：添加同义词/相关词
    synonym_map = {
        "请假": ["请假流程", "请假制度", "请假申请", "休假"],
        "报销": ["报销流程", "报销标准", "差旅费", "费用报销"],
        "离职": ["离职流程", "离职申请", "解除合同", "辞职"],
        "入职": ["入职流程", "入职手续", "新员工", "报到"],
        "审批": ["审批流程", "审批权限", "审批节点", "审核"],
        "密码": ["密码管理", "密码过期", "密码修改", "账号安全"],
        "公章": ["公章使用", "用印流程", "盖章"],
        "考勤": ["考勤管理", "打卡", "出勤", "迟到早退"],
        "绩效": ["绩效考核", "绩效评定", "绩效奖金"],
        "调岗": ["调岗流程", "岗位调整", "人事变动"],
        "模板": ["模板", "范本", "样例", "格式"],
        "条": ["条", "表单", "申请", "模板"],
        "制度": ["制度", "规定", "办法", "规则"],
    }
    for key, syns in synonym_map.items():
        if key in query:
            for s in syns:
                if s not in expanded:
                    expanded.append(s)

    # 规则4：如果用户要"写"、"生成"、"模板"，同时加上"格式"、"范文"等词
    if any(w in query for w in ["写", "生成", "做", "模板", "格式"]):
        expanded.extend(["格式", "范文", "模板", "示例"])

    return list(dict.fromkeys(expanded))[:6]  # 去重，最多6个


def search_knowledge_base(query: str, top_k: int = 5) -> list:
    """在知识库中检索相关文档（ChromaDB 自动对 query 向量化）"""
    store = _get_vector_store()
    if not store:
        return []

    # 传入 query_texts，ChromaDB 自动用 embedding_function 编码
    results = store.query(
        query_texts=[query],
        n_results=top_k,
    )

    docs = []
    docs_list = results.get("documents", [[]])[0]
    metas_list = results.get("metadatas", [[]])[0] if results.get("metadatas") else [{}] * len(docs_list)
    dists_list = results.get("distances", [[]])[0] if results.get("distances") else [0] * len(docs_list)
    for i, doc in enumerate(docs_list):
        docs.append({
            "content": doc,
            "metadata": metas_list[i] if i < len(metas_list) else {},
            "distance": dists_list[i] if i < len(dists_list) else 0,
        })
    return docs


def rag_chat(prompt: str, system_prompt: str = "") -> dict:
    """RAG 增强对话 v2：查询改写 + 多路检索 + 结构化Prompt + 严格回答规则"""

    # 1. 查询改写：扩展成多个关键词
    query_variants = _expand_query(prompt)
    print(f"[AI] 查询改写: '{prompt}' → {query_variants}")

    # 2. 多路检索：每个变体都检索，合并去重后取 top_k
    all_results = []
    seen_ids = set()
    for variant in query_variants:
        results = search_knowledge_base(variant, top_k=4)
        for r in results:
            content_hash = hashlib.md5(r["content"].encode()).hexdigest()
            if content_hash not in seen_ids:
                seen_ids.add(content_hash)
                r["_query"] = variant
                all_results.append(r)
    # 按相似度排序取前5
    all_results.sort(key=lambda x: x.get("distance", 1))
    kb_results = all_results[:5]

    kb_context = ""
    if kb_results:
        # 结构化上下文：每条包含来源文件名、分类、内容摘要
        context_parts = []
        for i, d in enumerate(kb_results, 1):
            meta = d.get("metadata", {})
            source = meta.get("source", "未知文档")
            category = meta.get("category", "")
            dist = d.get("distance", 0)
            content = d["content"]
            # 截断过长内容，保留最相关部分
            if len(content) > 400:
                content = content[:400] + "..."
            context_parts.append(
                f"【参考{i}】来源：{source}（{category}，相似度{1-dist:.2f}）\n{content}"
            )
        kb_context = "\n\n".join(context_parts)

    # 3. 构建增强 Prompt（结构化 + 严格规则）
    if kb_context:
        enhanced_prompt = f"""以下是从本单位知识库中检索到的相关内容（按相关度排序）：

{kb_context}

---
请严格按照以下规则回答用户问题：
1. 优先依据上述知识库内容回答，引用时标注【参考X】
2. 如果知识库内容不足以完整回答，可补充通用知识，但必须区分说明
3. 如果知识库完全没有相关内容，请直接说"该问题在知识库中暂未收录，请联系相关管理人员咨询"，不要编造
4. 回答要具体、有操作性，避免空泛
5. 如果用户要求"写"、"生成"、"模板"，请输出完整可用的模板/文档格式

用户问题：{prompt}"""
    else:
        # 无知识库命中：直接告知
        enhanced_prompt = f"""请回答以下问题。如果知识库中没有相关内容，请直接告知用户。

用户问题：{prompt}"""

    # 4. 调用大模型（优先本地 PyTorch，其次 Ollama）
    answer = local_chat(enhanced_prompt, system_prompt)
    if answer:
        return {
            "answer": answer,
            "source": "local+rag-v2",
            "kb_hits": len(kb_results),
            "model": "local-pytorch-qwen2-0.5b",
            "query_variants": query_variants,
            "retrieved_sources": [d.get("metadata", {}).get("source", "") for d in kb_results],
        }

    if check_ollama():
        answer = ollama_chat(enhanced_prompt, system_prompt)
        if answer:
            return {
                "answer": answer,
                "source": "ollama+rag-v2",
                "kb_hits": len(kb_results),
                "model": DEFAULT_MODEL,
                "query_variants": query_variants,
            }

    # 5. 降级：返回知识库检索结果
    if kb_results:
        return {
            "answer": f"根据知识库检索到 {len(kb_results)} 条相关内容：\n\n" +
                      "\n---\n".join([f"【{d.get('metadata', {}).get('source', '未知')}】{d['content'][:300]}" for d in kb_results]),
            "source": "rag_only-v2",
            "kb_hits": len(kb_results),
            "model": None,
        }

    return {
        "answer": "该问题在知识库中暂未收录，请联系相关管理人员咨询。",
        "source": "fallback",
        "kb_hits": 0,
        "model": None,
    }


def ai_generate_form_fields(description: str) -> dict:
    """AI 生成表单字段（支持大模型和预设库两种模式）"""
    system = """你是一个表单设计助手。根据用户描述，生成合适的表单字段列表。
返回 JSON 格式：{"form_name": "表单名称", "fields": [{"field_label": "字段名", "field_type": "text/textarea/date/number/radio/select", "is_required": true/false, "field_options": ["选项1","选项2"]}]}
只返回 JSON，不要其他文字。"""

    # 优先本地 PyTorch 模型
    result = local_chat(description, system)
    if not result and check_ollama():
        result = ollama_chat(description, system)
        if result:
            try:
                # 尝试提取 JSON
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]
                data = json.loads(result)
                return {"source": "ollama", "data": data}

            except json.JSONDecodeError:
                pass

    return {"source": "preset", "data": None}


# ============ 知识库文档管理 ============

def _read_file_text(filepath: Path) -> Optional[str]:
    """读取文档内容，支持 .txt / .md / .docx / .xlsx / .pdf"""
    try:
        suffix = filepath.suffix.lower()
        if suffix in (".txt", ".md", ".log"):
            return filepath.read_text(encoding="utf-8", errors="replace")
        if suffix == ".docx":
            try:
                from docx import Document
            except Exception:
                return None
            doc = Document(str(filepath))
            return "\n".join([p.text for p in doc.paragraphs] +
                             ["\n".join([c.text for c in row.cells]) for table in doc.tables for row in table.rows])
        if suffix in (".xlsx", ".xls"):
            try:
                from openpyxl import load_workbook
            except Exception:
                return None
            wb = load_workbook(str(filepath), data_only=True, read_only=True)
            parts = []
            for ws in wb.worksheets:
                parts.append(f"=== Sheet: {ws.title} ===")
                for row in ws.iter_rows(values_only=True):
                    parts.append("\t".join([str(c) if c is not None else "" for c in row]))
            return "\n".join(parts)
        if suffix == ".pdf":
            # 尝试用 pypdf / PyPDF2，失败则跳过
            try:
                import pypdf
                reader = pypdf.PdfReader(str(filepath))
                return "\n".join([(page.extract_text() or "") for page in reader.pages])
            except Exception:
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(str(filepath))
                    return "\n".join([(page.extract_text() or "") for page in reader.pages])
                except Exception:
                    return None
        return None
    except Exception as e:
        print(f"[AI] 读取文件失败 {filepath.name}: {e}")
        return None


def _list_doc_files() -> list:
    """列出 DOCS_DIR 下所有支持的文档，返回 [{name, size, mtime}]"""
    exts = {".txt", ".md", ".docx", ".xlsx", ".xls", ".pdf", ".log"}
    files = []
    for p in DOCS_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            st = p.stat()
            files.append({
                "filename": p.name,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
                "category": _guess_category(p.name),
            })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


def _guess_category(filename: str) -> str:
    """根据文件名前缀大致分类"""
    mappings = [
        ("规章制度", "规章制度"),
        ("审批规范", "审批规范"),
        ("审批流程", "审批规范"),
        ("操作手册", "操作手册"),
        ("操作指南", "操作手册"),
        ("FAQ", "FAQ案例"),
        ("案例", "FAQ案例"),
        ("政策", "政策公文"),
        ("公文", "政策公文"),
        ("模板", "政策公文"),
        ("入职", "规章制度"),
        ("涉密", "涉密管理"),
        ("保密", "涉密管理"),
    ]
    for kw, cat in mappings:
        if kw in filename:
            return cat
    return "其他"


def _load_index() -> dict:
    if _KB_INDEX_FILE.exists():
        try:
            return json.loads(_KB_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_index(index: dict):
    try:
        _KB_INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[AI] 保存索引失败: {e}")


def _remove_from_vector_store_by_filename(filename: str):
    """根据文件名从向量库中移除对应 chunk"""
    store = _get_vector_store()
    if not store:
        return
    try:
        # 遍历匹配 metadata.source = filename 的条目（chromadb 支持 where）
        res = store.get(where={"source": filename})
        if res and res.get("ids"):
            store.delete(ids=res["ids"])
            print(f"[AI] 从向量库移除 {filename}: {len(res['ids'])} chunks")
    except Exception as e:
        print(f"[AI] 从向量库移除失败 {filename}: {e}")


def _ingest_one_file(filepath: Path) -> dict:
    """将单个文档入库，返回 {chunks, ok}"""
    text = _read_file_text(filepath)
    if not text:
        return {"filename": filepath.name, "chunks": 0, "ok": False, "error": "无法读取内容或格式不支持"}

    # 先移除旧的同名 chunk（避免重复）
    _remove_from_vector_store_by_filename(filepath.name)

    metadata = {
        "source": filepath.name,
        "category": _guess_category(filepath.name),
        "size": filepath.stat().st_size,
        "mtime": int(filepath.stat().st_mtime),
    }
    n = add_to_knowledge_base(text, metadata)
    print(f"[AI] 入库 {filepath.name}: {n} chunks")
    return {"filename": filepath.name, "chunks": n, "ok": True}


def list_documents() -> list:
    """列出所有文档及入库状态"""
    index = _load_index()
    files = _list_doc_files()
    for f in files:
        entry = index.get(f["filename"]) or {}
        f["indexed"] = bool(entry.get("indexed", False))
        f["chunks"] = entry.get("chunks", 0)
        f["last_indexed_at"] = entry.get("last_indexed_at", None)
        f["size_human"] = _human_size(f["size"])
        f["mtime_human"] = _format_ts(f["mtime"])
    return files


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _format_ts(ts: int) -> str:
    import datetime as _dt
    try:
        return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def build_knowledge_base(filenames: list = None, force: bool = False) -> dict:
    """将 docs 目录的文档入库（增量或全量重建）
    filenames: 指定文件名列表，None 表示全部
    force: True 强制重新入库
    """
    index = _load_index()
    target_files = [Path(DOCS_DIR / fn) for fn in filenames] if filenames else list(DOCS_DIR.iterdir())
    results = []
    total_chunks = 0
    for fp in target_files:
        if not fp.is_file():
            continue
        filename = fp.name
        need = False
        if force:
            need = True
        else:
            entry = index.get(filename)
            if not entry or not entry.get("indexed"):
                need = True
            else:
                try:
                    if fp.stat().st_mtime > (entry.get("last_mtime") or 0):
                        need = True
                except Exception:
                    need = True
        if not need:
            results.append({"filename": filename, "chunks": entry.get("chunks", 0), "ok": True, "skipped": True})
            continue
        r = _ingest_one_file(fp)
        if r["ok"]:
            total_chunks += r["chunks"]
            index[filename] = {
                "indexed": True,
                "chunks": r["chunks"],
                "last_indexed_at": int(time.time()),
                "last_mtime": fp.stat().st_mtime,
            }
        results.append(r)
    _save_index(index)
    return {"results": results, "total_chunks": total_chunks}


def delete_document(filename: str) -> dict:
    """删除文档（文件 + 向量库chunk + 索引）"""
    # 安全校验：防止 ../ 路径穿越
    safe_name = Path(filename).name
    if safe_name != filename or "/" in filename or "\\" in filename:
        return {"ok": False, "error": "非法文件名"}
    fp = DOCS_DIR / safe_name
    existed = False
    if fp.exists():
        try:
            fp.unlink()
            existed = True
        except Exception as e:
            return {"ok": False, "error": f"删除文件失败: {e}"}
    # 从向量库移除
    _remove_from_vector_store_by_filename(safe_name)
    # 更新索引
    index = _load_index()
    if safe_name in index:
        index.pop(safe_name, None)
        _save_index(index)
    return {"ok": True, "existed": existed, "filename": safe_name}


def get_kb_stats() -> dict:
    """获取知识库总体情况"""
    files = _list_doc_files()
    index = _load_index()
    indexed_count = sum(1 for f in files if index.get(f["filename"], {}).get("indexed"))
    total_chunks = sum(index.get(f["filename"], {}).get("chunks", 0) for f in files)
    total_size = sum(f["size"] for f in files)
    # 向量库实际条数
    vec_count = None
    try:
        store = _get_vector_store()
        if store:
            vec_count = store.count()
    except Exception:
        pass
    # 分类统计
    categories = {}
    for f in files:
        cat = f["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "total_docs": len(files),
        "indexed_docs": indexed_count,
        "total_chunks_in_index": total_chunks,
        "vector_store_chunks": vec_count,
        "total_size": total_size,
        "total_size_human": _human_size(total_size),
        "categories": categories,
    }
