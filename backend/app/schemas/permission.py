"""权限 Schemas"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    """角色基础信息"""
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool = True


class RoleCreate(RoleBase):
    """创建角色"""
    pass


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """角色响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_system: bool = False
    created_at: Optional[datetime] = None
    user_count: int = 0


class UserRoleCreate(BaseModel):
    """创建用户角色关联"""
    user_id: int
    role_id: int
    unit_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class UserRoleResponse(BaseModel):
    """用户角色关联响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role_id: int
    role_name: Optional[str] = None
    role_code: Optional[str] = None
    unit_id: Optional[int] = None
    granted_by: Optional[int] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class DataPermissionBase(BaseModel):
    """数据权限基础信息"""
    role_id: int
    resource: str
    scope: str = "self"
    conditions: Optional[dict] = None


class DataPermissionCreate(DataPermissionBase):
    """创建数据权限"""
    pass


class DataPermissionUpdate(BaseModel):
    """更新数据权限"""
    resource: Optional[str] = None
    scope: Optional[str] = None
    conditions: Optional[dict] = None


class DataPermissionResponse(DataPermissionBase):
    """数据权限响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


class FieldPermissionBase(BaseModel):
    """字段权限基础信息"""
    role_id: int
    resource: str
    field_key: str
    can_read: bool = True
    can_write: bool = False


class FieldPermissionCreate(FieldPermissionBase):
    """创建字段权限"""
    pass


class FieldPermissionUpdate(BaseModel):
    """更新字段权限"""
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None


class FieldPermissionResponse(FieldPermissionBase):
    """字段权限响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


class UserPermissionsResponse(BaseModel):
    """用户权限响应"""
    roles: List[RoleResponse] = []
    data_permissions: List[DataPermissionResponse] = []
    field_permissions: List[FieldPermissionResponse] = []
    is_super_admin: bool = False