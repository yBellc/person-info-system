"""统计表模板路由：上传、智能匹配、保存映射、生成报表（模块 3）"""
import os
import uuid
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openpyxl import Workbook

from app import settings
from app.database import get_db
from app.core.permissions import require_admin, filter_persons_by_clearance, get_clearance_level, mask_field_value
from app.core.idcard import calc_age
from app.models import (
    User, ReportTemplate, TemplateFieldMapping, Person, Unit,
    CustomFieldDefinition, OperationLog,
)
from app.schemas.report import MappingItem, SaveMappingRequest, GenerateReportRequest, TemplateOut
from app.services.field_matcher import match_all, SYSTEM_FIELDS
from app.services.table_parser import parse_template_headers, fill_template

router = APIRouter(prefix="/reports", tags=["统计报表模板"])

ALLOWED_EXT = {".xlsx", ".xls"}


def log_op(db, user, action, detail=None, target_type=None, target_id=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
    ))


def get_custom_fields_dict(db: Session) -> dict:
    """获取自定义字段 {field_key: 显示名}"""
    fields = db.query(CustomFieldDefinition).filter(CustomFieldDefinition.is_active == True).all()
    return {f.field_key: f.display_name for f in fields}


def can_access_unit(user: User, unit_id: Optional[int], db: Session = None) -> bool:
    # 统一调用 permissions.can_access_unit，支持层级
    from app.core.permissions import can_access_unit as _can_access
    return _can_access(user, unit_id, db)


@router.post("/upload-and-match", summary="上传模板并自动匹配字段")
async def upload_and_match(
    file: UploadFile = File(...),
    header_row: int = Query(1, description="表头行号"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传 Excel 模板，返回表头和自动匹配结果（不落库，预览用）"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx/.xls 文件")

    # 保存到临时位置
    tmp_name = f"tmp_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    # 解析表头
    try:
        headers = parse_template_headers(tmp_path, header_row=header_row)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")

    # 智能匹配
    custom_fields = get_custom_fields_dict(db)
    match_results = match_all(headers, custom_fields)

    return {
        "tmp_file": tmp_name,
        "headers": headers,
        "mappings": match_results,
        "available_fields": list(match_results),  # 用于前端展示可选字段
    }


@router.post("/templates", response_model=TemplateOut, summary="保存模板及映射")
def save_template(
    req: SaveMappingRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """把上传的模板和确认后的映射关系保存"""
    # 公开模板仅超管可建
    if req.is_public and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可创建公开模板")

    # 数据库存储路径（这里 req 里没有 tmp_file，简化：复用已上传文件名）
    # 实际文件名从请求体扩展字段取，简化为 name + 时间戳
    file_path = os.path.join(settings.UPLOAD_DIR, f"tpl_{uuid.uuid4().hex}.xlsx")

    template = ReportTemplate(
        name=req.name,
        file_path=file_path,
        header_row=req.header_row,
        data_start_row=req.data_start_row,
        data_start_col=req.data_start_col,
        is_public=req.is_public,
        creator_id=current_user.id,
        unit_id=None if req.is_public else current_user.unit_id,
    )
    db.add(template)
    db.flush()

    for m in req.mappings:
        db.add(TemplateFieldMapping(
            template_id=template.id,
            col_index=m.col_index,
            template_field_name=m.template_name,
            system_field_key=m.system_field_key,
            confidence=m.confidence,
            confirmed=m.confirmed,
        ))

    log_op(db, current_user, "save_template", f"保存模板 {req.name}", target_type="template", target_id=template.id)
    db.commit()
    db.refresh(template)
    return _template_to_out(template)


@router.post("/templates/{template_id}/upload-file", summary="为已保存模板补充上传 Excel 文件")
async def upload_template_file(
    template_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """单独上传模板文件，绑定到模板记录"""
    template = db.query(ReportTemplate).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx/.xls")

    save_name = f"tpl_{template_id}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    template.file_path = save_path
    db.commit()
    return {"msg": "文件已上传", "file": save_name}


def _template_to_out(template: ReportTemplate) -> TemplateOut:
    return TemplateOut(
        id=template.id,
        name=template.name,
        header_row=template.header_row,
        data_start_row=template.data_start_row,
        data_start_col=template.data_start_col,
        is_public=template.is_public,
        unit_id=template.unit_id,
        created_at=template.created_at,
        mappings=[
            MappingItem(
                col_index=m.col_index,
                template_name=m.template_field_name,
                system_field_key=m.system_field_key,
                confidence=m.confidence,
                confirmed=m.confirmed,
            ) for m in template.mappings
        ],
    )


@router.get("/templates", response_model=list[TemplateOut], summary="模板列表（按权限）")
def list_templates(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(ReportTemplate)
    if current_user.role != "super_admin":
        # 公开模板 + 本单位私有模板
        from sqlalchemy import or_
        q = q.filter(or_(
            ReportTemplate.is_public == True,
            ReportTemplate.unit_id == current_user.unit_id,
        ))
    templates = q.order_by(ReportTemplate.created_at.desc()).all()
    return [_template_to_out(t) for t in templates]


@router.delete("/templates/{template_id}", summary="删除模板")
def delete_template(
    template_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    template = db.query(ReportTemplate).get(template_id)
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


@router.post("/generate", summary="生成报表（自动填充）")
def generate_report(
    req: GenerateReportRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """根据模板映射，把人员数据填入模板生成报表"""
    template = db.query(ReportTemplate).get(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if not os.path.exists(template.file_path):
        raise HTTPException(status_code=400, detail="模板文件不存在，请重新上传 Excel")

    # 权限：非超管只能用公开模板或本单位模板
    if current_user.role != "super_admin":
        if not template.is_public and template.unit_id != current_user.unit_id:
            raise HTTPException(status_code=403, detail="无权使用该模板")

    # 取数据范围（支持层级：管理员可生成本单位或下属单位报表）
    unit_id = req.unit_id or current_user.unit_id
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权访问该单位数据")

    q = db.query(Person).filter(Person.unit_id == unit_id, Person.is_deleted == False)
    # 涉密分级过滤：低密级用户只能导出可见密级的人员
    q = filter_persons_by_clearance(q, current_user)
    persons = q.order_by(Person.id).all()

    # 加载自定义字段定义和值，供报表填充使用
    custom_defs = db.query(CustomFieldDefinition).filter(CustomFieldDefinition.is_active == True).all()
    custom_def_map = {d.field_key: d.id for d in custom_defs}
    person_ids = [p.id for p in persons]
    custom_values = {}
    if person_ids and custom_def_map:
        from app.models.person import CustomFieldValue
        cvs = db.query(CustomFieldValue).filter(
            CustomFieldValue.person_id.in_(person_ids)
        ).all()
        for cv in cvs:
            if cv.person_id not in custom_values:
                custom_values[cv.person_id] = {}
            # 反查 field_key
            for fkey, fid in custom_def_map.items():
                if fid == cv.field_id:
                    custom_values[cv.person_id][fkey] = cv.value
                    break

    # 补充派生字段、单位名和自定义字段
    unit_cache = {}
    clearance = get_clearance_level(current_user)
    for p in persons:
        p.age = calc_age(p.birth_date)
        if p.unit_id:
            if p.unit_id not in unit_cache:
                unit_cache[p.unit_id] = db.query(Unit).get(p.unit_id)
            u = unit_cache[p.unit_id]
            p.unit_name = u.name if u else None
        # 挂载自定义字段供 fill_template 读取
        p._custom_values = custom_values.get(p.id, {})
        # 涉密脱敏：对人员敏感字段打码（仅低密级用户受影响）
        if clearance < 3:
            for sensitive_field in ("id_card", "phone", "office_phone", "emergency_contact", "home_address", "spouse_name"):
                orig = getattr(p, sensitive_field, None)
                if orig:
                    setattr(p, sensitive_field, mask_field_value(orig, sensitive_field, clearance))

    mappings = [
        {"col_index": m.col_index, "system_field_key": m.system_field_key}
        for m in template.mappings if m.system_field_key
    ]

    output_name = f"report_{template.id}_{uuid.uuid4().hex}.xlsx"
    output_path = os.path.join(settings.UPLOAD_DIR, output_name)

    result = fill_template(
        template_path=template.file_path,
        output_path=output_path,
        mappings=mappings,
        persons=persons,
        header_row=template.header_row,
        data_start_row=template.data_start_row,
    )
    result["output_file"] = output_name

    log_op(db, current_user, "generate_report",
           f"生成报表 {template.name}: {result['total']}人", target_type="template", target_id=template.id)
    db.commit()
    return result


@router.get("/download/{filename}", summary="下载生成的报表")
def download_file(
    filename: str,
    current_user: User = Depends(require_admin),
):
    # 防路径穿越
    safe_name = os.path.basename(filename)
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=safe_name,
    )


# ===== AI 智能生成报表 =====

# 报表类型 → 推荐字段
REPORT_PRESETS = {
    "花名册": ["name", "gender", "age", "id_card", "department", "position", "rank", "phone", "political_status"],
    "roster": ["name", "gender", "age", "id_card", "department", "position", "rank", "phone", "political_status"],
    "人员信息": ["name", "gender", "birth_date", "id_card", "ethnicity", "native_place", "department", "position", "phone"],
    "basic": ["name", "gender", "birth_date", "id_card", "ethnicity", "native_place", "department", "position", "phone"],
    "党员": ["name", "gender", "age", "political_status", "party_join_date", "party_years", "department", "position", "phone"],
    "party": ["name", "gender", "age", "political_status", "party_join_date", "party_years", "department", "position", "phone"],
    "学历": ["name", "gender", "age", "education_level", "degree", "school", "major", "graduation_date", "department"],
    "education": ["name", "gender", "age", "education_level", "degree", "school", "major", "graduation_date", "department"],
    "通讯录": ["name", "department", "position", "phone", "office_phone", "unit_name"],
    "contact": ["name", "department", "position", "phone", "office_phone", "unit_name"],
    "年龄": ["name", "gender", "birth_date", "age", "department", "position"],
    "age": ["name", "gender", "birth_date", "age", "department", "position"],
    "职称": ["name", "gender", "age", "rank", "department", "position", "work_start_date", "work_years"],
    "rank": ["name", "gender", "age", "rank", "department", "position", "work_start_date", "work_years"],
    "新入职": ["name", "gender", "birth_date", "id_card", "department", "position", "join_unit_date", "phone", "education_level"],
    "new": ["name", "gender", "birth_date", "id_card", "department", "position", "join_unit_date", "phone", "education_level"],
    "退休": ["name", "gender", "birth_date", "age", "department", "position", "work_start_date", "work_years"],
    "retire": ["name", "gender", "birth_date", "age", "department", "position", "work_start_date", "work_years"],
}


class AIGenerateRequest(BaseModel):
    description: str
    template_name: Optional[str] = None
    unit_id: Optional[int] = None
    is_public: bool = False


@router.post("/ai-recommend-fields", summary="AI 智能推荐报表字段")
def ai_recommend_fields(
    req: AIGenerateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """根据自然语言描述，智能推荐报表字段"""
    desc = req.description.lower().strip()

    # 1. 匹配预设报表类型
    matched_preset = None
    for keyword, fields in REPORT_PRESETS.items():
        if keyword in desc:
            matched_preset = fields
            break

    # 2. 从描述中提取字段关键词
    extracted_fields = []
    for key, display in SYSTEM_FIELDS.items():
        if display in desc or key in desc:
            extracted_fields.append(key)

    # 3. 合并去重
    recommended = []
    seen = set()
    if matched_preset:
        for f in matched_preset:
            if f not in seen:
                recommended.append(f)
                seen.add(f)
    for f in extracted_fields:
        if f not in seen:
            recommended.append(f)
            seen.add(f)

    # 4. 如果没有匹配到任何字段，返回默认花名册字段
    if not recommended:
        recommended = REPORT_PRESETS["花名册"]

    # 5. 构建字段详情
    field_details = []
    for key in recommended:
        field_details.append({
            "field_key": key,
            "field_label": SYSTEM_FIELDS.get(key, key),
            "in_preset": matched_preset is not None and key in matched_preset,
            "extracted_from_desc": key in extracted_fields,
        })

    # 6. 智能推荐模板名称
    suggested_name = req.template_name
    if not suggested_name:
        if matched_preset:
            # 找到匹配的中文关键词
            for keyword in REPORT_PRESETS:
                if keyword in desc and not keyword.isascii():
                    suggested_name = f"{keyword}报表"
                    break
        if not suggested_name:
            suggested_name = "自定义报表"

    return {
        "recommended_fields": field_details,
        "suggested_name": suggested_name,
        "matched_preset": matched_preset is not None,
        "total_fields": len(field_details),
    }


@router.post("/ai-generate", summary="AI 智能生成报表（一步到位）")
def ai_generate_report(
    req: AIGenerateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """根据自然语言描述，自动创建模板并生成报表 Excel"""
    desc = req.description.lower().strip()

    # 1. 智能推荐字段
    recommend_res = ai_recommend_fields(req, current_user, db)
    field_keys = [f["field_key"] for f in recommend_res["recommended_fields"]]
    field_labels = [f["field_label"] for f in recommend_res["recommended_fields"]]
    template_name = recommend_res["suggested_name"]

    # 2. 创建 Excel 模板文件
    wb = Workbook()
    ws = wb.active
    ws.title = template_name[:31] if template_name else "报表"

    # 写入表头
    for col_idx, label in enumerate(field_labels, 1):
        ws.cell(row=1, column=col_idx, value=label)

    # 3. 获取人员数据并填充
    unit_id = req.unit_id or current_user.unit_id
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权访问该单位数据")

    q = db.query(Person).filter(Person.unit_id == unit_id, Person.is_deleted == False)
    # 涉密分级过滤：低密级用户只能导出可见密级的人员
    q = filter_persons_by_clearance(q, current_user)
    persons = q.order_by(Person.id).all()

    # 补充派生字段
    for p in persons:
        p.age = calc_age(p.birth_date)
        if p.unit_id:
            u = db.query(Unit).get(p.unit_id)
            p.unit_name = u.name if u else None

    # 填充数据行（含涉密脱敏）
    clearance = get_clearance_level(current_user)
    filled_cells = 0
    missing_cells = 0
    for row_idx, person in enumerate(persons, 2):
        for col_idx, key in enumerate(field_keys, 1):
            value = _get_person_value(person, key)
            # 涉密脱敏：根据用户密级对敏感字段打码
            value = mask_field_value(value, key, clearance)
            if value is not None and value != "":
                ws.cell(row=row_idx, column=col_idx, value=str(value))
                filled_cells += 1
            else:
                missing_cells += 1

    # 4. 保存文件
    output_name = f"ai_report_{uuid.uuid4().hex}.xlsx"
    output_path = os.path.join(settings.UPLOAD_DIR, output_name)
    wb.save(output_path)

    # 5. 保存模板到数据库
    file_path = os.path.join(settings.UPLOAD_DIR, f"tpl_{uuid.uuid4().hex}.xlsx")
    wb.save(file_path)

    template = ReportTemplate(
        name=template_name,
        file_path=file_path,
        header_row=1,
        data_start_row=2,
        is_public=req.is_public and current_user.role == "super_admin",
        creator_id=current_user.id,
        unit_id=None if req.is_public else current_user.unit_id,
    )
    db.add(template)
    db.flush()

    for col_idx, key in enumerate(field_keys):
        db.add(TemplateFieldMapping(
            template_id=template.id,
            col_index=col_idx,
            template_field_name=SYSTEM_FIELDS.get(key, key),
            system_field_key=key,
            confidence=1.0,
            confirmed=True,
        ))

    log_op(db, current_user, "ai_generate_report",
           f"AI生成报表「{template_name}」: {len(persons)}人, {len(field_keys)}个字段",
           target_type="template", target_id=template.id)
    db.commit()

    return {
        "output_file": output_name,
        "template_id": template.id,
        "template_name": template_name,
        "total": len(persons),
        "filled_cells": filled_cells,
        "missing_cells": missing_cells,
        "field_count": len(field_keys),
        "fields": field_labels,
    }


def _get_person_value(person: Person, field_key: str):
    """从人员档案获取字段值"""
    # 派生字段
    if field_key == "age":
        return str(person.age) if hasattr(person, "age") and person.age else None
    if field_key == "work_years":
        if person.work_start_date:
            from datetime import datetime
            return str(max(0, datetime.now().year - person.work_start_date.year))
        return None
    if field_key == "party_years":
        if person.party_join_date:
            from datetime import datetime
            return str(max(0, datetime.now().year - person.party_join_date.year))
        return None
    if field_key == "unit_name":
        return getattr(person, "unit_name", None)

    # 直接字段
    value = getattr(person, field_key, None)
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value) if value else None
