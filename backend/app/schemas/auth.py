"""认证与账号相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: int
    first_login: bool = False


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    """用户自助注册 - 凭姓名+身份证匹配名单"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    id_card: str = Field(..., min_length=18, max_length=18, description="身份证号")

    @field_validator("id_card")
    @classmethod
    def validate_id_card_len(cls, v):
        if len(v) != 18:
            raise ValueError("身份证号必须为18位")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class CreateUnitAdminRequest(BaseModel):
    """超级管理员创建单位管理员账号"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    unit_id: int = Field(..., description="管理的单位ID")
    display_name: Optional[str] = Field(None, max_length=50, description="管理员姓名(备注用)")


class AdminApplicationCreate(BaseModel):
    """提交管理员申请"""
    reason: Optional[str] = Field(None, max_length=500, description="申请理由")


class AdminApplicationReview(BaseModel):
    """审批申请"""
    review_note: Optional[str] = Field(None, max_length=500, description="审批意见")


class AdminApplicationOut(BaseModel):
    """申请信息输出"""
    id: int
    user_id: int
    username: str
    target_unit_id: int
    target_unit_name: str
    status: str
    reason: Optional[str] = None
    reviewer_id: Optional[int] = None
    review_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    """用户信息输出"""
    id: int
    username: str
    role: str
    unit_id: Optional[int] = None
    unit_name: Optional[str] = None
    person_id: Optional[int] = None
    is_active: bool
    first_login: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 人事批量注册 =====

class HrCreateAccountRequest(BaseModel):
    """人事为员工创建账号"""
    name: str = Field(..., min_length=1, max_length=50, description="员工姓名")
    id_card: str = Field(..., min_length=18, max_length=18, description="身份证号")
    phone: Optional[str] = Field(None, max_length=20, description="手机号(用作用户名)")
    unit_id: int = Field(..., description="所属单位ID")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    position: Optional[str] = Field(None, max_length=100, description="岗位")
    password: Optional[str] = Field(None, min_length=6, description="初始密码(不填则用身份证后6位)")


class HrBatchCreateRequest(BaseModel):
    """人事批量创建账号"""
    unit_id: int = Field(..., description="单位ID")
    roster_ids: list[int] = Field(..., description="名单ID列表")
    password_mode: str = Field("idcard", description="密码模式: idcard(身份证后6位)/phone(手机后6位)/uniform(统一密码)")
    uniform_password: Optional[str] = Field(None, min_length=6, description="统一密码(password_mode=uniform时使用)")


class HrAccountOut(BaseModel):
    """人事创建的账号信息"""
    id: int
    username: str
    name: str
    id_card: str
    phone: Optional[str] = None
    unit_id: int
    unit_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool
    first_login: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HrBatchResult(BaseModel):
    """批量创建结果"""
    success: list[HrAccountOut] = []
    failed: list[dict] = []  # [{name, id_card, reason}]


class FirstLoginChangePasswordRequest(BaseModel):
    """首次登录修改密码"""
    new_password: str = Field(..., min_length=6, max_length=100)
