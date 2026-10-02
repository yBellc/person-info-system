"""人员管理路由：CRUD、变更历史、派生字段、数据隔离（模块 2、4）"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import (
    get_current_user, require_admin, can_access_unit, get_accessible_unit_ids,
    filter_persons_by_clearance, can_view_person, get_clearance_level,
    mask_field_value, mask_person_fields, SECURITY_LEVELS,
)
from app.core.idcard import (
    validate_id_card, parse_id_card, mask_id_card, calc_age, calc_years,
)
from app.models import (
    User, Person, FamilyMember, EducationRecord, WorkRecord, RewardPunishment,
    CustomFieldDefinition, CustomFieldValue, ChangeLog, OperationLog, Unit,
)
from app.schemas.person import (
    PersonCreate, PersonUpdate, PersonOut, PersonListOut, ChangeLogOut,
)

router = APIRouter(prefix="/persons", tags=["人员管理"])


def log_op(db, user, action, detail=None, target_type=None, target_id=None, old_value=None, new_value=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
        old_value=old_value, new_value=new_value,
    ))


def add_derived_fields(person: Person, db: Session) -> Person:
    """给人员对象补充派生字段（年龄/工龄/党龄）和关联单位名"""
    person.age = calc_age(person.birth_date)
    person.work_years = calc_years(person.work_start_date)
    person.party_years = calc_years(person.party_join_date)
    if person.unit_id:
        unit = db.query(Unit).get(person.unit_id)
        person.unit_name = unit.name if unit else None
    else:
        person.unit_name = None
    return person


def attach_custom_values(person: Person, db: Session):
    """附加自定义字段值（field_id, field_key, display_name, value）"""
    rows = db.query(CustomFieldValue, CustomFieldDefinition).join(
        CustomFieldDefinition, CustomFieldValue.field_id == CustomFieldDefinition.id
    ).filter(CustomFieldValue.person_id == person.id).all()
    person.custom_values = [
        {"field_id": fv.field_id, "field_key": fd.field_key,
         "display_name": fd.display_name, "value": fv.value}
        for fv, fd in rows
    ]


def record_change_log(db, person_id, user, field_key, old_val, new_val, reason=None):
    """记录字段级变更"""
    if str(old_val) == str(new_val):
        return
    db.add(ChangeLog(
        person_id=person_id, operator_id=user.id, operator_name=user.username,
        field_key=field_key, change_type="update",
        old_value=str(old_val) if old_val is not None else None,
        new_value=str(new_val) if new_val is not None else None,
        reason=reason,
    ))


# 可被本人/管理员修改的字段（防止越权改单位/职务）
PERSON_OWN_FIELDS = {
    "gender", "birth_date", "ethnicity", "native_place", "birth_place",
    "political_status", "party_join_date", "party_apply_date",
    "phone", "office_phone", "emergency_contact",
    "education_level", "degree", "school", "major", "graduation_date",
    "marital_status", "spouse_name", "children_count", "home_address",
    "department",  # 部门本人可改
}
# 仅管理员可改的字段
ADMIN_ONLY_FIELDS = {"unit_id", "position", "rank", "work_start_date", "join_unit_date"}
# 仅安全保密管理员/超管可改的字段（涉密分级）
SECURITY_ONLY_FIELDS = {"security_level"}


@router.get("", response_model=list[PersonListOut], summary="人员列表（按权限过滤）")
def list_persons(
    keyword: Optional[str] = Query(None, description="搜索姓名/身份证"),
    unit_id: Optional[int] = Query(None, description="按单位筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Person).filter(Person.is_deleted == False)

    # 数据隔离（支持层级：管理员可访问本单位及所有子孙单位）
    if current_user.role != "super_admin":
        accessible_ids = get_accessible_unit_ids(current_user, db)
        if not accessible_ids:
            return []
        q = q.filter(Person.unit_id.in_(accessible_ids))

    # 涉密分级过滤：低密级用户只能看到 security_level <= clearance_level 的人员
    q = filter_persons_by_clearance(q, current_user)

    if unit_id:
        if not can_access_unit(current_user, unit_id, db):
            raise HTTPException(status_code=403, detail="无权访问该单位")
        q = q.filter(Person.unit_id == unit_id)

    if keyword:
        q = q.filter(or_(Person.name.contains(keyword), Person.id_card.contains(keyword)))

    total = q.count()
    persons = q.order_by(Person.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    clearance = get_clearance_level(current_user)
    own_id = getattr(current_user, "person_id", None)
    for p in persons:
        p = add_derived_fields(p, db)
        # 用户查看自己的记录时不脱敏
        if own_id and p.id == own_id:
            result.append(PersonListOut(
                id=p.id, name=p.name, gender=p.gender, age=p.age,
                id_card_masked=mask_id_card(p.id_card) if p.id_card else None,
                unit_name=p.unit_name, department=p.department,
                position=p.position, rank=p.rank,
                education_level=p.education_level,
                phone=p.phone,
                security_level=getattr(p, "security_level", 1) or 1,
            ))
        else:
            result.append(PersonListOut(
                id=p.id, name=p.name, gender=p.gender, age=p.age,
                id_card_masked=mask_field_value(mask_id_card(p.id_card), "id_card", clearance),
                unit_name=p.unit_name, department=p.department,
                position=p.position, rank=p.rank,
                education_level=p.education_level,
                phone=mask_field_value(p.phone, "phone", clearance),
                security_level=getattr(p, "security_level", 1) or 1,
            ))
    return result


@router.get("/count", summary="人员总数（当前可见范围）")
def count_persons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Person)
    if current_user.role != "super_admin":
        accessible_ids = get_accessible_unit_ids(current_user, db)
        q = q.filter(Person.unit_id.in_(accessible_ids)) if accessible_ids else q.filter(False)
    return {"total": q.count()}


@router.get("/{person_id}", response_model=PersonOut, summary="人员详情")
def get_person(
    person_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = db.query(Person).get(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    # 权限：本人或本单位管理员或超管
    if current_user.role == "person":
        if current_user.person_id != person_id:
            raise HTTPException(status_code=403, detail="无权查看他人信息")
    elif current_user.role == "unit_admin":
        if not can_access_unit(current_user, person.unit_id, db):
            raise HTTPException(status_code=403, detail="无权查看外单位人员")

    # 涉密分级检查：低密级用户不能查看高密级人员
    if not can_view_person(current_user, person):
        raise HTTPException(status_code=403, detail=f"您的涉密等级不足，无法查看此{SECURITY_LEVELS.get(getattr(person, 'security_level', 1), '涉密')}级人员")

    person = add_derived_fields(person, db)
    attach_custom_values(person, db)
    return person


@router.post("", response_model=PersonOut, status_code=201, summary="新建人员（管理员）")
def create_person(
    req: PersonCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 决定归属单位：管理员可指定本单位及下属单位，超管可指定任意
    unit_id = req.unit_id or current_user.unit_id
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权在该单位创建人员")

    # 身份证查重
    if req.id_card:
        if db.query(Person).filter(Person.id_card == req.id_card).first():
            raise HTTPException(status_code=400, detail="该身份证号已存在")

    # 身份证联动回填出生日期/性别
    gender = req.gender
    birth_date = req.birth_date
    if req.id_card and validate_id_card(req.id_card):
        auto_birth, auto_gender = parse_id_card(req.id_card)
        if auto_birth:
            birth_date = birth_date or auto_birth
        if auto_gender:
            gender = gender or auto_gender

    person = Person(
        unit_id=unit_id, name=req.name, gender=gender, birth_date=birth_date,
        ethnicity=req.ethnicity, native_place=req.native_place, birth_place=req.birth_place,
        id_card=req.id_card, political_status=req.political_status,
        party_join_date=req.party_join_date, party_apply_date=req.party_apply_date,
        phone=req.phone, office_phone=req.office_phone, emergency_contact=req.emergency_contact,
        department=req.department, position=req.position, rank=req.rank,
        work_start_date=req.work_start_date, join_unit_date=req.join_unit_date,
        education_level=req.education_level, degree=req.degree, school=req.school,
        major=req.major, graduation_date=req.graduation_date,
        marital_status=req.marital_status, spouse_name=req.spouse_name,
        children_count=req.children_count, home_address=req.home_address,
        security_level=getattr(req, "security_level", 1) or 1,
        created_by=current_user.id,
    )
    db.add(person)
    db.flush()

    # 子表
    for fm in req.family_members:
        db.add(FamilyMember(person_id=person.id, **fm.model_dump()))
    for er in req.education_records:
        db.add(EducationRecord(person_id=person.id, **er.model_dump()))
    for wr in req.work_records:
        db.add(WorkRecord(person_id=person.id, **wr.model_dump()))
    for rp in req.rewards:
        db.add(RewardPunishment(person_id=person.id, **rp.model_dump()))

    # 自定义字段值
    for cv in req.custom_values:
        db.add(CustomFieldValue(person_id=person.id, field_id=cv.field_id, value=cv.value))

    # 变更日志：记录创建
    db.add(ChangeLog(
        person_id=person.id, operator_id=current_user.id, operator_name=current_user.username,
        field_key="__all__", change_type="create", new_value=req.name,
    ))
    log_op(db, current_user, "create_person", f"新建人员 {person.name}", target_type="person", target_id=person.id)
    db.commit()
    db.refresh(person)
    person = add_derived_fields(person, db)
    attach_custom_values(person, db)
    return person


@router.put("/{person_id}", response_model=PersonOut, summary="更新人员信息")
def update_person(
    person_id: int,
    req: PersonUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = db.query(Person).get(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")

    # 权限判定
    is_own = (current_user.role == "person" and current_user.person_id == person_id)
    is_admin = current_user.role in ("unit_admin", "super_admin")
    if not is_own and not is_admin:
        raise HTTPException(status_code=403, detail="无权修改")
    if current_user.role == "unit_admin" and not can_access_unit(current_user, person.unit_id, db):
        raise HTTPException(status_code=403, detail="无权修改外单位人员")

    reason = req.reason
    update_data = req.model_dump(exclude_unset=True, exclude_none=True)
    update_data.pop("reason", None)
    custom_values = update_data.pop("custom_values", None)

    # 字段级权限校验：个人账号不能改管理员专属字段
    # 注意：前端表单可能带上 unit_id 等字段的原值或空值，
    # 只有当字段确实"有值且与原值不同"时才视为越权修改
    if current_user.role == "person":
        for k in list(update_data.keys()):
            if k in ADMIN_ONLY_FIELDS:
                new_val = update_data[k]
                old_val = getattr(person, k, None)
                # 空值或与原值相同：视为未修改，直接剔除，不报错
                if new_val in (None, "", 0) or str(new_val) == str(old_val):
                    update_data.pop(k)
                    continue
                # 确实想改管理员字段 → 拒绝
                raise HTTPException(status_code=403, detail=f"字段 {k} 仅管理员可修改")

    # 涉密分级字段：仅安全保密管理员/超管可修改
    if "security_level" in update_data:
        if current_user.role not in ("super_admin", "security_officer"):
            update_data.pop("security_level", None)

    # 身份证变更：校验+查重+联动回填
    if "id_card" in update_data and update_data["id_card"]:
        new_id = update_data["id_card"]
        if not validate_id_card(new_id):
            raise HTTPException(status_code=400, detail="身份证号格式或校验位错误")
        exist = db.query(Person).filter(Person.id_card == new_id, Person.id != person_id).first()
        if exist:
            raise HTTPException(status_code=400, detail="该身份证号已被其他人占用")
        auto_birth, auto_gender = parse_id_card(new_id)
        # 身份证变了，自动回填（如未单独传值）
        if auto_birth and "birth_date" not in update_data:
            update_data["birth_date"] = auto_birth
        if auto_gender and "gender" not in update_data:
            update_data["gender"] = auto_gender

    # 调动单位日志
    if "unit_id" in update_data and not can_access_unit(current_user, update_data["unit_id"], db):
        raise HTTPException(status_code=403, detail="无权调动到该单位")

    # 逐字段更新 + 变更记录
    for k, v in update_data.items():
        old_val = getattr(person, k)
        record_change_log(db, person_id, current_user, k, old_val, v, reason)
        setattr(person, k, v)

    # 自定义字段更新
    if custom_values is not None:
        for cv in custom_values:
            existing = db.query(CustomFieldValue).filter(
                CustomFieldValue.person_id == person_id,
                CustomFieldValue.field_id == cv.field_id,
            ).first()
            if existing:
                record_change_log(db, person_id, current_user, f"custom_{cv.field_id}",
                                  existing.value, cv.value, reason)
                existing.value = cv.value
            else:
                db.add(CustomFieldValue(person_id=person_id, field_id=cv.field_id, value=cv.value))

    log_op(db, current_user, "update_person", f"修改人员 {person.name}", target_type="person", target_id=person.id)
    db.commit()
    db.refresh(person)
    person = add_derived_fields(person, db)
    attach_custom_values(person, db)
    return person


@router.delete("/{person_id}", summary="删除人员（管理员）")
def delete_person(
    person_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """软删除人员（可从回收站恢复）"""
    person = db.query(Person).filter(Person.id == person_id, Person.is_deleted == False).first()
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    if current_user.role == "unit_admin" and not can_access_unit(current_user, person.unit_id, db):
        raise HTTPException(status_code=403, detail="无权删除")
    name = person.name

    # 记录旧值用于审计
    old_value = {"name": name, "id_card": person.id_card, "is_deleted": False}

    person.is_deleted = True
    person.deleted_at = datetime.utcnow()
    person.deleted_by = current_user.id

    log_op(db, current_user, "delete_person", f"软删除人员 {name}",
           target_type="person", target_id=person_id, old_value=old_value, new_value={"is_deleted": True})
    db.commit()
    return {"msg": f"已删除 {name}（可在回收站恢复）"}


@router.get("/recycle-bin/list", summary="回收站 - 已删除人员列表")
def list_deleted_persons(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """查看已软删除的人员列表"""
    q = db.query(Person).filter(Person.is_deleted == True)
    if current_user.role != "super_admin":
        accessible_ids = get_accessible_unit_ids(current_user, db)
        if not accessible_ids:
            return []
        q = q.filter(Person.unit_id.in_(accessible_ids))
    persons = q.order_by(Person.deleted_at.desc()).all()
    return [
        {
            "id": p.id, "name": p.name, "id_card": p.id_card,
            "deleted_at": p.deleted_at, "deleted_by": current_user.username,
        }
        for p in persons
    ]


@router.post("/{person_id}/restore", summary="从回收站恢复人员")
def restore_person(
    person_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """恢复软删除的人员"""
    person = db.query(Person).filter(Person.id == person_id, Person.is_deleted == True).first()
    if not person:
        raise HTTPException(status_code=404, detail="该人员不在回收站中")
    person.is_deleted = False
    person.deleted_at = None
    person.deleted_by = None
    log_op(db, current_user, "restore_person", f"恢复人员 {person.name}",
           target_type="person", target_id=person_id, old_value={"is_deleted": True}, new_value={"is_deleted": False})
    db.commit()
    return {"msg": f"已恢复 {person.name}"}


@router.get("/{person_id}/changes", response_model=list[ChangeLogOut], summary="变更历史")
def get_change_logs(
    person_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = db.query(Person).get(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    # 权限同查看
    if current_user.role == "person" and current_user.person_id != person_id:
        raise HTTPException(status_code=403, detail="无权查看")
    if current_user.role == "unit_admin" and not can_access_unit(current_user, person.unit_id, db):
        raise HTTPException(status_code=403, detail="无权查看")

    logs = db.query(ChangeLog).filter(ChangeLog.person_id == person_id).order_by(
        ChangeLog.created_at.desc()
    ).limit(200).all()
    return logs
