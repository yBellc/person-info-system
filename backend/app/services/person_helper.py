"""人员创建共享 helper（供正常创建和简历导入复用）"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.idcard import validate_id_card, parse_id_card
from app.models import (
    Person, FamilyMember, EducationRecord, WorkRecord, RewardPunishment,
    ChangeLog, OperationLog,
)


def create_person_from_dict(
    db: Session,
    data: dict,
    unit_id: int,
    operator_id: int,
    operator_name: str,
) -> tuple:
    """从字典创建人员记录（含子表、身份证联动回填、变更日志）

    Args:
        db: 数据库会话
        data: 人员数据，flat字段在顶层，子表在 family_members/work_records/education_records/rewards
        unit_id: 所属单位
        operator_id: 操作人ID
        operator_name: 操作人用户名

    Returns:
        (person, error_message)  成功时 error_message 为 None
    """
    # 提取子表（从 data 中弹出，避免污染主表字段）
    family = data.pop("family_members", []) or []
    education = data.pop("education_records", []) or []
    work = data.pop("work_records", []) or []
    rewards = data.pop("rewards", []) or []

    # 身份证查重
    id_card = data.get("id_card")
    if id_card:
        exist = db.query(Person).filter(Person.id_card == id_card).first()
        if exist:
            return None, f"身份证号 {id_card} 已存在（人员: {exist.name}）"

    # 身份证联动回填出生日期/性别
    gender = data.get("gender")
    birth_date = _parse_date(data.get("birth_date"))
    if id_card and validate_id_card(id_card):
        auto_birth, auto_gender = parse_id_card(id_card)
        if auto_birth and not birth_date:
            birth_date = auto_birth
        if auto_gender and not gender:
            gender = auto_gender

    # 只取 Person 主表存在的字段
    person_fields = _get_person_fields()
    person_data = {}
    for k, v in data.items():
        if k in person_fields:
            person_data[k] = _convert_value(k, v)

    # 覆盖联动回填的值
    person_data["gender"] = gender
    person_data["birth_date"] = birth_date

    person = Person(
        unit_id=unit_id,
        created_by=operator_id,
        **person_data,
    )
    db.add(person)
    db.flush()

    # 子表
    for fm in family:
        fm_data = {k: _convert_sub_value(k, v) for k, v in fm.items() if k in _FAMILY_FIELDS}
        fm_data["person_id"] = person.id
        db.add(FamilyMember(**fm_data))
    for er in education:
        er_data = {k: _convert_sub_value(k, v) for k, v in er.items() if k in _EDU_FIELDS}
        er_data["person_id"] = person.id
        db.add(EducationRecord(**er_data))
    for wr in work:
        wr_data = {k: _convert_sub_value(k, v) for k, v in wr.items() if k in _WORK_FIELDS}
        wr_data["person_id"] = person.id
        db.add(WorkRecord(**wr_data))
    for rp in rewards:
        rp_data = {k: _convert_sub_value(k, v) for k, v in rp.items() if k in _REWARD_FIELDS}
        rp_data["person_id"] = person.id
        db.add(RewardPunishment(**rp_data))

    # 变更日志
    db.add(ChangeLog(
        person_id=person.id, operator_id=operator_id, operator_name=operator_name,
        field_key="__all__", change_type="create",
        new_value=person.name, reason="简历表批量导入",
    ))
    db.add(OperationLog(
        operator_id=operator_id, operator_name=operator_name, action="import_person",
        detail=f"简历导入创建人员 {person.name}", target_type="person", target_id=person.id,
    ))

    return person, None


# Person 主表字段白名单
_PERSON_FIELDS = None
_FAMILY_FIELDS = {"relation", "name", "birth_date", "political_status", "work_info", "phone", "sort"}
_EDU_FIELDS = {"start_date", "end_date", "school", "major", "education_level", "degree", "is_full_time", "sort"}
_WORK_FIELDS = {"start_date", "end_date", "unit", "position", "witness", "sort"}
_REWARD_FIELDS = {"type", "date", "name", "approval_authority", "document_no", "sort"}

_DATE_FIELDS = {
    "birth_date", "party_join_date", "party_apply_date",
    "work_start_date", "join_unit_date", "graduation_date",
}
_INT_FIELDS = {"children_count"}


def _get_person_fields():
    global _PERSON_FIELDS
    if _PERSON_FIELDS is None:
        from app.models import Person
        _PERSON_FIELDS = {c.name for c in Person.__table__.columns}
        _PERSON_FIELDS.discard("id")
        _PERSON_FIELDS.discard("created_at")
        _PERSON_FIELDS.discard("updated_at")
        _PERSON_FIELDS.discard("created_by")
    return _PERSON_FIELDS


def _parse_date(val) -> Optional[date]:
    """把字符串转 date，失败返回 None"""
    if val is None or val == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    # YYYY-MM-DD
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        pass
    return None


def _convert_value(field_key: str, val):
    """主表字段值转换"""
    if val is None or val == "":
        return None
    if field_key in _DATE_FIELDS:
        return _parse_date(val)
    if field_key in _INT_FIELDS:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    return val


def _convert_sub_value(field_key: str, val):
    """子表字段值转换"""
    if val is None or val == "":
        return None
    if field_key in ("birth_date", "start_date", "end_date", "date"):
        return _parse_date(val)
    if field_key in ("is_full_time",):
        if isinstance(val, bool):
            return val
        return str(val).strip() in ("是", "True", "true", "1", "全日制")
    if field_key == "sort":
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
    return val
