"""智能简历识别路由

提供：
1. POST /resume-smart/parse - 单个简历智能解析
2. POST /resume-smart/batch-parse - 批量简历智能解析
3. POST /resume-smart/apply-to-person/{person_id} - 把识别结果应用到人员档案
4. POST /resume-smart/create-with-account - 从简历创建人员档案+账号（人事用）
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app import settings
from app.database import get_db
from app.core.permissions import get_current_user, require_admin, can_access_unit
from app.core.idcard import validate_id_card, parse_id_card, calc_age, calc_years
from app.core.security import hash_password
from app.models import (
    User, Person, FamilyMember, EducationRecord, WorkRecord, Unit, OperationLog,
)
from app.services.smart_resume import smart_parse_resume

router = APIRouter(prefix="/resume-smart", tags=["智能简历识别"])

ALLOWED_EXT = {".docx", ".xlsx"}


def log_op(db, user, action, detail=None, target_type=None, target_id=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
    ))


# ==================== 单个简历解析 ====================

@router.post("/parse", summary="智能解析单个简历")
async def smart_parse(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传单个简历文件，自动识别返回结构化字段

    支持 .docx 和 .xlsx 格式，无需预先配置模板。
    返回识别到的扁平字段（姓名、身份证、学历等）和列表字段（家庭成员、教育经历等）。
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 .docx 和 .xlsx 文件")

    tmp_name = f"smart_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        result = smart_parse_resume(tmp_path, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 统计识别情况
    flat_count = len(result["flat_fields"])
    sub_count = sum(len(items) for items in result["sub_tables"].values())

    return {
        "filename": file.filename,
        "flat_fields": result["flat_fields"],
        "sub_tables": result["sub_tables"],
        "raw_text": result["raw_text"][:1000],  # 只返回前1000字供预览
        "stats": {
            "flat_field_count": flat_count,
            "sub_table_rows": sub_count,
            "grids_count": result["grids_count"],
        },
    }


# ==================== 批量简历解析 ====================

@router.post("/batch-parse", summary="批量智能解析简历")
async def batch_smart_parse(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_admin),
):
    """批量上传简历文件，自动识别返回每个文件的结构化字段

    每个文件独立解析，返回结果列表。
    """
    results = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": f"不支持的格式: {ext}",
                "flat_fields": {},
                "sub_tables": {},
            })
            continue

        tmp_name = f"batch_smart_{uuid.uuid4().hex}{ext}"
        tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
        try:
            content = await file.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            result = smart_parse_resume(tmp_path, ext)
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e),
                "flat_fields": {},
                "sub_tables": {},
            })
            continue
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # 检查是否识别到关键字段
        flat = result["flat_fields"]
        has_name = bool(flat.get("name"))
        has_idcard = bool(flat.get("id_card"))

        if not has_name and not has_idcard:
            status = "warning"
        else:
            status = "success"

        results.append({
            "filename": file.filename,
            "status": status,
            "error": None if status == "success" else "未识别到姓名或身份证",
            "flat_fields": flat,
            "sub_tables": result["sub_tables"],
            "stats": {
                "flat_field_count": len(flat),
                "sub_table_rows": sum(len(items) for items in result["sub_tables"].values()),
            },
        })

    return results


# ==================== 应用到现有人员档案 ====================

@router.post("/apply-to-person/{person_id}", summary="把简历识别结果应用到人员档案")
def apply_to_person(
    person_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """把智能识别的简历字段应用到指定人员档案

    - 只更新提供的字段，不覆盖未提供的字段
    - 普通员工只能更新自己的档案，且不能改管理员专属字段
    - 管理员可更新本单位人员档案
    - 子表（家庭成员/教育/工作）按追加模式添加
    """
    person = db.query(Person).filter(Person.id == person_id, Person.is_deleted == False).first()
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")

    # 权限校验
    is_own = (current_user.role == "person" and current_user.person_id == person_id)
    is_admin = current_user.role in ("unit_admin", "super_admin")
    if not is_own and not is_admin:
        raise HTTPException(status_code=403, detail="无权修改")
    if current_user.role == "unit_admin" and not can_access_unit(current_user, person.unit_id, db):
        raise HTTPException(status_code=403, detail="无权修改外单位人员")

    flat_fields = payload.get("flat_fields", {})
    sub_tables = payload.get("sub_tables", {})
    overwrite = payload.get("overwrite", False)  # 是否覆盖已有值，默认只填空字段

    # 普通员工不能改管理员字段
    admin_only_fields = {"unit_id", "position", "rank", "work_start_date", "join_unit_date"}
    if current_user.role == "person":
        for k in list(flat_fields.keys()):
            if k in admin_only_fields:
                flat_fields.pop(k)

    updated_fields = []
    skipped_fields = []

    # 应用扁平字段
    for key, value in flat_fields.items():
        if not value:
            continue
        current_val = getattr(person, key, None)
        if current_val and not overwrite:
            skipped_fields.append(key)
            continue
        # 身份证变更需校验
        if key == "id_card" and value:
            if not validate_id_card(value):
                skipped_fields.append(key)
                continue
            exist = db.query(Person).filter(
                Person.id_card == value, Person.id != person_id, Person.is_deleted == False
            ).first()
            if exist:
                skipped_fields.append(key)
                continue
            # 联动回填出生日期和性别
            auto_birth, auto_gender = parse_id_card(value)
            if auto_birth and not person.birth_date:
                person.birth_date = auto_birth
            if auto_gender and not person.gender:
                person.gender = auto_gender

        setattr(person, key, value)
        updated_fields.append(key)

    # 应用子表（追加模式）
    added_sub = {}
    if sub_tables:
        sub_table_map = {
            "family_members": (FamilyMember, "family"),
            "education_records": (EducationRecord, "edu"),
            "work_records": (WorkRecord, "work"),
        }
        for table_key, items in sub_tables.items():
            if table_key not in sub_table_map:
                continue
            Model, _ = sub_table_map[table_key]
            added = 0
            for item in items:
                if not item:
                    continue
                # 过滤空值
                item = {k: v for k, v in item.items() if v}
                if not item:
                    continue
                record = Model(person_id=person.id, **item)
                db.add(record)
                added += 1
            if added > 0:
                added_sub[table_key] = added

    log_op(db, current_user, "apply_resume_to_person",
           f"应用简历到人员 {person.name}: 更新{len(updated_fields)}个字段, 新增子表{added_sub}",
           target_type="person", target_id=person.id)
    db.commit()

    return {
        "msg": "应用成功",
        "updated_fields": updated_fields,
        "skipped_fields": skipped_fields,
        "added_sub_tables": added_sub,
        "person_id": person.id,
    }


# ==================== 从简历创建人员档案 + 账号 ====================

@router.post("/create-with-account", summary="从简历创建人员档案和账号（人事用）")
def create_with_account(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """人事从简历识别结果创建人员档案和账号

    请求体：
    {
        "flat_fields": {...},
        "sub_tables": {...},
        "unit_id": 1,
        "department": "办公室",
        "position": "科员",
        "password": "可选，留空用身份证后6位",
        "username": "可选，留空自动生成"
    }
    """
    # 权限检查
    unit_id = payload.get("unit_id") or current_user.unit_id
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权在该单位创建")

    flat = payload.get("flat_fields", {})
    sub_tables = payload.get("sub_tables", {})

    name = flat.get("name", "").strip()
    id_card = flat.get("id_card", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="简历未识别到姓名，无法创建")
    if not id_card or not validate_id_card(id_card):
        raise HTTPException(status_code=400, detail="简历未识别到有效身份证号，无法创建")

    # 检查是否已存在
    existing_person = db.query(Person).filter(
        Person.id_card == id_card, Person.is_deleted == False
    ).first()
    if existing_person:
        raise HTTPException(status_code=400, detail=f"该身份证已存在人员档案：{existing_person.name}")

    existing_user = db.query(User).join(Person, User.person_id == Person.id).filter(
        Person.id_card == id_card
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"该员工已有账号：{existing_user.username}")

    # 解析身份证获取出生日期和性别（如果简历未提供，用身份证回填）
    auto_birth, auto_gender = parse_id_card(id_card)
    if not flat.get("birth_date") and auto_birth:
        flat["birth_date"] = auto_birth
    if not flat.get("gender") and auto_gender:
        flat["gender"] = auto_gender

    # 创建人员档案
    person_fields = {k: v for k, v in flat.items() if v}
    person_fields["unit_id"] = unit_id
    if payload.get("department"):
        person_fields["department"] = payload["department"]
    if payload.get("position"):
        person_fields["position"] = payload["position"]
    person_fields["created_by"] = current_user.id

    person = Person(**person_fields)
    db.add(person)
    db.flush()

    # 创建子表记录
    sub_table_models = {
        "family_members": FamilyMember,
        "education_records": EducationRecord,
        "work_records": WorkRecord,
    }
    sub_added = {}
    for table_key, items in sub_tables.items():
        if table_key not in sub_table_models:
            continue
        Model = sub_table_models[table_key]
        added = 0
        for item in items:
            item = {k: v for k, v in item.items() if v}
            if not item:
                continue
            record = Model(person_id=person.id, **item)
            db.add(record)
            added += 1
        if added > 0:
            sub_added[table_key] = added

    # 生成用户名
    username = payload.get("username")
    if not username:
        phone = flat.get("phone", "")
        username = _generate_username(db, name, phone)

    # 生成密码
    password = payload.get("password") or id_card[-6:]

    # 创建账号
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="person",
        unit_id=unit_id,
        person_id=person.id,
        first_login=True,
    )
    db.add(user)
    db.flush()

    log_op(db, current_user, "create_from_resume",
           f"从简历创建人员 {person.name} 和账号 {user.username}",
           target_type="person", target_id=person.id)
    db.commit()

    unit = db.query(Unit).get(unit_id)
    return {
        "msg": "创建成功",
        "person": {
            "id": person.id,
            "name": person.name,
            "id_card": id_card,
        },
        "account": {
            "user_id": user.id,
            "username": user.username,
            "initial_password": password,
            "first_login": True,
        },
        "unit": {"id": unit_id, "name": unit.name if unit else None},
        "sub_tables_added": sub_added,
        "flat_fields_applied": len(person_fields),
    }


# ==================== 批量从简历创建 ====================

@router.post("/batch-create", summary="批量从简历创建人员档案和账号")
async def batch_create(
    files: list[UploadFile] = File(...),
    unit_id: int = Query(..., description="目标单位ID"),
    password_mode: str = Query("idcard", description="密码模式: idcard=身份证后6位, uniform=统一密码"),
    uniform_password: str = Query(None, description="统一密码（password_mode=uniform时生效）"),
    department: str = Query(None, description="统一部门"),
    position: str = Query(None, description="统一岗位"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量上传简历，智能识别后一次性创建人员档案和账号

    每个简历独立处理，失败的不会影响其他文件。
    """
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权在该单位创建")

    success_list = []
    failed_list = []

    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            failed_list.append({
                "filename": file.filename,
                "name": "",
                "reason": f"不支持的格式: {ext}",
            })
            continue

        tmp_name = f"batch_create_{uuid.uuid4().hex}{ext}"
        tmp_path = os.path.join(settings.UPLOAD_DIR, tmp_name)
        try:
            content = await file.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            result = smart_parse_resume(tmp_path, ext)
        except Exception as e:
            failed_list.append({
                "filename": file.filename, "name": "", "reason": f"解析失败: {e}",
            })
            continue
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        flat = result["flat_fields"]
        sub_tables = result["sub_tables"]
        name = flat.get("name", "").strip()
        id_card = flat.get("id_card", "").strip()

        if not name:
            failed_list.append({
                "filename": file.filename, "name": "", "reason": "未识别到姓名",
            })
            continue
        if not id_card or not validate_id_card(id_card):
            failed_list.append({
                "filename": file.filename, "name": name, "reason": "未识别到有效身份证号",
            })
            continue

        # 检查重复
        existing_person = db.query(Person).filter(
            Person.id_card == id_card, Person.is_deleted == False
        ).first()
        if existing_person:
            failed_list.append({
                "filename": file.filename, "name": name,
                "reason": f"身份证已存在：{existing_person.name}",
            })
            continue

        existing_user = db.query(User).join(Person, User.person_id == Person.id).filter(
            Person.id_card == id_card
        ).first()
        if existing_user:
            failed_list.append({
                "filename": file.filename, "name": name,
                "reason": f"已有账号：{existing_user.username}",
            })
            continue

        try:
            # 解析身份证回填
            auto_birth, auto_gender = parse_id_card(id_card)
            if not flat.get("birth_date") and auto_birth:
                flat["birth_date"] = auto_birth
            if not flat.get("gender") and auto_gender:
                flat["gender"] = auto_gender

            # 创建人员
            person_fields = {k: v for k, v in flat.items() if v}
            person_fields["unit_id"] = unit_id
            if department:
                person_fields["department"] = department
            if position:
                person_fields["position"] = position
            person_fields["created_by"] = current_user.id

            person = Person(**person_fields)
            db.add(person)
            db.flush()

            # 创建子表
            sub_added = {}
            sub_models = {
                "family_members": FamilyMember,
                "education_records": EducationRecord,
                "work_records": WorkRecord,
            }
            for tk, items in sub_tables.items():
                if tk not in sub_models:
                    continue
                Model = sub_models[tk]
                added = 0
                for item in items:
                    item = {k: v for k, v in item.items() if v}
                    if not item:
                        continue
                    db.add(Model(person_id=person.id, **item))
                    added += 1
                if added > 0:
                    sub_added[tk] = added

            # 生成用户名和密码
            phone = flat.get("phone", "")
            username = _generate_username(db, name, phone)
            if password_mode == "uniform" and uniform_password:
                pwd = uniform_password
            else:
                pwd = id_card[-6:]

            user = User(
                username=username,
                password_hash=hash_password(pwd),
                role="person",
                unit_id=unit_id,
                person_id=person.id,
                first_login=True,
            )
            db.add(user)
            db.flush()

            success_list.append({
                "filename": file.filename,
                "name": name,
                "username": username,
                "password": pwd,
                "person_id": person.id,
                "fields_count": len(person_fields),
                "sub_tables": sub_added,
            })
        except Exception as e:
            failed_list.append({
                "filename": file.filename, "name": name, "reason": str(e),
            })

    log_op(db, current_user, "batch_create_from_resume",
           f"批量从简历创建: 成功{len(success_list)}个, 失败{len(failed_list)}个",
           target_type="unit", target_id=unit_id)
    db.commit()

    return {
        "success_count": len(success_list),
        "failed_count": len(failed_list),
        "success": success_list,
        "failed": failed_list,
    }


# ==================== 辅助函数 ====================

def _generate_username(db: Session, name: str, phone: str = None) -> str:
    """生成用户名：优先用手机号，否则用姓名+序号"""
    import re
    if phone and not db.query(User).filter(User.username == phone).first():
        return phone
    base = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name)
    for i in range(1, 1000):
        candidate = f"{base}{i:03d}" if i > 1 else base
        if not db.query(User).filter(User.username == candidate).first():
            return candidate
    return base + str(int(datetime.utcnow().timestamp()))
