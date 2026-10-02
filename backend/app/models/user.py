"""账号、单位、名单、操作日志模型（模块 1）"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Unit(Base):
    """单位表 - 扁平结构，可选父单位用于汇总"""

    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="单位名称")
    code = Column(String(50), unique=True, nullable=True, comment="单位编码")
    parent_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="父单位ID，用于汇总统计")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    children = relationship("Unit", backref="parent", remote_side=[id])
    users = relationship("User", back_populates="unit")
    persons = relationship("Person", back_populates="unit")
    rosters = relationship("UnitRoster", back_populates="unit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Unit {self.name}>"


class User(Base):
    """账号表 - 三级权限：person / unit_admin / super_admin"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), nullable=False, default="person", comment="角色: person/unit_admin/super_admin")

    # 关联：个人账号关联人员记录；单位管理员/超管关联单位
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, comment="关联人员ID（个人账号）")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="关联单位ID")

    is_active = Column(Boolean, default=True, nullable=False, comment="账号是否启用")
    first_login = Column(Boolean, default=True, nullable=False, comment="是否首次登录(需改密)")

    # === 涉密分级 ===
    clearance_level = Column(Integer, default=0, nullable=False, comment="涉密等级: 0=公开 1=内部 2=秘密 3=机密")

    # === 登录安全 ===
    failed_login_count = Column(Integer, default=0, nullable=False, comment="连续登录失败次数")
    locked_until = Column(DateTime, nullable=True, comment="锁定截止时间")
    password_changed_at = Column(DateTime, nullable=True, comment="最后改密时间")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_password_hashes = Column(JSON, nullable=True, comment="最近5次密码哈希(防重复)")

    # === 软删除 ===
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    deleted_by = Column(Integer, nullable=True, comment="删除人ID")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    unit = relationship("Unit", back_populates="users")
    person = relationship("Person", foreign_keys=[person_id])

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class UnitRoster(Base):
    """单位名单表 - 单位管理员预导入（姓名+身份证），用于用户自助匹配注册"""

    __tablename__ = "unit_rosters"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True, comment="所属单位")
    name = Column(String(50), nullable=False, comment="姓名")
    id_card = Column(String(18), nullable=False, comment="身份证号")
    is_registered = Column(Boolean, default=False, nullable=False, comment="是否已注册")
    registered_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="注册后关联的账号")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    unit = relationship("Unit", back_populates="rosters")

    def __repr__(self):
        return f"<Roster {self.name} {self.id_card[-4:]}>"


class OperationLog(Base):
    """操作日志 - 关键操作审计（调动、修改、导出等）"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="操作人ID")
    operator_name = Column(String(50), nullable=False, comment="操作人用户名（冗余便于查询）")
    action = Column(String(50), nullable=False, comment="操作类型: login/transfer/update/export 等")
    target_type = Column(String(50), nullable=True, comment="目标类型: person/unit 等")
    target_id = Column(Integer, nullable=True, comment="目标ID")
    detail = Column(Text, nullable=True, comment="操作详情")
    ip_address = Column(String(50), nullable=True, comment="操作者IP")
    old_value = Column(JSON, nullable=True, comment="变更前值(JSON)")
    new_value = Column(JSON, nullable=True, comment="变更后值(JSON)")
    extra = Column(JSON, nullable=True, comment="附加数据")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminApplication(Base):
    """管理员申请 - 普通用户申请成为本单位管理员，超管审批"""

    __tablename__ = "admin_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="申请人ID")
    username = Column(String(50), nullable=False, comment="申请人用户名(冗余)")
    target_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, comment="申请管理的单位ID")
    target_unit_name = Column(String(100), nullable=False, comment="申请单位名称(冗余)")
    status = Column(String(20), default="pending", nullable=False, comment="状态: pending/approved/rejected")
    reason = Column(Text, nullable=True, comment="申请理由")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    review_note = Column(Text, nullable=True, comment="审批意见")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True, comment="审批时间")
