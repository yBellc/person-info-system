"""简历表导入路由（模块 5）

流程：上传简历表 → 解析为网格 → 前端点单元格配对 → 保存模板 → 批量提取 → 确认入库
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app import settings
from app.database import get_db
from app.core.permissions import require_admin
from app.core.idcard import validate_id_card
from app.models import (
    User, Person, ResumeTemplate, CellMapping, ListGroupMapping, OperationLog,
)
from app.schemas.resume_import import (
    CellMappingItem, ListGroupItem, SaveResumeTemplateRequest,
    ResumeTemplateOut, ExtractedPerson, ImportRequest,
)
from app.services.resume_parser import (
    parse_document_to_grids, extract_record_from_grid,
)
from app.services.person_helper import create_person_from_dict

router = APIRouter(prefix="/resume-import", tags=["简历表导入"])

ALLOWED_EXT = {".docx", ".xlsx"}


def log_op(db, user, action, detail=None, target_type=None, target_id=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
    ))


def can_access_unit(user: User, unit_id: Optional[int], db: Session = None) -> bool:
    # 统一调用 permissions.can_access_unit，支持层级
    from app.core.permissions import can_access_unit as _can_access
    return _can_access(user, unit_id, db)


# ==================== 上传预览 ====================

@router.post("/upload-preview", summary="上传简历表，返回解析后的网格供配对")
async def upload_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
):
    """上传单个简历表，后端解析为行列网格返回前端，供点击单元格配对"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .docx 和 .xlsx 文件")

    tmp_name = f"resume_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        grids = parse_document_to_grids(tmp_path, ext)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")

    if not grids:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail="未在文件中找到表格")

    return {
        "tmp_file": tmp_name,
        "file_type": ext.lstrip("."),
        "grids": [
            {
                "name": g["name"],
                "rows": g["rows"],
                "cols": g["cols"],
                "cells": g["grid"],
                "merged_cells": g.get("merged_cells", []),
            }
            for g in grids
        ],
    }


# ==================== 模板 CRUD ====================

@router.post("/templates", response_model=ResumeTemplateOut, summary="保存提取模板")
def save_template(
    req: SaveResumeTemplateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """保存字段-单元格映射配置为模板"""
    if req.is_public and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可创建公开模板")

    template = ResumeTemplate(
        name=req.name,
        file_type=req.file_type,
        table_index=req.table_index,
        is_public=req.is_public,
        creator_id=current_user.id,
        unit_id=None if req.is_public else current_user.unit_id,
    )
    db.add(template)
    db.flush()

    for i, m in enumerate(req.cell_mappings):
        db.add(CellMapping(
            template_id=template.id,
            field_name=m.field_name,
            system_field_key=m.system_field_key,
            label_row=m.label_row, label_col=m.label_col,
            value_row=m.value_row, value_col=m.value_col,
            sort=m.sort or i,
        ))

    for lg in req.list_groups:
        db.add(ListGroupMapping(
            template_id=template.id,
            group_name=lg.group_name,
            target_table=lg.target_table,
            columns=[c.model_dump() for c in lg.columns],
        ))

    log_op(db, current_user, "save_resume_template", f"保存简历模板 {req.name}",
           target_type="resume_template", target_id=template.id)
    db.commit()
    db.refresh(template)
    return _template_to_out(template)


def _template_to_out(template: ResumeTemplate) -> ResumeTemplateOut:
    return ResumeTemplateOut(
        id=template.id,
        name=template.name,
        file_type=template.file_type,
        table_index=template.table_index,
        is_public=template.is_public,
        unit_id=template.unit_id,
        created_at=template.created_at,
        cell_mappings=[
            CellMappingItem(
                field_name=m.field_name, system_field_key=m.system_field_key,
                label_row=m.label_row, label_col=m.label_col,
                value_row=m.value_row, value_col=m.value_col, sort=m.sort,
            ) for m in template.cell_mappings
        ],
        list_groups=[
            ListGroupItem(
                group_name=lg.group_name, target_table=lg.target_table,
                columns=lg.columns,
            ) for lg in template.list_groups
        ],
    )


@router.get("/templates", response_model=list[ResumeTemplateOut], summary="模板列表")
def list_templates(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_
    q = db.query(ResumeTemplate)
    if current_user.role != "super_admin":
        q = q.filter(or_(
            ResumeTemplate.is_public == True,
            ResumeTemplate.unit_id == current_user.unit_id,
        ))
    templates = q.order_by(ResumeTemplate.created_at.desc()).all()
    return [_template_to_out(t) for t in templates]


@router.delete("/templates/{template_id}", summary="删除模板")
def delete_template(
    template_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    template = db.query(ResumeTemplate).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if current_user.role != "super_admin":
        if not template.is_public and template.unit_id != current_user.unit_id:
            raise HTTPException(status_code=403, detail="无权删除")
        if template.is_public:
            raise HTTPException(status_code=403, detail="公开模板仅超管可删")
    db.delete(template)
    db.commit()
    return {"msg": "已删除"}


# ==================== 批量提取 ====================

def _build_mapping_payload(template: ResumeTemplate) -> tuple:
    """从模板记录构造提取所需的 mappings 和 list_groups"""
    cell_mappings = [
        {
            "field_name": m.field_name,
            "system_field_key": m.system_field_key,
            "label_row": m.label_row, "label_col": m.label_col,
            "value_row": m.value_row, "value_col": m.value_col,
        }
        for m in template.cell_mappings
    ]
    list_groups = [
        {
            "group_name": lg.group_name,
            "target_table": lg.target_table,
            "columns": lg.columns,
        }
        for lg in template.list_groups
    ]
    return cell_mappings, list_groups


def _check_conflict(db: Session, flat_fields: dict, current_unit_id: int) -> dict:
    """检查身份证冲突"""
    id_card = flat_fields.get("id_card")
    if id_card and validate_id_card(id_card):
        exist = db.query(Person).filter(Person.id_card == id_card).first()
        if exist:
            return {"conflict": True, "person_id": exist.id, "existing_name": exist.name}
    return {"conflict": False}


@router.post("/extract-preview", summary="用模板对单个文件试提取")
async def extract_preview(
    template_id: int = Query(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """用已存模板对单个简历表提取，返回结构化人员数据供预览"""
    template = db.query(ResumeTemplate).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .docx 和 .xlsx")

    tmp_name = f"preview_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        grids = parse_document_to_grids(tmp_path, ext)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return _extract_from_grids(grids, template, db, current_user.unit_id, file.filename)


@router.post("/batch-extract", summary="批量提取多个简历表")
async def batch_extract(
    template_id: int = Query(...),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量上传简历表，用模板提取，返回结果列表"""
    template = db.query(ResumeTemplate).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    results = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            results.append(ExtractedPerson(
                source_file=file.filename, status="failed",
                error=f"不支持的格式: {ext}",
            ).model_dump())
            continue

        tmp_name = f"batch_{uuid.uuid4().hex}{ext}"
        tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
        try:
            content = await file.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            grids = parse_document_to_grids(tmp_path, ext)
        except Exception as e:
            results.append(ExtractedPerson(
                source_file=file.filename, status="failed", error=str(e),
            ).model_dump())
            continue
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        result = _extract_from_grids(grids, template, db, current_user.unit_id, file.filename)
        results.extend(result if isinstance(result, list) else [result])

    log_op(db, current_user, "batch_extract",
           f"模板{template_id}批量提取 {len(files)} 文件", target_type="resume_template", target_id=template_id)
    db.commit()
    return results


def _extract_from_grids(grids: list, template: ResumeTemplate, db: Session, unit_id: int, filename: str) -> list:
    """从多个网格中用模板提取记录（一个文件可能含多张表/多人）"""
    cell_mappings, list_groups = _build_mapping_payload(template)
    table_index = template.table_index
    results = []

    # 优先用配置的 table_index，匹配不上则遍历所有表
    target_grids = []
    if 0 <= table_index < len(grids):
        target_grids = [grids[table_index]]
    else:
        target_grids = grids

    any_matched = False
    for grid_info in target_grids:
        record = extract_record_from_grid(grid_info["grid"], cell_mappings, list_groups)
        if record is None:
            continue
        any_matched = True
        # 冲突检查
        conflict_info = _check_conflict(db, record["flat_fields"], unit_id)
        status = "conflict" if conflict_info["conflict"] else "success"
        results.append(ExtractedPerson(
            source_file=filename,
            status=status,
            person_id=conflict_info.get("person_id"),
            error=f"身份证已存在：{conflict_info.get('existing_name')}" if conflict_info["conflict"] else None,
            flat_fields=record["flat_fields"],
            sub_tables=record["sub_tables"],
        ).model_dump())

    if not any_matched:
        results.append(ExtractedPerson(
            source_file=filename, status="failed",
            error="未匹配到目标表格（字段相似度不足）",
        ).model_dump())

    return results


# ==================== 确认入库 ====================

@router.post("/import", summary="确认入库（批量创建人员）")
def do_import(
    req: ImportRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """把确认后的人员数据批量入库"""
    unit_id = req.unit_id or current_user.unit_id
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权操作该单位")

    success, failed, skipped = [], [], []
    for i, p in enumerate(req.persons):
        if p.status == "failed":
            skipped.append({"index": i, "source": p.source_file, "reason": p.error or "失败"})
            continue
        if p.status == "conflict":
            skipped.append({"index": i, "source": p.source_file,
                            "reason": f"冲突未处理: {p.error}"})
            continue

        # 合并 flat_fields 和 sub_tables 为完整数据
        data = dict(p.flat_fields)
        for table_key, items in p.sub_tables.items():
            mapping = {
                "family": "family_members", "work": "work_records",
                "edu": "education_records", "reward": "rewards",
            }
            target = mapping.get(table_key, table_key)
            if target in ("family_members", "work_records", "education_records", "rewards"):
                data[target] = items

        person, err = create_person_from_dict(
            db, data, unit_id, current_user.id, current_user.username,
        )
        if err:
            failed.append({"index": i, "source": p.source_file, "reason": err})
        else:
            success.append({"index": i, "id": person.id, "name": person.name})

    db.commit()

    return {
        "success_count": len(success),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "success": success,
        "failed": failed,
        "skipped": skipped,
    }
