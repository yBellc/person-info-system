"""安全与假期模型 - 登录日志、假期余额"""
from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class LoginLog(Base):
    """登录日志 - 安全审计"""

    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="用户ID(不存在时为null)")
    username = Column(String(50), nullable=False, comment="尝试登录的用户名")
    ip_address = Column(String(50), nullable=True, comment="登录IP")
    user_agent = Column(String(500), nullable=True, comment="浏览器UA")
    success = Column(Boolean, default=False, nullable=False, comment="是否成功")
    fail_reason = Column(String(200), nullable=True, comment="失败原因")
    login_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="登录时间")
    logout_time = Column(DateTime, nullable=True, comment="登出时间")


class LeaveBalance(Base):
    """假期余额 - 每人每年每种假期类型一条"""

    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("user_id", "year", "leave_type", name="uq_user_year_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    year = Column(Integer, nullable=False, index=True, comment="年度")
    leave_type = Column(String(20), nullable=False, comment="假期类型: annual/sick/personal/marriage/maternity/compassionate")
    total_days = Column(Float, default=0, nullable=False, comment="总天数")
    used_days = Column(Float, default=0, nullable=False, comment="已用天数")
    remaining_days = Column(Float, default=0, nullable=False, comment="剩余天数")
    note = Column(String(200), nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LeaveRecord(Base):
    """请假记录 - 关联流程实例和余额扣减"""

    __tablename__ = "leave_records"

    id = Column(Integer, primary_key=True, index=True)
    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=False, index=True, comment="流程实例ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="申请人ID")
    leave_type = Column(String(20), nullable=False, comment="假期类型")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    days = Column(Float, nullable=False, comment="请假天数")
    deducted = Column(Boolean, default=False, nullable=False, comment="是否已扣减余额")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
