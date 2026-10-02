"""权限模型 - 角色、数据权限、字段权限"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    """角色表 - RBAC 角色"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="角色名称")
    code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    description = Column(Text, nullable=True, comment="角色描述")
    is_system = Column(Boolean, default=False, nullable=False, comment="是否系统内置角色(不可删除)")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    level = Column(Integer, default=0, nullable=False, comment="角色等级(数字越小权限越高)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    data_permissions = relationship("DataPermission", back_populates="role", cascade="all, delete-orphan")
    field_permissions = relationship("FieldPermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role {self.name}>"


class UserRole(Base):
    """用户角色关联表"""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True, comment="角色ID")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="关联单位ID(角色在该单位生效)")
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="授权人ID")
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="授权时间")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")

    user = relationship("User", foreign_keys=[user_id], backref="user_roles")
    role = relationship("Role", back_populates="user_roles")
    unit = relationship("Unit")

    def __repr__(self):
        return f"<UserRole user={self.user_id} role={self.role_id}>"


class DataPermission(Base):
    """数据权限表 - 行级权限控制"""

    __tablename__ = "data_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True, comment="角色ID")
    resource = Column(String(50), nullable=False, comment="资源名称: persons/contracts/leaves等")
    scope = Column(String(20), nullable=False, default="self", comment="权限范围: all/unit/department/self")
    conditions = Column(JSON, nullable=True, comment="额外过滤条件")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="data_permissions")

    def __repr__(self):
        return f"<DataPermission role={self.role_id} resource={self.resource} scope={self.scope}>"


class FieldPermission(Base):
    """字段权限表 - 字段级可见/可编辑控制"""

    __tablename__ = "field_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True, comment="角色ID")
    resource = Column(String(50), nullable=False, comment="资源名称: persons等")
    field_key = Column(String(50), nullable=False, comment="字段key")
    can_read = Column(Boolean, default=True, nullable=False, comment="是否可读")
    can_write = Column(Boolean, default=False, nullable=False, comment="是否可写")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="field_permissions")

    def __repr__(self):
        return f"<FieldPermission role={self.role_id} field={self.field_key}>"