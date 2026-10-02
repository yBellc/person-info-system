"""人员相关 Pydantic 模型（模块 2、4）"""
from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

from app.core.idcard import validate_id_card, parse_id_card


# ===== 子表 =====
class FamilyMemberBase(BaseModel):
    relation: Optional[str] = None
    name: Optional[str] = None
    birth_date: Optional[date] = None
    political_status: Optional[str] = None
    work_info: Optional[str] = None
    phone: Optional[str] = None
    sort: int = 0


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberOut(FamilyMemberBase):
    id: int
    class Config:
        from_attributes = True


class EducationRecordBase(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    school: Optional[str] = None
    major: Optional[str] = None
    education_level: Optional[str] = None
    degree: Optional[str] = None
    is_full_time: Optional[bool] = None
    sort: int = 0


class EducationRecordCreate(EducationRecordBase):
    pass


class EducationRecordOut(EducationRecordBase):
    id: int
    class Config:
        from_attributes = True


class WorkRecordBase(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    unit: Optional[str] = None
    position: Optional[str] = None
    witness: Optional[str] = None
    sort: int = 0


class WorkRecordCreate(WorkRecordBase):
    pass


class WorkRecordOut(WorkRecordBase):
    id: int
    class Config:
        from_attributes = True


class RewardPunishmentBase(BaseModel):
    type: Optional[str] = None
    date: Optional[date] = None
    name: Optional[str] = None
    approval_authority: Optional[str] = None
    document_no: Optional[str] = None
    sort: int = 0


class RewardPunishmentCreate(RewardPunishmentBase):
    pass


class RewardPunishmentOut(RewardPunishmentBase):
    id: int
    class Config:
        from_attributes = True


# ===== 自定义字段 =====
class CustomFieldBase(BaseModel):
    field_key: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=50)
    data_type: str = Field("text", pattern=r"^(text|number|date|select|textarea)$")
    group_name: str = "自定义"
    sort: int = 0
    is_required: bool = False
    options: Optional[list[str]] = None
    is_active: bool = True


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldUpdate(BaseModel):
    display_name: Optional[str] = None
    data_type: Optional[str] = None
    group_name: Optional[str] = None
    sort: Optional[int] = None
    is_required: Optional[bool] = None
    options: Optional[list[str]] = None
    is_active: Optional[bool] = None


class CustomFieldOut(CustomFieldBase):
    id: int
    class Config:
        from_attributes = True


class CustomFieldValueIn(BaseModel):
    """自定义字段值输入（key->value）"""
    field_id: int
    value: Optional[str] = None


# ===== 人员主表 =====
class PersonBase(BaseModel):
    """人员核心字段"""
    name: str = Field(..., max_length=50)
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    ethnicity: Optional[str] = None
    native_place: Optional[str] = None
    birth_place: Optional[str] = None
    id_card: Optional[str] = None
    political_status: Optional[str] = None
    party_join_date: Optional[date] = None
    party_apply_date: Optional[date] = None
    phone: Optional[str] = None
    office_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    rank: Optional[str] = None
    work_start_date: Optional[date] = None
    join_unit_date: Optional[date] = None
    education_level: Optional[str] = None
    degree: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    graduation_date: Optional[date] = None
    marital_status: Optional[str] = None
    spouse_name: Optional[str] = None
    children_count: Optional[int] = None
    home_address: Optional[str] = None


class PersonCreate(PersonBase):
    """创建人员 - 带子表和自定义字段"""
    unit_id: Optional[int] = None
    security_level: Optional[int] = Field(1, ge=0, le=3, description="涉密等级: 0=公开 1=内部 2=秘密 3=机密")
    family_members: list[FamilyMemberCreate] = []
    education_records: list[EducationRecordCreate] = []
    work_records: list[WorkRecordCreate] = []
    rewards: list[RewardPunishmentCreate] = []
    custom_values: list[CustomFieldValueIn] = []

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, v):
        if v is not None and v != "" and not validate_id_card(v):
            raise ValueError("身份证号格式或校验位错误")
        return v


class PersonUpdate(BaseModel):
    """更新人员 - 所有字段可选，支持部分更新"""
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    ethnicity: Optional[str] = None
    native_place: Optional[str] = None
    birth_place: Optional[str] = None
    id_card: Optional[str] = None
    political_status: Optional[str] = None
    party_join_date: Optional[date] = None
    party_apply_date: Optional[date] = None
    phone: Optional[str] = None
    office_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    unit_id: Optional[int] = None
    department: Optional[str] = None
    position: Optional[str] = None
    rank: Optional[str] = None
    work_start_date: Optional[date] = None
    join_unit_date: Optional[date] = None
    education_level: Optional[str] = None
    degree: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    graduation_date: Optional[date] = None
    marital_status: Optional[str] = None
    spouse_name: Optional[str] = None
    children_count: Optional[int] = None
    home_address: Optional[str] = None
    security_level: Optional[int] = Field(None, ge=0, le=3, description="涉密等级: 0=公开 1=内部 2=秘密 3=机密")
    reason: Optional[str] = Field(None, description="修改原因，记入变更日志")
    custom_values: Optional[list[CustomFieldValueIn]] = None


class PersonOut(PersonBase):
    """人员信息输出 - 含派生字段和关联数据"""
    id: int
    unit_id: Optional[int] = None
    unit_name: Optional[str] = None
    data_status: Optional[str] = None
    security_level: int = 1
    created_at: datetime
    updated_at: datetime

    # 派生字段（实时计算）
    age: Optional[int] = None
    work_years: Optional[float] = None
    party_years: Optional[float] = None

    # 子表
    family_members: list[FamilyMemberOut] = []
    education_records: list[EducationRecordOut] = []
    work_records: list[WorkRecordOut] = []
    rewards: list[RewardPunishmentOut] = []
    custom_values: list[dict] = []

    class Config:
        from_attributes = True


class PersonListOut(BaseModel):
    """人员列表项（精简，带脱敏）"""
    id: int
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    id_card_masked: Optional[str] = None
    unit_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    rank: Optional[str] = None
    education_level: Optional[str] = None
    phone: Optional[str] = None
    security_level: int = 1

    class Config:
        from_attributes = True


class ChangeLogOut(BaseModel):
    """变更历史"""
    id: int
    person_id: int
    operator_name: str
    field_key: str
    change_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
