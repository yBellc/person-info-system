# -*- coding: utf-8 -*-
"""智能表格路由：文档识别 → 创建表单 → 下发 → 填写 → 收集"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import settings
from app.database import get_db
from app.models.user import User
from app.models.person import Person, CustomFieldDefinition
from app.models.organization import Department, PersonPosition
from app.models.smart_form import SmartForm, SmartFormField, SmartFormDistribution, SmartFormTask
from app.models.workspace import TodoItem
from app.services.form_parser import parse_document
from app.services.message_center import send_message
from app.services.field_matcher import SYSTEM_FIELDS, match_field

router = APIRouter(tags=["智能表格"])

ALLOWED_EXT = {".docx", ".pdf", ".xlsx", ".xls"}


def require_role(min_role: str):
    """角色权限检查（所有登录用户均可使用智能表格）"""
    from app.core.permissions import get_current_user
    return get_current_user


def get_custom_fields_dict(db: Session) -> dict:
    fields = db.query(CustomFieldDefinition).filter(CustomFieldDefinition.is_active == True).all()
    return {f.field_key: f.display_name for f in fields}


def get_person_field_value(person: Person, field_key: str):
    """从人员档案中获取字段值"""
    if not person or not field_key:
        return None

    # 派生字段
    if field_key == "age":
        from app.core.idcard import calc_age
        return str(calc_age(person.birth_date)) if person.birth_date else None
    if field_key == "work_years":
        if person.work_start_date:
            delta = datetime.now().year - person.work_start_date.year
            return str(max(0, delta))
        return None
    if field_key == "party_years":
        if person.party_join_date:
            delta = datetime.now().year - person.party_join_date.year
            return str(max(0, delta))
        return None

    # 直接字段
    value = getattr(person, field_key, None)
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


# ===== AI 智能创建表单（必须在参数路由之前注册） =====

FORM_PRESETS = {
    "信息更新": {
        "keywords": ["信息更新", "信息采集", "信息登记", "档案更新"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "性别", "field_type": "radio", "auto_fill_key": "gender", "field_options": ["男", "女"]},
            {"field_label": "出生日期", "field_type": "date", "auto_fill_key": "birth_date"},
            {"field_label": "身份证号", "field_type": "text", "auto_fill_key": "id_card"},
            {"field_label": "手机号", "field_type": "text", "auto_fill_key": "phone", "is_required": True},
            {"field_label": "家庭住址", "field_type": "text", "auto_fill_key": "home_address"},
            {"field_label": "紧急联系人", "field_type": "text", "auto_fill_key": "emergency_contact"},
        ],
    },
    "年度考核": {
        "keywords": ["考核", "考评", "年度", "总结"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "职务", "field_type": "text", "auto_fill_key": "position"},
            {"field_label": "本年度工作总结", "field_type": "textarea", "is_required": True},
            {"field_label": "下年度工作计划", "field_type": "textarea"},
            {"field_label": "自我评价", "field_type": "textarea"},
        ],
    },
    "请假申请": {
        "keywords": ["请假", "休假", "事假", "病假"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "请假类型", "field_type": "select", "field_options": ["事假", "病假", "年假", "婚假", "产假", "调休", "其他"], "is_required": True},
            {"field_label": "开始时间", "field_type": "date", "is_required": True},
            {"field_label": "结束时间", "field_type": "date", "is_required": True},
            {"field_label": "请假事由", "field_type": "textarea", "is_required": True},
        ],
    },
    "培训登记": {
        "keywords": ["培训", "学习", "进修"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "培训名称", "field_type": "text", "is_required": True},
            {"field_label": "培训时间", "field_type": "date"},
            {"field_label": "培训地点", "field_type": "text"},
            {"field_label": "培训内容", "field_type": "textarea"},
            {"field_label": "培训心得", "field_type": "textarea"},
        ],
    },
    "健康申报": {
        "keywords": ["健康", "身体", "体检"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "性别", "field_type": "radio", "auto_fill_key": "gender", "field_options": ["男", "女"]},
            {"field_label": "年龄", "field_type": "number", "auto_fill_key": "age"},
            {"field_label": "体温", "field_type": "number", "is_required": True},
            {"field_label": "健康状况", "field_type": "select", "field_options": ["良好", "一般", "不适"], "is_required": True},
            {"field_label": "症状描述", "field_type": "textarea"},
            {"field_label": "近期行程", "field_type": "textarea"},
        ],
    },
    "出差申请": {
        "keywords": ["出差", "外勤", "公务"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "出差目的地", "field_type": "text", "is_required": True},
            {"field_label": "出差事由", "field_type": "textarea", "is_required": True},
            {"field_label": "开始时间", "field_type": "date", "is_required": True},
            {"field_label": "结束时间", "field_type": "date", "is_required": True},
            {"field_label": "预计费用", "field_type": "number"},
        ],
    },
    "加班申请": {
        "keywords": ["加班", "延时", "额外工作"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "加班日期", "field_type": "date", "is_required": True},
            {"field_label": "开始时间", "field_type": "text", "is_required": True},
            {"field_label": "结束时间", "field_type": "text", "is_required": True},
            {"field_label": "加班事由", "field_type": "textarea", "is_required": True},
        ],
    },
    "物资领用": {
        "keywords": ["物资", "领用", "物品", "办公用品"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "物品名称", "field_type": "text", "is_required": True},
            {"field_label": "规格型号", "field_type": "text"},
            {"field_label": "领用数量", "field_type": "number", "is_required": True},
            {"field_label": "用途说明", "field_type": "textarea"},
        ],
    },
    "会议登记": {
        "keywords": ["会议", "参会", "大会"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "部门", "field_type": "text", "auto_fill_key": "department"},
            {"field_label": "会议名称", "field_type": "text", "is_required": True},
            {"field_label": "会议时间", "field_type": "date", "is_required": True},
            {"field_label": "会议地点", "field_type": "text"},
            {"field_label": "会议议题", "field_type": "textarea"},
        ],
    },
    "入党材料": {
        "keywords": ["入党", "党员", "党组织"],
        "fields": [
            {"field_label": "姓名", "field_type": "text", "auto_fill_key": "name", "is_required": True},
            {"field_label": "性别", "field_type": "radio", "auto_fill_key": "gender", "field_options": ["男", "女"]},
            {"field_label": "民族", "field_type": "text", "auto_fill_key": "ethnicity"},
            {"field_label": "出生日期", "field_type": "date", "auto_fill_key": "birth_date"},
            {"field_label": "入党时间", "field_type": "date", "auto_fill_key": "party_join_date"},
            {"field_label": "党籍状态", "field_type": "select", "field_options": ["正式党员", "预备党员", "入党积极分子"]},
            {"field_label": "所在党支部", "field_type": "text"},
        ],
    },
}


class AIFormRequest(BaseModel):
    description: str
    title: Optional[str] = None


@router.post("/smart-forms/ai-recommend", summary="AI 智能推荐表单字段")
def ai_recommend_form_fields(
    req: AIFormRequest,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """根据自然语言描述，智能推荐表单字段配置"""
    desc = req.description.lower().strip()

    # 1. 匹配预设场景（支持多关键词匹配）
    matched_preset = None
    matched_key = None
    for keyword, preset in FORM_PRESETS.items():
        kw_list = preset.get("keywords", [keyword])
        for kw in kw_list:
            if kw.lower() in desc:
                matched_preset = preset["fields"]
                matched_key = keyword
                break
        if matched_preset:
            break

    # 2. 从描述中提取字段关键词
    extracted_fields = []
    for key, display in SYSTEM_FIELDS.items():
        if display in desc or key in desc:
            field_type = "text"
            field_opts = None
            if key == "gender":
                field_type = "radio"
                field_opts = ["男", "女"]
            elif key in ("marital_status", "political_status"):
                field_type = "select"
            elif key in ("birth_date", "party_join_date", "work_start_date", "join_unit_date", "graduation_date"):
                field_type = "date"
            elif key in ("age", "work_years", "party_years", "children_count"):
                field_type = "number"
            elif key == "education_level":
                field_type = "select"
                field_opts = ["中专", "高中", "大专", "本科", "硕士", "博士"]
            elif key == "degree":
                field_type = "select"
                field_opts = ["无", "学士", "硕士", "博士"]
            entry = {
                "field_label": display,
                "field_type": field_type,
                "auto_fill_key": key,
                "is_required": False,
                "source": "extracted",
            }
            if field_opts:
                entry["field_options"] = field_opts
            extracted_fields.append(entry)

    # 3. 合并去重（预设优先，用户提取补充）
    recommended = []
    seen_labels = set()
    if matched_preset:
        for f in matched_preset:
            label = f["field_label"]
            if label not in seen_labels:
                f_copy = {**f, "source": "preset"}
                recommended.append(f_copy)
                seen_labels.add(label)
    for f in extracted_fields:
        if f["field_label"] not in seen_labels:
            recommended.append(f)
            seen_labels.add(f["field_label"])

    # 4. 如果没有匹配到，返回默认信息更新字段
    if not recommended:
        recommended = [{**f, "source": "default"} for f in FORM_PRESETS["信息更新"]["fields"]]

    # 5. 推荐标题
    suggested_title = req.title
    if not suggested_title:
        if matched_key:
            suggested_title = f"{matched_key}登记表"
        else:
            suggested_title = "信息采集表"

    return {
        "recommended_fields": recommended,
        "suggested_title": suggested_title,
        "matched_preset": matched_key,
        "total_fields": len(recommended),
    }


@router.post("/smart-forms/ai-create", summary="AI 智能创建表单（一步到位）")
def ai_create_smart_form(
    req: AIFormRequest,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """根据自然语言描述，自动创建智能表格"""
    class _TmpReq:
        description = req.description
        title = req.title
    recommend_res = ai_recommend_form_fields(_TmpReq(), current_user, db)
    fields = recommend_res["recommended_fields"]
    title = recommend_res["suggested_title"]

    form = SmartForm(
        title=title,
        description=f"AI 智能创建：{req.description}",
        creator_id=current_user.id,
        unit_id=current_user.unit_id,
        source_type="ai_generated",
        preview_text=f"AI生成表单，共{len(fields)}个字段",
        status="active",
    )
    db.add(form)
    db.flush()

    for idx, f in enumerate(fields):
        db.add(SmartFormField(
            form_id=form.id,
            field_key=f.get("auto_fill_key") or f"field_{idx}",
            field_label=f["field_label"],
            field_type=f.get("field_type", "text"),
            field_options=f.get("field_options"),
            is_required=f.get("is_required", False),
            is_readonly=f.get("is_readonly", False),
            auto_fill_key=f.get("auto_fill_key"),
            default_value=f.get("default_value", ""),
            sort_order=idx,
            placeholder=f.get("placeholder", ""),
        ))

    db.commit()
    db.refresh(form)
    return _form_to_dict(form)


# ===== 1. 上传文档并智能识别 =====

@router.post("/smart-forms/recognize", summary="上传文档并智能识别为表单字段")
async def recognize_document(
    file: UploadFile = File(...),
    header_row: int = Query(1, description="Excel表头行号"),
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """上传 Word/PDF/Excel 文档，自动识别表单结构并智能匹配系统字段"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"仅支持 {', '.join(ALLOWED_EXT)} 格式")

    # 保存临时文件
    tmp_name = f"smart_form_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    # 解析文档
    try:
        custom_fields = get_custom_fields_dict(db)
        result = parse_document(tmp_path, ext.lstrip("."), header_row=header_row, custom_fields=custom_fields)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")

    result["tmp_file"] = tmp_name
    result["source_filename"] = file.filename
    return result


# ===== 2. 创建智能表格 =====

@router.post("/smart-forms/create", summary="创建智能表格")
def create_smart_form_body(
    data: dict,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """创建智能表格"""
    source_file_path = data.get("source_file_path", "")
    
    # 如果有临时文件，将其复制到持久化存储
    if data.get("tmp_file"):
        tmp_path = os.path.join(settings.UPLOAD_DIR, data["tmp_file"])
        if os.path.exists(tmp_path):
            ext = Path(data.get("source_filename", data.get("tmp_file", ""))).suffix.lower()
            persistent_name = f"form_source_{uuid.uuid4().hex}{ext}"
            persistent_path = os.path.join(settings.UPLOAD_DIR, persistent_name)
            import shutil
            shutil.copy2(tmp_path, persistent_path)
            source_file_path = persistent_name

    form = SmartForm(
        title=data["title"],
        description=data.get("description", ""),
        creator_id=current_user.id,
        unit_id=current_user.unit_id,
        source_filename=data.get("source_filename", ""),
        source_type=data.get("source_type", ""),
        source_file_path=source_file_path,
        preview_text=data.get("preview_text", "")[:2000],
        status="active",
    )
    db.add(form)
    db.flush()

    for f in data.get("fields", []):
        db.add(SmartFormField(
            form_id=form.id,
            field_key=f.get("field_key", f"field_{f.get('sort_order', 0)}"),
            field_label=f["field_label"],
            field_type=f.get("field_type", "text"),
            field_options=f.get("field_options"),
            is_required=f.get("is_required", False),
            is_readonly=f.get("is_readonly", False),
            auto_fill_key=f.get("auto_fill_key"),
            default_value=f.get("default_value", ""),
            sort_order=f.get("sort_order", 0),
            placeholder=f.get("placeholder", ""),
            source_cell_path=f.get("source_cell_path"),
        ))

    db.commit()
    db.refresh(form)
    return _form_to_dict(form)


# ===== 2.5 获取原始文件（供前端预览） =====

@router.get("/smart-forms/{form_id}/source-file", summary="获取表单的原始源文件")
def get_source_file(
    form_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """获取表单的原始Word/Excel文件，供前端渲染预览"""
    form = db.query(SmartForm).get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    
    if not form.source_file_path:
        raise HTTPException(status_code=404, detail="该表单没有源文件")
    
    file_path = os.path.join(settings.UPLOAD_DIR, form.source_file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="源文件不存在")
    
    ext = Path(form.source_file_path).suffix.lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    filename = form.source_filename or f"form_{form_id}{ext}"
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"}
    )


# ===== 3. 查询表单列表 =====

@router.get("/smart-forms", summary="我的表单列表")
def list_smart_forms(
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """获取当前用户创建的表单列表"""
    forms = db.query(SmartForm).filter(
        SmartForm.creator_id == current_user.id
    ).order_by(SmartForm.created_at.desc()).all()
    return [_form_to_dict(f) for f in forms]


# ===== 我的填写任务（必须在 {form_id} 路由之前定义）=====

@router.get("/smart-forms/my-tasks", summary="我的待填表格")
def my_tasks(
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """获取分配给当前用户的所有表格填写任务（含待填写、已提交、已退回）"""
    tasks = db.query(SmartFormTask).filter(
        SmartFormTask.user_id == current_user.id,
        SmartFormTask.status.in_(["pending", "returned", "submitted"]),
    ).order_by(SmartFormTask.assigned_at.desc()).all()

    result = []
    for t in tasks:
        form = db.query(SmartForm).get(t.form_id)
        dist = db.query(SmartFormDistribution).get(t.distribution_id)
        distributor = db.query(User).get(dist.distributor_id) if dist else None
        
        # Check source file existence
        has_source = False
        source_path = None
        if form and form.source_file_path:
            source_path = form.source_file_path
            full_path = os.path.join(settings.UPLOAD_DIR, form.source_file_path)
            has_source = os.path.exists(full_path)
        
        result.append({
            "task_id": t.id,
            "form_id": t.form_id,
            "form_title": form.title if form else "",
            "form_description": form.description if form else "",
            "distribution_title": dist.title if dist else "",
            "distributor": distributor.username if distributor else "",
            "deadline": dist.deadline.strftime("%Y-%m-%d %H:%M") if dist and dist.deadline else None,
            "status": t.status,
            "assigned_at": t.assigned_at.strftime("%Y-%m-%d %H:%M") if t.assigned_at else None,
            "submitted_at": t.submitted_at.strftime("%Y-%m-%d %H:%M") if t.submitted_at else None,
            "return_note": t.return_note,
            "has_source_file": has_source,
            "source_file_path": source_path,
            "source_type": form.source_type if form else None,
        })
    return result


@router.get("/smart-forms/tasks/{task_id}", summary="获取填写任务详情（含表单字段+自动填充数据）")
def get_task_detail(
    task_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """获取填写任务详情，包含表单字段定义和自动填充的个人数据"""
    task = db.query(SmartFormTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看")

    form = db.query(SmartForm).get(task.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")

    # 获取人员档案用于自动填充
    person = db.query(Person).get(task.person_id) if task.person_id else None
    if not person and current_user.person_id:
        person = db.query(Person).get(current_user.person_id)

    # 构建字段列表，填充自动填充值（使用直接查询避免relationship问题）
    form_fields = db.query(SmartFormField).filter(SmartFormField.form_id == form.id).order_by(SmartFormField.sort_order).all()
    fields = []
    for f in form_fields:
        field_data = {
            "id": f.id,
            "field_key": f.field_key,
            "field_label": f.field_label,
            "field_type": f.field_type,
            "field_options": f.field_options,
            "is_required": f.is_required,
            "is_readonly": f.is_readonly,
            "auto_fill_key": f.auto_fill_key,
            "placeholder": f.placeholder or f"请输入{f.field_label}",
            "sort_order": f.sort_order,
            "source_cell_path": f.source_cell_path,
            "default_value": f.default_value,
        }

        # 自动填充
        if f.auto_fill_key and person:
            field_data["auto_fill_value"] = get_person_field_value(person, f.auto_fill_key)
        else:
            field_data["auto_fill_value"] = None

        # 如果已有提交数据，显示已填写的值
        if task.response_data and f.field_key in task.response_data:
            field_data["current_value"] = task.response_data[f.field_key]
        else:
            field_data["current_value"] = field_data.get("auto_fill_value") or ""

        fields.append(field_data)

    return {
        "task_id": task.id,
        "form_id": form.id,
        "form_title": form.title,
        "form_description": form.description,
        "fields": fields,
        "status": task.status,
        "return_note": task.return_note,
    }


@router.post("/smart-forms/tasks/{task_id}/submit", summary="提交填写表格")
def submit_task(
    task_id: int,
    data: dict,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """提交填写的表格数据"""
    task = db.query(SmartFormTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    if task.status not in ("pending", "returned"):
        raise HTTPException(status_code=400, detail="任务已提交，无法重复提交")

    # 校验必填字段
    form = db.query(SmartForm).get(task.form_id)
    for f in form.fields:
        if f.is_required:
            val = data.get("response_data", {}).get(f.field_key)
            if not val or (isinstance(val, str) and not val.strip()):
                raise HTTPException(status_code=400, detail=f"必填字段「{f.field_label}」未填写")

    task.response_data = data.get("response_data", {})
    task.status = "submitted"
    task.submitted_at = datetime.utcnow()

    # 先flush让状态变更写入数据库，确保count能统计到当前任务
    db.flush()

    # 更新下发任务的已提交数
    dist = db.query(SmartFormDistribution).get(task.distribution_id)
    if dist:
        dist.submitted_count = db.query(SmartFormTask).filter(
            SmartFormTask.distribution_id == dist.id,
            SmartFormTask.status == "submitted",
        ).count()

        # 通知下发人
        db.add(TodoItem(
            user_id=dist.distributor_id,
            title=f"表格已提交: {form.title}",
            content=f"{current_user.username} 已提交表格「{form.title}」，请查看",
            category="notification",
            resource_type="smart_form",
            resource_id=dist.id,
        ))
        send_message(db, dist.distributor_id, msg_type="smart_form", title=f"{current_user.username} 已提交表格: {form.title}", content=f"请前往收集结果查看填写内容", resource_type="smart_form", resource_id=dist.id, sender_id=current_user.id, extra={"router": "/smart-forms", "tab": "my-forms"})

    db.commit()
    return {"msg": "提交成功"}


@router.post("/smart-forms/tasks/{task_id}/return", summary="退回重填")
def return_task(
    task_id: int,
    data: dict,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """退回任务让成员重新填写"""
    task = db.query(SmartFormTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    dist = db.query(SmartFormDistribution).get(task.distribution_id)
    if not dist or dist.distributor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    task.status = "returned"
    task.return_note = data.get("note", "请修改后重新提交")
    send_message(db, task.user_id, msg_type="smart_form", title=f"您的填写任务被退回: {task.form and task.form.title or '表格'}", content=f"退回原因: {task.return_note or '请修改后重新提交'}", resource_type="smart_form", resource_id=task.distribution_id, sender_id=current_user.id, extra={"router": "/smart-forms", "tab": "my-tasks"})

    # flush让状态变更生效后再重新计算已提交数
    db.flush()

    dist.submitted_count = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == dist.id,
        SmartFormTask.status == "submitted",
    ).count()

    db.commit()

    # 通知被退回人
    db.add(TodoItem(
        user_id=task.user_id,
        title=f"表格需修改: {dist.form.title}",
        content=f"退回原因: {data.get('note', '请修改后重新提交')}",
        category="approval",
        resource_type="smart_form",
        resource_id=dist.id,
        priority=2,
    ))
    db.commit()
    return {"msg": "已退回"}


@router.get("/smart-forms/{form_id}", summary="表单详情")
def get_smart_form(
    form_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    form = db.query(SmartForm).get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    return _form_to_dict(form)


@router.put("/smart-forms/{form_id}", summary="更新表单")
def update_smart_form(
    form_id: int,
    data: dict,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    form = db.query(SmartForm).get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    if form.creator_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权修改")

    if "title" in data:
        form.title = data["title"]
    if "description" in data:
        form.description = data.get("description", "")
    if "status" in data:
        form.status = data["status"]

    # 更新字段列表
    if "fields" in data:
        # 删除旧字段
        db.query(SmartFormField).filter(SmartFormField.form_id == form_id).delete()
        # 添加新字段
        for idx, f in enumerate(data["fields"]):
            db.add(SmartFormField(
                form_id=form.id,
                field_key=f.get("field_key", f"field_{idx}"),
                field_label=f["field_label"],
                field_type=f.get("field_type", "text"),
                field_options=f.get("field_options"),
                is_required=f.get("is_required", False),
                is_readonly=f.get("is_readonly", False),
                auto_fill_key=f.get("auto_fill_key"),
                default_value=f.get("default_value", ""),
                sort_order=f.get("sort_order", idx),
                placeholder=f.get("placeholder", ""),
                source_cell_path=f.get("source_cell_path"),
            ))

    db.commit()
    db.refresh(form)
    return _form_to_dict(form)


@router.delete("/smart-forms/{form_id}", summary="删除表单")
def delete_smart_form(
    form_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    form = db.query(SmartForm).get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    if form.creator_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权删除")
    db.delete(form)
    db.commit()
    return {"msg": "已删除"}


# ===== 4. 下发表单 =====

@router.post("/smart-forms/{form_id}/distribute", summary="下发表单给成员")
def distribute_form(
    form_id: int,
    data: dict,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """下发表单给指定成员（全部/按部门/按个人）"""
    form = db.query(SmartForm).get(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    if form.creator_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权下发")

    target_type = data.get("target_type", "all")
    target_ids = data.get("target_ids", [])

    # 获取目标用户列表
    target_users = _get_target_users(db, current_user, target_type, target_ids)
    if not target_users:
        raise HTTPException(status_code=400, detail="未找到目标成员")

    # 创建下发任务
    dist = SmartFormDistribution(
        form_id=form_id,
        distributor_id=current_user.id,
        title=data.get("title", form.title),
        description=data.get("description", ""),
        deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
        target_type=target_type,
        target_ids=target_ids,
        status="collecting",
        total_count=len(target_users),
        submitted_count=0,
    )
    db.add(dist)
    db.flush()

    # 为每个用户创建填写任务
    for user in target_users:
        # 查找关联的人员档案（通过 person_id 外键）
        person = db.query(Person).get(user.person_id) if user.person_id else None
        if not person:
            person = db.query(Person).filter(Person.name == user.username).first()

        task = SmartFormTask(
            distribution_id=dist.id,
            form_id=form_id,
            user_id=user.id,
            person_id=person.id if person else None,
            status="pending",
        )
        db.add(task)

        # 创建待办通知
        db.add(TodoItem(
            user_id=user.id,
            title=f"填写表格: {form.title}",
            content=f"{current_user.username} 下发给您的表格任务，请及时填写提交",
            category="approval",
            resource_type="smart_form",
            resource_id=dist.id,
            priority=1,
        ))
        send_message(db, user.id, msg_type="smart_form", title=f"您有新的填写任务: {form.title}", content=f"{current_user.username} 下发给您一个表格填写任务，请及时处理", resource_type="smart_form", resource_id=dist.id, sender_id=current_user.id, extra={"router": "/smart-forms", "tab": "my-tasks"})

    db.commit()
    db.refresh(dist)
    return {
        "id": dist.id,
        "total_count": dist.total_count,
        "msg": f"已下发给 {dist.total_count} 人",
    }


# ===== 5. 查看下发任务和收集结果 =====

@router.get("/smart-forms/{form_id}/distributions", summary="表单的下发记录列表")
def list_distributions(
    form_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    dists = db.query(SmartFormDistribution).filter(
        SmartFormDistribution.form_id == form_id
    ).order_by(SmartFormDistribution.created_at.desc()).all()
    
    # 动态计算已提交数作为兜底（修复历史数据不准的问题）
    result = []
    for d in dists:
        actual_count = db.query(SmartFormTask).filter(
            SmartFormTask.distribution_id == d.id,
            SmartFormTask.status == "submitted",
        ).count()
        d.submitted_count = actual_count  # 修正数据库中的值
        result.append(_dist_to_dict(d))
    return result


@router.get("/distributions/{dist_id}/responses", summary="查看收集结果")
def list_responses(
    dist_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """查看某次下发的所有填写结果（仅下发人或超管可查看）"""
    dist = db.query(SmartFormDistribution).get(dist_id)
    if not dist:
        raise HTTPException(status_code=404, detail="下发任务不存在")
    if dist.distributor_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权查看该收集结果")

    tasks = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == dist_id
    ).all()

    result = []
    for t in tasks:
        user = db.query(User).get(t.user_id)
        person = db.query(Person).get(t.person_id) if t.person_id else None
        result.append({
            "task_id": t.id,
            "user_id": t.user_id,
            "username": user.username if user else "",
            "person_name": person.name if person else (user.username if user else ""),
            "status": t.status,
            "response_data": t.response_data,
            "assigned_at": t.assigned_at.strftime("%Y-%m-%d %H:%M") if t.assigned_at else None,
            "submitted_at": t.submitted_at.strftime("%Y-%m-%d %H:%M") if t.submitted_at else None,
            "return_note": t.return_note,
        })

    return {
        "distribution": _dist_to_dict(dist),
        "form": _form_to_dict(dist.form),
        "responses": result,
        "total": len(result),
        "submitted": sum(1 for r in result if r["status"] == "submitted"),
        "pending": sum(1 for r in result if r["status"] == "pending"),
    }


@router.post("/distributions/{dist_id}/close", summary="关闭收集")
def close_distribution(
    dist_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """关闭收集（仅下发人或超管可关闭）"""
    dist = db.query(SmartFormDistribution).get(dist_id)
    if not dist:
        raise HTTPException(status_code=404, detail="下发任务不存在")
    if dist.distributor_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权操作")
    dist.status = "closed"
    db.commit()
    return {"msg": "已关闭收集"}


@router.post("/smart-forms/tasks/{task_id}/export-original", summary="按原模板导出单个任务的填写结果")
def export_task_original(
    task_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """将单个填写任务的结果回填到原版模板，生成一份原格式文档
       权限：任务本人、下发人、超管可导出
    """
    task = db.query(SmartFormTask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="填写任务不存在")
    
    dist = db.query(SmartFormDistribution).get(task.distribution_id)
    is_owner = (task.user_id == current_user.id)
    is_distributor = dist and dist.distributor_id == current_user.id
    is_admin = current_user.role == "super_admin"
    if not (is_owner or is_distributor or is_admin):
        raise HTTPException(status_code=403, detail="无权导出")

    # 直接查询表单，避免relationship延迟加载问题
    form = db.query(SmartForm).get(task.form_id)
    if not form or not form.source_file_path:
        raise HTTPException(status_code=400, detail="该表单没有源文件，无法按模板导出")

    source_path = os.path.join(settings.UPLOAD_DIR, form.source_file_path)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=400, detail=f"源文件不存在: {form.source_file_path}")

    ext = Path(form.source_file_path).suffix.lower()
    user = db.query(User).get(task.user_id)
    person = db.query(Person).get(task.person_id) if task.person_id else None
    name = person.name if person else (user.username if user else "未知")

    rand = uuid.uuid4().hex[:8]
    safe_title = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in form.title)
    output_name = f"task_export_{task_id}_{name}_{safe_title}_{rand}{ext}"
    output_path = os.path.join(settings.UPLOAD_DIR, output_name)

    response_data = task.response_data or {}

    # 直接查询字段列表，避免relationship延迟加载问题
    fields = db.query(SmartFormField).filter(SmartFormField.form_id == form.id).all() or []

    try:
        if ext == ".xlsx" or ext == ".xls":
            _fill_excel_template(source_path, output_path, response_data, fields)
        elif ext == ".docx":
            _fill_word_template(source_path, output_path, response_data, fields)
        else:
            import shutil
            shutil.copy2(source_path, output_path)

        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="文件生成失败")

        return {"filename": output_name, "name": f"{name}_{form.title}{ext}"}
    except HTTPException:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise
    except Exception as e:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ===== 8. 导出收集结果 =====

@router.post("/distributions/{dist_id}/export", summary="导出收集结果为Excel")
def export_responses(
    dist_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """将收集结果导出为专业格式的Excel（仅下发人或超管）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    dist = db.query(SmartFormDistribution).get(dist_id)
    if not dist:
        raise HTTPException(status_code=404, detail="下发任务不存在")
    if dist.distributor_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权导出")

    form = dist.form
    tasks = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == dist_id,
        SmartFormTask.status == "submitted",
    ).all()
    distributor = db.query(User).get(dist.distributor_id)

    wb = Workbook()
    ws = wb.active
    ws.title = form.title[:30]

    # 样式定义
    header_font = Font(bold=True, size=11)
    title_font = Font(bold=True, size=14)
    meta_font = Font(size=10)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')

    # ===== 元数据区域（前3行）=====
    ws.merge_cells('A1:J1')
    ws['A1'] = form.title
    ws['A1'].font = title_font
    ws['A1'].alignment = center_align

    ws['A2'] = f"下发任务：{dist.title}"
    ws['A2'].font = meta_font
    ws.merge_cells('A2:J2')

    meta_parts = [f"下发人：{distributor.username if distributor else ''}"]
    if dist.deadline:
        meta_parts.append(f"截止时间：{dist.deadline.strftime('%Y-%m-%d %H:%M')}")
    meta_parts.append(f"已收集：{len(tasks)} 条")
    ws['A3'] = "  |  ".join(meta_parts)
    ws['A3'].font = meta_font
    ws.merge_cells('A3:J3')

    # 空一行
    header_row_num = 5

    # ===== 表头 =====
    headers = ["序号", "姓名"]
    field_keys = []
    for f in sorted(form.fields, key=lambda x: x.sort_order):
        headers.append(f.field_label)
        field_keys.append(f.field_key)
    headers.append("提交时间")
    headers.append("状态")

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row_num, column=col_idx, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    # ===== 数据行 =====
    for idx, task in enumerate(tasks, 1):
        row_num = header_row_num + idx
        user = db.query(User).get(task.user_id)
        person = db.query(Person).get(task.person_id) if task.person_id else None
        name = person.name if person else (user.username if user else "")

        ws.cell(row=row_num, column=1, value=idx).border = thin_border
        ws.cell(row=row_num, column=1).alignment = center_align
        ws.cell(row=row_num, column=2, value=name).border = thin_border
        ws.cell(row=row_num, column=2).alignment = center_align

        for col_offset, key in enumerate(field_keys):
            val = task.response_data.get(key, "") if task.response_data else ""
            cell = ws.cell(row=row_num, column=3 + col_offset, value=str(val) if val else "")
            cell.border = thin_border
            cell.alignment = left_align

        submit_time = task.submitted_at.strftime("%Y-%m-%d %H:%M") if task.submitted_at else ""
        ws.cell(row=row_num, column=3 + len(field_keys), value=submit_time).border = thin_border
        ws.cell(row=row_num, column=3 + len(field_keys)).alignment = center_align
        ws.cell(row=row_num, column=3 + len(field_keys) + 1, value="已提交").border = thin_border
        ws.cell(row=row_num, column=3 + len(field_keys) + 1).alignment = center_align

    # ===== 设置列宽 =====
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 12
    for i in range(len(field_keys)):
        col_letter = get_column_letter(3 + i)
        ws.column_dimensions[col_letter].width = 18
    last_col = get_column_letter(3 + len(field_keys))
    ws.column_dimensions[last_col].width = 16
    ws.column_dimensions[get_column_letter(3 + len(field_keys) + 1)].width = 10

    output_name = f"smart_form_export_{dist_id}_{uuid.uuid4().hex[:8]}.xlsx"
    output_path = os.path.join(settings.UPLOAD_DIR, output_name)
    wb.save(output_path)

    return {"filename": output_name, "total": len(tasks)}


@router.post("/distributions/{dist_id}/export-original", summary="按原版模板导出每个人的文档")
def export_original_documents(
    dist_id: int,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """将收集结果回填到原版模板，每人一份原格式文档（仅下发人或超管）"""
    import zipfile
    import tempfile
    
    dist = db.query(SmartFormDistribution).get(dist_id)
    if not dist:
        raise HTTPException(status_code=404, detail="下发任务不存在")
    if dist.distributor_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权导出")
    
    # 直接查询表单，避免relationship延迟加载问题
    form = db.query(SmartForm).get(dist.form_id)
    if not form or not form.source_file_path:
        raise HTTPException(status_code=400, detail="该表单没有源文件，无法按模板导出")
    
    tasks = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == dist_id,
        SmartFormTask.status == "submitted",
    ).all()
    
    source_path = os.path.join(settings.UPLOAD_DIR, form.source_file_path)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=400, detail="源文件不存在")
    
    ext = Path(form.source_file_path).suffix.lower()
    fields = db.query(SmartFormField).filter(SmartFormField.form_id == form.id).all() or []
    
    # 创建临时目录存放生成的文档
    tmp_dir = tempfile.mkdtemp()
    generated_files = []
    
    try:
        for task in tasks:
            user = db.query(User).get(task.user_id)
            person = db.query(Person).get(task.person_id) if task.person_id else None
            name = person.name if person else (user.username if user else "未知")
            
            response_data = task.response_data or {}
            
            if ext == ".xlsx" or ext == ".xls":
                # Excel 回填
                output_path = os.path.join(tmp_dir, f"{name}_{form.title}.xlsx")
                _fill_excel_template(source_path, output_path, response_data, fields)
                generated_files.append(output_path)
            elif ext == ".docx":
                # Word 回填
                output_path = os.path.join(tmp_dir, f"{name}_{form.title}.docx")
                _fill_word_template(source_path, output_path, response_data, fields)
                generated_files.append(output_path)
            else:
                # 其他格式直接复制
                output_path = os.path.join(tmp_dir, f"{name}_{form.title}{ext}")
                import shutil
                shutil.copy2(source_path, output_path)
                generated_files.append(output_path)
        
        # 打包为 ZIP
        zip_name = f"original_export_{dist_id}_{uuid.uuid4().hex[:8]}.zip"
        zip_path = os.path.join(settings.UPLOAD_DIR, zip_name)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fpath in generated_files:
                zf.write(fpath, os.path.basename(fpath))
        
        # 清理临时文件
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        
        return {"filename": zip_name, "total": len(tasks)}
    except Exception as e:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


def _fill_excel_template(source_path, output_path, response_data, fields):
    """将填写数据回填到 Excel 模板，优先使用 source_cell_path 精确定位"""
    from openpyxl import load_workbook

    wb = load_workbook(source_path)

    # 构建字段映射: field_key -> (value, label, source_cell_path)
    field_map = {}
    for f in fields:
        val = response_data.get(f.field_key, "")
        if val:
            field_map[f.field_key] = (str(val), f.field_label, f.source_cell_path)

    # 第一轮：使用 source_cell_path 精确回填
    for field_key, (val, label, cell_path) in field_map.items():
        if not cell_path:
            continue
        try:
            # 解析 path: sheet:Sheet1,row:5,col:2
            parts = dict(p.split(':') for p in cell_path.split(','))
            sheet_name = parts.get('sheet', '')
            row_idx = int(parts.get('row', '0'))
            col_idx = int(parts.get('col', '0'))

            ws = wb[sheet_name] if sheet_name else wb.worksheets[0]
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = val
        except Exception:
            pass  # 忽略路径解析错误，交给后续策略处理

    # 第二轮：替换 {{field_key}} 占位符
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    for field_key, (val, label, _) in field_map.items():
                        placeholder = f"{{{{{field_key}}}}}"
                        if placeholder in cell.value:
                            cell.value = cell.value.replace(placeholder, val)

    # 第三轮：标签匹配 - 找到标签单元格，填入相邻空单元格
    for ws in wb.worksheets:
        rows = list(ws.iter_rows())
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                if cell.value is None:
                    continue
                cell_text = str(cell.value).strip()
                for field_key, (val, label, _) in field_map.items():
                    if cell_text == label or cell_text == label + "：" or cell_text == label + ":":
                        # 找右侧单元格
                        target_cell = None
                        if ci + 1 < len(row):
                            right = row[ci + 1]
                            if right.value is None or (isinstance(right.value, str) and right.value.strip() in ("", "：", ":")):
                                target_cell = right
                        # 找下方单元格
                        if target_cell is None and ri + 1 < len(rows):
                            if ci < len(rows[ri + 1]):
                                below = rows[ri + 1][ci]
                                if below.value is None or (isinstance(below.value, str) and below.value.strip() in ("", "：", ":")):
                                    target_cell = below
                        if target_cell:
                            target_cell.value = val
                            break

    # 第四轮：兜底 - 仍有未填入的数据，按顺序填入空单元格
    filled_keys = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value:
                    for field_key, (val, label, _) in field_map.items():
                        if str(cell.value) == val:
                            filled_keys.add(field_key)

    remaining = [(k, v[0]) for k, v in field_map.items() if k not in filled_keys]
    if remaining:
        idx = 0
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if idx >= len(remaining):
                        break
                    if cell.value is None or (isinstance(cell.value, str) and cell.value.strip() == ""):
                        cell.value = remaining[idx][1]
                        idx += 1

    wb.save(output_path)


def _fill_word_template(source_path, output_path, response_data, fields):
    """将填写数据回填到 Word 模板，优先使用 source_cell_path 精确定位"""
    import re
    from docx import Document

    doc = Document(source_path)

    # 构建字段映射: field_key -> (value, label, source_cell_path)
    field_map = {}
    for f in fields:
        val = response_data.get(f.field_key, "")
        if val:
            field_map[f.field_key] = (str(val), f.field_label, f.source_cell_path)

    # 第一轮：使用 source_cell_path 精确回填
    for field_key, (val, label, cell_path) in field_map.items():
        if not cell_path:
            continue
        try:
            parts = dict(p.split(':') for p in cell_path.split(','))
            table_idx = int(parts.get('table', '0'))
            row_idx = int(parts.get('row', '0'))
            col_idx = int(parts.get('col', '0'))

            if table_idx < len(doc.tables):
                table = doc.tables[table_idx]
                if row_idx < len(table.rows):
                    row_cells = table.rows[row_idx].cells
                    if col_idx < len(row_cells):
                        cell = row_cells[col_idx]
                        # 清空单元格并填入值
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.text = ""
                        if cell.paragraphs:
                            cell.paragraphs[0].text = val
        except Exception:
            pass  # 忽略路径解析错误，交给后续策略处理

    # 第二轮：替换段落和表格中的 {{field_key}} 占位符
    placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')

    def replace_placeholders_in_runs(paragraph):
        for run in paragraph.runs:
            if run.text and '{{' in run.text:
                run.text = placeholder_pattern.sub(
                    lambda m: field_map.get(m.group(1), ("", "", ""))[0] or m.group(0),
                    run.text
                )

    # 段落中的占位符
    for para in doc.paragraphs:
        replace_placeholders_in_runs(para)

    # 表格中的占位符
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_placeholders_in_runs(para)

    # 第三轮：标签匹配 - 在表格中找到标签单元格，填入相邻空单元格
    for table in doc.tables:
        rows = table.rows
        for ri, row in enumerate(rows):
            cells = row.cells
            for ci, cell in enumerate(cells):
                cell_text = cell.text.strip()
                if not cell_text:
                    continue
                for field_key, (val, label, _) in field_map.items():
                    if cell_text == label or cell_text == label + "：" or cell_text == label + ":":
                        # 找右侧空单元格
                        target_cell = None
                        if ci + 1 < len(cells):
                            right = cells[ci + 1]
                            if not right.text.strip() or right.text.strip() in ("：", ":"):
                                target_cell = right
                        # 找下方空单元格
                        if target_cell is None and ri + 1 < len(rows):
                            if ci < len(rows[ri + 1].cells):
                                below = rows[ri + 1].cells[ci]
                                if not below.text.strip() or below.text.strip() in ("：", ":"):
                                    target_cell = below
                        if target_cell:
                            for paragraph in target_cell.paragraphs:
                                for run in paragraph.runs:
                                    run.text = ""
                            if target_cell.paragraphs:
                                target_cell.paragraphs[0].text = val
                            break

    # 第四轮：兜底 - 按顺序填入表格中的空单元格
    filled_values = set()
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for field_key, (val, label, _) in field_map.items():
                    if cell.text.strip() == val:
                        filled_values.add(field_key)

    remaining = [(k, v[0]) for k, v in field_map.items() if k not in filled_values]
    if remaining:
        idx = 0
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if idx >= len(remaining):
                        break
                    if not cell.text.strip():
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.text = ""
                        if cell.paragraphs:
                            cell.paragraphs[0].text = remaining[idx][1]
                        idx += 1

    doc.save(output_path)


@router.get("/smart-forms/download/{filename}", summary="下载导出的表格")
def download_export_file(
    filename: str,
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """下载智能表格导出的文件（额外校验文件前缀或扩展名，防范路径穿越）"""
    from fastapi.responses import FileResponse
    
    # 基础安全：只允许 basename，防止 ../../xxx 路径穿越
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    
    # 额外安全：只允许导出格式文件
    allowed_prefixes = ("task_export_", "original_export_", "smart_form_export_", "form_source_", "form_export_", "dist_export_")
    allowed_exts = (".docx", ".xlsx", ".xls", ".zip", ".pdf")
    ext = Path(safe_name).suffix.lower()
    if not any(safe_name.startswith(p) for p in allowed_prefixes) and not safe_name.lower().endswith(allowed_exts):
        raise HTTPException(status_code=400, detail="非法文件类型")
    
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    # 确保文件真实位于 uploads 目录（防止符号链接穿越）
    real_path = os.path.realpath(file_path)
    upload_real = os.path.realpath(settings.UPLOAD_DIR)
    if not real_path.startswith(upload_real):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    media_types = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".zip": "application/zip",
        ".pdf": "application/pdf",
        ".xls": "application/vnd.ms-excel",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=safe_name,
    )


# ===== 9. 下发辅助：部门列表 / 用户搜索 =====

@router.get("/smart-forms/options/departments", summary="获取部门列表（供下发选择）")
def list_departments_for_distribution(
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """获取当前用户所在单位的部门列表（所有登录用户可用）"""
    q = db.query(Department).filter(Department.is_active == True)
    if current_user.role != "super_admin" and current_user.unit_id:
        q = q.filter(Department.unit_id == current_user.unit_id)
    depts = q.order_by(Department.level, Department.sort).all()
    return [{"id": d.id, "name": d.name, "parent_id": d.parent_id} for d in depts]


@router.get("/smart-forms/options/users", summary="搜索用户（供按个人下发）")
def search_users_for_distribution(
    q: str = Query("", description="搜索关键字（用户名/姓名）"),
    limit: int = Query(20, description="返回数量上限"),
    current_user: User = Depends(require_role("person")),
    db: Session = Depends(get_db),
):
    """搜索可下发的用户列表（排除自己，限本单位）"""
    query = db.query(User).filter(
        User.is_active == True,
        User.is_deleted == False,
        User.id != current_user.id,
    )
    if current_user.role != "super_admin" and current_user.unit_id:
        query = query.filter(User.unit_id == current_user.unit_id)

    if q.strip():
        kw = f"%{q.strip()}%"
        query = query.filter(User.username.like(kw))

    users = query.limit(limit).all()
    result = []
    for u in users:
        # 通过 person_id 外键匹配人员档案
        person = db.query(Person).get(u.person_id) if u.person_id else None
        if not person:
            person = db.query(Person).filter(Person.name == u.username).first()
        result.append({
            "id": u.id,
            "username": u.username,
            "name": person.name if person else "",
            "department": person.department if person else "",
            "position": person.position if person else "",
        })
    return result


# ===== 辅助函数 =====

def _get_target_users(db: Session, current_user: User, target_type: str, target_ids: list) -> list:
    """根据下发范围获取目标用户列表"""
    q = db.query(User).filter(User.is_active == True, User.id != current_user.id)

    # "全部成员"时不受单位限制，其他情况按单位过滤（非超管）
    if target_type != "all" and current_user.role != "super_admin":
        q = q.filter(User.unit_id == current_user.unit_id)

    if target_type == "all":
        return q.all()

    if target_type == "department" and target_ids:
        # 通过部门ID找到部门名称，再匹配人员档案
        dept_names = [row[0] for row in db.query(Department.name).filter(
            Department.id.in_(target_ids)
        ).all()]
        if dept_names:
            dept_persons = db.query(Person).filter(Person.department.in_(dept_names)).all()
            person_ids = [p.id for p in dept_persons]
            if person_ids:
                return q.filter(User.person_id.in_(person_ids)).all()
        return []

    if target_type == "individual" and target_ids:
        return q.filter(User.id.in_(target_ids)).all()

    return []


def _form_to_dict(form: SmartForm) -> dict:
    return {
        "id": form.id,
        "title": form.title,
        "description": form.description,
        "source_filename": form.source_filename,
        "source_type": form.source_type,
        "source_file_path": form.source_file_path,
        "status": form.status,
        "created_at": form.created_at.strftime("%Y-%m-%d %H:%M") if form.created_at else None,
        "fields": [
            {
                "id": f.id,
                "field_key": f.field_key,
                "field_label": f.field_label,
                "field_type": f.field_type,
                "field_options": f.field_options,
                "is_required": f.is_required,
                "is_readonly": f.is_readonly,
                "auto_fill_key": f.auto_fill_key,
                "placeholder": f.placeholder,
                "sort_order": f.sort_order,
                "source_cell_path": f.source_cell_path,
            }
            for f in sorted(form.fields, key=lambda x: x.sort_order)
        ],
        "distributions": len(form.distributions) if form.distributions else 0,
    }


def _dist_to_dict(dist: SmartFormDistribution) -> dict:
    form = dist.form
    return {
        "id": dist.id,
        "form_id": dist.form_id,
        "title": dist.title,
        "description": dist.description,
        "deadline": dist.deadline.strftime("%Y-%m-%d %H:%M") if dist.deadline else None,
        "target_type": dist.target_type,
        "status": dist.status,
        "total_count": dist.total_count,
        "submitted_count": dist.submitted_count,
        "created_at": dist.created_at.strftime("%Y-%m-%d %H:%M") if dist.created_at else None,
        "has_source_file": bool(form and form.source_file_path),
    }

