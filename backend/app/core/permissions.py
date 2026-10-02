"""权限辅助模块 - 角色验证、数据权限过滤"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, Unit
from app.models.permission import UserRole, Role
from app.core.security import decode_access_token

# JWT Bearer 认证
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前登录用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或令牌无效",
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期或无效",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已禁用",
        )

    return user


def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求用户必须是超级管理员"""
    # 涉密三员：只有 super_admin 拥有最高权限（三员分立后超管仍保留全局权限，但审计员不能删除记录等在各接口单独校验）
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求用户必须是管理员级
    包含：super_admin / unit_admin / system_admin（系统管理员三员）/ security_officer（保密管理员三员）
    auditor（审计员三员）**不允许**访问业务管理类接口
    """
    admin_roles = ("super_admin", "unit_admin", "system_admin", "security_officer")
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限（审计员仅可查看审计日志）",
        )
    return current_user


def require_auditor(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求：安全审计员或超管（用于审计日志相关接口的专门权限）
    三员分立：system_admin 与 security_officer **不得**查看审计日志
    """
    if current_user.role not in ("super_admin", "auditor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅安全审计员与超管可查看审计日志（三员分立强制隔离）",
        )
    return current_user


def require_security_officer(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求：安全保密管理员或超管（用于密码策略、密级、权限配置等安全类操作）
    三员分立：system_admin 与 auditor **不得**修改安全策略
    """
    if current_user.role not in ("super_admin", "security_officer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅安全保密管理员与超管可配置安全策略（三员分立强制隔离）",
        )
    return current_user


def require_system_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求：系统管理员(三员)或超管（用于系统配置、账号管理、备份恢复等系统级操作）
    三员分立：security_officer 与 auditor **不得**操作系统配置
    """
    if current_user.role not in ("super_admin", "system_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅系统管理员与超管可操作系统配置（三员分立强制隔离）",
        )
    return current_user


def _get_descendant_unit_ids(db: Session, unit_id: int) -> set:
    """递归获取某单位及其所有子单位的ID"""
    ids = {unit_id}
    children = db.query(Unit).filter(Unit.parent_id == unit_id).all()
    for child in children:
        ids.update(_get_descendant_unit_ids(db, child.id))
    return ids


def can_access_unit(current_user: User, unit_id: int, db: Session) -> bool:
    """检查用户是否有权访问指定单位"""
    if current_user.role == "super_admin":
        return True
    if current_user.role == "unit_admin" and current_user.unit_id:
        accessible = _get_descendant_unit_ids(db, current_user.unit_id)
        return unit_id in accessible
    return False


def get_accessible_unit_ids(current_user: User, db: Session) -> list:
    """获取用户可访问的单位ID列表"""
    if current_user.role == "super_admin":
        return [u.id for u in db.query(Unit).all()]
    if current_user.role == "unit_admin" and current_user.unit_id:
        return list(_get_descendant_unit_ids(db, current_user.unit_id))
    # 普通用户：可访问自己所属单位（通过 person_id 关联）
    if current_user.role == "person" and getattr(current_user, "person_id", None):
        from app.models.person import Person
        person = db.query(Person).get(current_user.person_id)
        if person and person.unit_id:
            return list(_get_descendant_unit_ids(db, person.unit_id))
    return []


def require_role(*roles: str):
    """要求用户具有指定角色之一"""
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        # 超级管理员跳过所有检查
        if current_user.role == "super_admin":
            return current_user

        # 单位管理员也能访问 person 级接口（管理员可查看所有模块）
        if current_user.role == "unit_admin" and "person" in roles:
            return current_user

        # 检查基础角色
        if current_user.role in roles:
            return current_user

        # 检查分配的角色
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == current_user.id
        ).all()

        for ur in user_roles:
            role = db.query(Role).filter(Role.id == ur.role_id).first()
            if role and role.code in roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要以下角色之一: {', '.join(roles)}",
        )

    return dependency


def get_data_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """获取当前用户的数据权限配置"""
    if current_user.role == "super_admin":
        return {"scope": "all", "conditions": None}

    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]

    # 检查是否有全局权限
    for role_id in role_ids:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role and role.code == "unit_admin":
            return {"scope": "unit", "unit_id": current_user.unit_id}

    # 个人账号只能看自己
    if current_user.role == "person":
        return {"scope": "self", "user_id": current_user.id}

    return {"scope": "none", "conditions": None}


# ============ 涉密分级管控 ============

SECURITY_LEVELS = {
    0: "公开",
    1: "内部",
    2: "秘密",
    3: "机密",
}

# 字段密级映射：哪些字段属于哪个密级
FIELD_SECURITY_MAP = {
    # 公开字段（0级）
    "name": 0, "gender": 0, "department": 0, "position": 0, "rank": 0,
    "education_level": 0, "unit_name": 0, "age": 0, "work_years": 0,
    # 内部字段（1级）
    "birth_date": 1, "ethnicity": 1, "native_place": 1, "birth_place": 1,
    "political_status": 1, "party_join_date": 1, "party_apply_date": 1,
    "work_start_date": 1, "join_unit_date": 1, "degree": 1, "school": 1,
    "major": 1, "graduation_date": 1, "marital_status": 1, "data_status": 1,
    "security_level": 1,
    # 秘密字段（2级）
    "id_card": 2, "phone": 2, "office_phone": 2, "emergency_contact": 2,
    "home_address": 2, "spouse_name": 2, "children_count": 2,
}

# 默认密级：未在映射中的字段视为1级（内部）
DEFAULT_FIELD_LEVEL = 1


def get_clearance_level(user: User) -> int:
    """获取用户的涉密等级（0-3）"""
    return getattr(user, "clearance_level", 0) or 0


def can_view_person(user: User, person) -> bool:
    """检查用户是否有权查看该人员记录（基于人员密级 vs 用户密级）
    规则：
    - 超管可查看所有
    - 用户可查看自己（不受密级限制）
    - 其他用户：密级必须 >= 目标人员密级
    """
    if user.role == "super_admin":
        return True
    # 用户可查看自己的档案（无论密级）
    if getattr(user, "person_id", None) and user.person_id == person.id:
        return True
    person_level = getattr(person, "security_level", 1) or 1
    return get_clearance_level(user) >= person_level


def filter_persons_by_clearance(query, user: User):
    """在查询上追加密级过滤：用户只能看到 security_level <= clearance_level 的人员
    用户自己的记录不受密级过滤限制，始终可见
    """
    if user.role == "super_admin":
        return query
    from app.models.person import Person
    clearance = get_clearance_level(user)
    own_id = getattr(user, "person_id", None)
    if own_id:
        from sqlalchemy import or_
        return query.filter(or_(
            Person.security_level <= clearance,
            Person.id == own_id,
        ))
    return query.filter(Person.security_level <= clearance)


def mask_field_value(value, field_key: str, user_clearance: int):
    """根据用户密级对字段值进行脱敏

    - clearance >= 3 (机密)：不脱敏
    - clearance == 2 (秘密)：部分打码（保留首尾）
    - clearance <= 1 (内部/公开)：完全打码或隐藏
    """
    if value is None or value == "":
        return value

    field_level = FIELD_SECURITY_MAP.get(field_key, DEFAULT_FIELD_LEVEL)

    # 用户密级 >= 字段密级：不脱敏
    if user_clearance >= field_level:
        return value

    # 机密级用户：不脱敏
    if user_clearance >= 3:
        return value

    # 秘密级用户看秘密字段：部分打码
    if user_clearance == 2 and field_level == 2:
        s = str(value)
        if field_key == "id_card" and len(s) >= 11:
            return s[:4] + "********" + s[-4:]
        if field_key in ("phone", "office_phone") and len(s) >= 7:
            return s[:3] + "****" + s[-4:]
        if field_key in ("home_address", "emergency_contact"):
            return s[:6] + "***" if len(s) > 6 else "***"
        if field_key == "spouse_name" and len(s) > 0:
            return s[0] + "*" if len(s) > 1 else "*"
        return s[:2] + "***" if len(s) > 2 else "***"

    # 内部/公开用户看秘密字段：完全打码
    if field_level >= 2:
        return "******"

    return value


def mask_person_fields(person_data: dict, user: User) -> dict:
    """对人员数据字典进行字段级脱敏（用于导出和API返回）"""
    clearance = get_clearance_level(user)
    if clearance >= 3:
        return person_data
    masked = {}
    for key, value in person_data.items():
        masked[key] = mask_field_value(value, key, clearance)
    return masked