"""权限路由 - 角色、用户角色、数据权限、字段权限"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.permission import Role, UserRole, DataPermission, FieldPermission
from app.models.user import User
from app.schemas.permission import (
    RoleCreate, RoleUpdate, RoleResponse,
    UserRoleCreate, UserRoleResponse,
    DataPermissionCreate, DataPermissionUpdate, DataPermissionResponse,
    FieldPermissionCreate, FieldPermissionUpdate, FieldPermissionResponse,
    UserPermissionsResponse,
)
from app.core.permissions import require_role

router = APIRouter(tags=["权限管理"])


# ============ 角色路由 ============

@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """获取角色列表"""
    query = db.query(Role)
    if is_active is not None:
        query = query.filter(Role.is_active == is_active)

    results = []
    for role in query.order_by(Role.level).all():
        role_dict = {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "created_at": role.created_at,
            "user_count": len(role.user_roles),
        }
        results.append(role_dict)

    return results


@router.post("/roles", response_model=RoleResponse)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """创建角色"""
    existing = db.query(Role).filter(Role.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色编码已存在")
    role = Role(**data.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """更新角色"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可修改")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)

    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除角色"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")
    if len(role.user_roles) > 0:
        raise HTTPException(status_code=400, detail="角色已分配给用户，无法删除")

    db.delete(role)
    db.commit()
    return {"message": "角色已删除"}


# ============ 用户角色路由 ============

@router.get("/user-roles", response_model=List[UserRoleResponse])
def list_user_roles(
    user_id: Optional[int] = Query(None, description="用户ID"),
    role_id: Optional[int] = Query(None, description="角色ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """获取用户角色关联列表"""
    query = db.query(UserRole)
    if user_id:
        query = query.filter(UserRole.user_id == user_id)
    if role_id:
        query = query.filter(UserRole.role_id == role_id)

    results = []
    for ur in query.all():
        role = db.query(Role).filter(Role.id == ur.role_id).first()
        ur_dict = {
            "id": ur.id,
            "user_id": ur.user_id,
            "role_id": ur.role_id,
            "role_name": role.name if role else None,
            "role_code": role.code if role else None,
            "unit_id": ur.unit_id,
            "granted_by": ur.granted_by,
            "granted_at": ur.granted_at,
            "expires_at": ur.expires_at,
        }
        results.append(ur_dict)

    return results


@router.post("/user-roles", response_model=UserRoleResponse)
def create_user_role(
    data: UserRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """创建用户角色关联"""
    # 检查用户是否存在
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查角色是否存在
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查是否已存在
    existing = db.query(UserRole).filter(
        UserRole.user_id == data.user_id,
        UserRole.role_id == data.role_id,
        UserRole.unit_id == data.unit_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已分配此角色")

    ur = UserRole(
        user_id=data.user_id,
        role_id=data.role_id,
        unit_id=data.unit_id,
        granted_by=current_user.id,
        expires_at=data.expires_at,
    )
    db.add(ur)
    db.commit()
    db.refresh(ur)

    # 返回结果
    result = {
        "id": ur.id,
        "user_id": ur.user_id,
        "role_id": ur.role_id,
        "role_name": role.name,
        "role_code": role.code,
        "unit_id": ur.unit_id,
        "granted_by": ur.granted_by,
        "granted_at": ur.granted_at,
        "expires_at": ur.expires_at,
    }
    return result


@router.delete("/user-roles/{ur_id}")
def delete_user_role(
    ur_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除用户角色关联"""
    ur = db.query(UserRole).filter(UserRole.id == ur_id).first()
    if not ur:
        raise HTTPException(status_code=404, detail="用户角色关联不存在")

    db.delete(ur)
    db.commit()
    return {"message": "用户角色关联已删除"}


# ============ 数据权限路由 ============

@router.get("/data-permissions", response_model=List[DataPermissionResponse])
def list_data_permissions(
    role_id: Optional[int] = Query(None, description="角色ID"),
    resource: Optional[str] = Query(None, description="资源名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """获取数据权限列表"""
    query = db.query(DataPermission)
    if role_id:
        query = query.filter(DataPermission.role_id == role_id)
    if resource:
        query = query.filter(DataPermission.resource == resource)
    return query.all()


@router.post("/data-permissions", response_model=DataPermissionResponse)
def create_data_permission(
    data: DataPermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """创建数据权限"""
    dp = DataPermission(**data.model_dump())
    db.add(dp)
    db.commit()
    db.refresh(dp)
    return dp


@router.put("/data-permissions/{dp_id}", response_model=DataPermissionResponse)
def update_data_permission(
    dp_id: int,
    data: DataPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """更新数据权限"""
    dp = db.query(DataPermission).filter(DataPermission.id == dp_id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="数据权限不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dp, key, value)

    db.commit()
    db.refresh(dp)
    return dp


@router.delete("/data-permissions/{dp_id}")
def delete_data_permission(
    dp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除数据权限"""
    dp = db.query(DataPermission).filter(DataPermission.id == dp_id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="数据权限不存在")

    db.delete(dp)
    db.commit()
    return {"message": "数据权限已删除"}


# ============ 字段权限路由 ============

@router.get("/field-permissions", response_model=List[FieldPermissionResponse])
def list_field_permissions(
    role_id: Optional[int] = Query(None, description="角色ID"),
    resource: Optional[str] = Query(None, description="资源名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """获取字段权限列表"""
    query = db.query(FieldPermission)
    if role_id:
        query = query.filter(FieldPermission.role_id == role_id)
    if resource:
        query = query.filter(FieldPermission.resource == resource)
    return query.all()


@router.post("/field-permissions", response_model=FieldPermissionResponse)
def create_field_permission(
    data: FieldPermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """创建字段权限"""
    fp = FieldPermission(**data.model_dump())
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


@router.put("/field-permissions/{fp_id}", response_model=FieldPermissionResponse)
def update_field_permission(
    fp_id: int,
    data: FieldPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """更新字段权限"""
    fp = db.query(FieldPermission).filter(FieldPermission.id == fp_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="字段权限不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fp, key, value)

    db.commit()
    db.refresh(fp)
    return fp


@router.delete("/field-permissions/{fp_id}")
def delete_field_permission(
    fp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除字段权限"""
    fp = db.query(FieldPermission).filter(FieldPermission.id == fp_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="字段权限不存在")

    db.delete(fp)
    db.commit()
    return {"message": "字段权限已删除"}


# ============ 获取当前用户权限 ============

@router.get("/my-permissions", response_model=UserPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取当前用户的所有权限"""
    # 获取用户的所有角色
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []

    # 获取所有角色的数据权限
    data_permissions = db.query(DataPermission).filter(DataPermission.role_id.in_(role_ids)).all() if role_ids else []

    # 获取所有角色的字段权限
    field_permissions = db.query(FieldPermission).filter(FieldPermission.role_id.in_(role_ids)).all() if role_ids else []

    # 构建响应
    role_responses = []
    for role in roles:
        role_responses.append({
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "created_at": role.created_at,
            "user_count": len(role.user_roles),
        })

    return {
        "roles": role_responses,
        "data_permissions": data_permissions,
        "field_permissions": field_permissions,
        "is_super_admin": current_user.role == "super_admin",
    }