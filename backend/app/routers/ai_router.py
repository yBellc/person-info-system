"""AI 路由：智能对话、表单生成、知识库管理"""
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import get_current_user, require_role
from app.models.user import User
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI智能助手"])

ALLOWED_EXT = {".txt", ".md", ".log", ".pdf", ".docx", ".xlsx", ".xls"}

# 知识库管理允许的角色（写操作：上传/删除/重建）
KB_ADMIN_ROLES = {"super_admin", "unit_admin", "hr", "system_admin", "security_officer"}


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class GenerateFormRequest(BaseModel):
    description: str


class BuildKBRequest(BaseModel):
    filenames: Optional[List[str]] = None
    force: bool = False


# 所有登录用户可读；写操作 require_role 拦截
require_kb_admin = require_role(*KB_ADMIN_ROLES)


@router.get("/status", summary="AI服务状态")
def ai_status(current_user: User = Depends(get_current_user)):
    """AI 服务状态（本地 PyTorch 模型 + RAG 知识库）"""
    model_ok = getattr(ai_service, "_local_model", None) is not None
    try:
        kb_stats = ai_service.get_kb_stats() or {}
    except Exception:
        kb_stats = {}
    chunk_count = kb_stats.get("vector_store_chunks", 0)
    return {
        "model_available": model_ok,
        "model_name": "Qwen2-0.5B-Instruct（本地PyTorch）",
        "model_device": getattr(ai_service, "_local_device", "-") or "-",
        "embedding_model": getattr(ai_service, "_embedding_backend", "未初始化"),
        "mode": "local+rag" if chunk_count > 0 else "local",
        "kb_doc_count": kb_stats.get("total_docs", 0),
        "kb_indexed_docs": kb_stats.get("indexed_docs", 0),
        "kb_chunk_count": chunk_count,
    }


@router.post("/chat", summary="AI智能对话（RAG增强）")
def ai_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """AI 对话：先检索知识库，再调用大模型生成回答"""
    system_prompt = "你是单位人员信息管理系统的智能助手。请基于知识库内容回答关于人员管理、审批流程、系统操作、规章制度、行政财务等问题。如果问题的答案不在知识库中，请如实告知'该问题在知识库中暂未收录，请联系相关管理人员咨询'，不要编造。"
    if req.context:
        system_prompt += f"\n当前上下文：{req.context}"

    result = ai_service.rag_chat(req.message, system_prompt)
    return result


@router.post("/generate-form", summary="AI生成表单字段")
def ai_generate_form(
    req: GenerateFormRequest,
    current_user: User = Depends(get_current_user),
):
    """根据自然语言描述，AI 推荐表单字段"""
    result = ai_service.ai_generate_form_fields(req.description)
    return result


# ==================== 知识库文档管理 ====================

@router.get("/kb/stats", summary="知识库统计概览")
def kb_stats(current_user: User = Depends(get_current_user)):
    try:
        return ai_service.get_kb_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/docs", summary="知识库文档列表（含入库状态）")
def list_kb_docs(
    category: Optional[str] = Query(None, description="按分类筛选"),
    keyword: Optional[str] = Query(None, description="按文件名关键词搜索"),
    current_user: User = Depends(get_current_user),
):
    """列出 docs 目录下所有文档，包含大小、分类、入库状态、分块数等"""
    try:
        docs = ai_service.list_documents()
        if category:
            docs = [d for d in docs if d.get("category") == category]
        if keyword:
            kw = keyword.strip().lower()
            docs = [d for d in docs if kw in d["filename"].lower()]
        return {"items": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/upload", summary="上传知识库文档（管理员）")
async def upload_kb_doc(
    file: UploadFile = File(..., description="支持 txt/md/docx/xlsx/pdf（≤10MB）"),
    current_user: User = Depends(require_kb_admin),
):
    """上传文档到 docs 目录（不自动入库，需要调用 /kb/build 入库）"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"仅支持以下格式: {', '.join(sorted(ALLOWED_EXT))}")
    if not file.filename or len(file.filename) > 200:
        raise HTTPException(status_code=400, detail="文件名非法或过长")
    # 安全：禁止 ../ 穿越
    safe_name = Path(file.filename).name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
    file_path = ai_service.DOCS_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(content)
    # 记录到 kb_index（未入库）
    import time as _t, json as _j
    index_file = ai_service._KB_INDEX_FILE
    index = {}
    if index_file.exists():
        try:
            index = _j.loads(index_file.read_text(encoding="utf-8"))
        except Exception:
            index = {}
    index[safe_name] = {
        "indexed": False,
        "chunks": 0,
        "last_mtime": file_path.stat().st_mtime,
    }
    try:
        index_file.write_text(_j.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {
        "ok": True,
        "message": "文档已上传，点击【重新入库】即可生效",
        "filename": safe_name,
        "size": len(content),
    }


@router.post("/kb/build", summary="重建/增量入库知识库（管理员）")
def build_kb(
    req: Optional[BuildKBRequest] = None,
    current_user: User = Depends(require_kb_admin),
):
    """将 docs 目录的文档向量化入库
    - filenames：指定文件名数组（可空=全部）
    - force=true：强制全部重新分块（即使没改动过）
    - 默认增量模式：只入库新增/修改过的文档
    """
    try:
        filenames = None
        force = False
        if req:
            filenames = req.filenames
            force = req.force
        result = ai_service.build_knowledge_base(filenames=filenames, force=force)
        ok_count = sum(1 for r in result["results"] if r.get("ok"))
        fail_count = sum(1 for r in result["results"] if not r.get("ok") and not r.get("skipped"))
        skip_count = sum(1 for r in result["results"] if r.get("skipped"))
        return {
            "ok": True,
            "total_chunks": result["total_chunks"],
            "ok_count": ok_count,
            "fail_count": fail_count,
            "skip_count": skip_count,
            "details": result["results"],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重建知识库失败: {e}")


@router.delete("/kb/docs/{filename}", summary="删除知识库文档（管理员）")
def delete_kb_doc(
    filename: str,
    current_user: User = Depends(require_kb_admin),
):
    """删除 docs 目录下的文档，同时从向量库和索引中移除"""
    try:
        r = ai_service.delete_document(filename)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "删除失败"))
        return {
            "ok": True,
            "message": f"已删除文档: {r['filename']}" if r.get("existed") else "已清理索引",
            "filename": r.get("filename"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/search", summary="知识库检索（调试用）")
def kb_search(
    query: str = Query(..., description="检索关键词"),
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """在知识库中检索相关内容，AI对话会自动调用"""
    results = ai_service.search_knowledge_base(query, top_k)
    return {
        "query": query,
        "total": len(results),
        "results": results,
    }
