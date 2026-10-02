"""在职管理与离职模型：考勤、绩效、奖惩、调岗、合同、离职流程、数据变更复核、工作交接
P0-1 / P0-2 / P0-3 三项核心模型
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Float
from sqlalchemy.orm import relationship

from app.database import Base


# ======================================================================
# 在职管理模型
# ======================================================================

class AttendanceRecord(Base):
    """考勤记录 - 按月记录，支持导入/人工录入"""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True, comment="人员ID")
    year = Column(Integer, nullable=False, index=True, comment="年份")
    month = Column(Integer, nullable=False, index=True, comment="月份 1-12")

    # 出勤统计（天/次）
    work_days = Column(Float, default=0, comment="应出勤天数")
    actual_days = Column(Float, default=0, comment="实出勤天数")
    late_count = Column(Integer, default=0, comment="迟到次数")
    early_leave_count = Column(Integer, default=0, comment="早退次数")
    absenteeism_days = Column(Float, default=0, comment="旷工天数")
    personal_leave_days = Column(Float, default=0, comment="事假天数")
    sick_leave_days = Column(Float, default=0, comment="病假天数")
    annual_leave_days = Column(Float, default=0, comment="年假天数")
    business_trip_days = Column(Float, default=0, comment="出差天数")
    overtime_hours = Column(Float, default=0, comment="加班小时数")

    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")
    __table_args__ = (UniqueConstraint("person_id", "year", "month", name="uq_attendance_person_month"),)


class PerformanceRecord(Base):
    """绩效考核记录 - 季度/年度"""
    __tablename__ = "performance_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True, comment="人员ID")
    period_type = Column(String(20), nullable=False, comment="周期: quarter/year")
    period_name = Column(String(50), nullable=False, comment="周期名称 如 2026Q1/2026年度")
    year = Column(Integer, nullable=True, index=True)

    result = Column(String(20), nullable=True, comment="考核结果: excellent/good/qualified/unqualified 或 优/良/中/差")
    score = Column(Float, nullable=True, comment="考核分数")
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="考核人ID")
    evaluate_date = Column(Date, nullable=True, comment="考核日期")
    feedback = Column(Text, nullable=True, comment="评语/反馈")
    document_no = Column(String(50), nullable=True, comment="考核文号")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person", foreign_keys=[person_id])


class TransferRecord(Base):
    """调岗/调动记录"""
    __tablename__ = "transfer_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True, comment="人员ID")
    transfer_type = Column(String(30), nullable=False,
                           comment="类型: department(调部门)/position(调职务)/rank(调职级)/unit(调单位)/salary(调薪)")

    # 变更前
    from_department = Column(String(100), nullable=True)
    from_position = Column(String(50), nullable=True)
    from_rank = Column(String(50), nullable=True)
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    from_salary = Column(Float, nullable=True, comment="原薪资")

    # 变更后
    to_department = Column(String(100), nullable=True)
    to_position = Column(String(50), nullable=True)
    to_rank = Column(String(50), nullable=True)
    to_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    to_salary = Column(Float, nullable=True, comment="新薪资")

    effective_date = Column(Date, nullable=True, comment="生效日期")
    reason = Column(Text, nullable=True, comment="调动原因")
    approval_authority = Column(String(100), nullable=True, comment="批准机关")
    document_no = Column(String(50), nullable=True, comment="文号")

    # 复核
    is_approved = Column(Boolean, default=False, nullable=False, comment="是否已复核(双人复核)")
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="复核人ID")
    approved_at = Column(DateTime, nullable=True, comment="复核时间")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")


class ContractRecord(Base):
    """合同签订记录"""
    __tablename__ = "contract_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    contract_type = Column(String(30), nullable=True, comment="类型: 劳动合同/聘用合同/借调协议/保密协议 等")
    contract_no = Column(String(50), nullable=True, comment="合同编号")
    start_date = Column(Date, nullable=True, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期")
    term_months = Column(Integer, nullable=True, comment="期限(月)")
    is_open_ended = Column(Boolean, default=False, comment="是否无固定期限")
    sign_date = Column(Date, nullable=True, comment="签订日期")
    status = Column(String(20), default="active", comment="状态: active/expired/terminated/renewed")
    remark = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")


class TrainingRecord(Base):
    """培训记录"""
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    training_name = Column(String(200), nullable=False, comment="培训名称")
    training_type = Column(String(30), nullable=True, comment="入职/在岗/业务/安全/晋升 等")
    organizer = Column(String(100), nullable=True, comment="主办单位")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration_hours = Column(Float, nullable=True, comment="学时")
    training_way = Column(String(20), nullable=True, comment="方式: 线上/线下/脱产/在职")
    result = Column(String(20), nullable=True, comment="结果: 合格/不合格/优秀")
    certificate_no = Column(String(50), nullable=True, comment="证书编号")
    remark = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person")


# ======================================================================
# 离职闭环模型
# ======================================================================

class ResignationApplication(Base):
    """离职申请"""
    __tablename__ = "resignation_applications"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True, comment="离职人员ID")
    applicant_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="申请人账号ID")
    resign_type = Column(String(30), nullable=False, comment="类型: resignation(主动辞职)/retirement(退休)/dismissal(辞退)/transfer_out(调出)/other")
    apply_date = Column(Date, nullable=False, comment="申请日期")
    last_work_date = Column(Date, nullable=True, comment="最后工作日")
    reason = Column(Text, nullable=True, comment="离职原因")

    # 审批
    status = Column(String(20), default="pending", comment="状态: pending/dept_approved/hr_approved/lead_approved/approved/rejected/withdrawn")
    dept_head_opinion = Column(Text, nullable=True, comment="部门负责人意见")
    dept_head_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hr_opinion = Column(Text, nullable=True, comment="人事意见")
    hr_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    lead_opinion = Column(Text, nullable=True, comment="领导意见")
    lead_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_date = Column(DateTime, nullable=True, comment="最终审批通过时间")

    # 是否完成交接
    handover_completed = Column(Boolean, default=False, nullable=False, comment="是否已完成工作交接")
    handover_completed_at = Column(DateTime, nullable=True)

    # 是否停用账号
    account_disabled = Column(Boolean, default=False, nullable=False, comment="是否已停用账号")
    account_disabled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    account_disabled_at = Column(DateTime, nullable=True)

    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person")


class HandoverItem(Base):
    """工作交接项"""
    __tablename__ = "handover_items"

    id = Column(Integer, primary_key=True, index=True)
    resignation_id = Column(Integer, ForeignKey("resignation_applications.id"), nullable=False, index=True, comment="关联离职申请")
    item_category = Column(String(50), nullable=False, comment="类别: 文档/钥匙/设备/账号/工作任务/印章/其他")
    item_name = Column(String(200), nullable=False, comment="交接项目名称")
    item_detail = Column(Text, nullable=True, comment="详细描述/数量")

    # 三方确认
    handover_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="交接人ID")
    receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="接收人ID")
    supervisor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="监交人ID")

    handover_confirmed_at = Column(DateTime, nullable=True)
    receiver_confirmed_at = Column(DateTime, nullable=True)
    supervisor_confirmed_at = Column(DateTime, nullable=True)

    all_confirmed = Column(Boolean, default=False, nullable=False, comment="三方是否都确认")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ======================================================================
# 数据变更双人复核模型
# ======================================================================

KEY_CHANGE_FIELDS = [
    "name", "id_card", "gender", "department", "position", "rank",
    "unit_id", "political_status", "education_level", "degree",
    "join_unit_date", "birth_date", "phone",
]  # 需双人复核的关键字段

class DataChangeReview(Base):
    """关键数据变更复核申请"""
    __tablename__ = "data_change_reviews"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(30), nullable=False, default="person", comment="变更目标类型")
    target_id = Column(Integer, nullable=False, index=True, comment="目标ID")
    target_display = Column(String(200), nullable=True, comment="目标显示名(冗余便于查看)")

    field_changes = Column(JSON, nullable=False, comment="变更字段列表 [{field, old, new, label}]")

    proposer_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="提交人ID")
    proposer_name = Column(String(50), nullable=False)
    proposer_reason = Column(Text, nullable=True, comment="修改原因")
    proposed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="复核人ID")
    reviewer_name = Column(String(50), nullable=True)
    reviewer_opinion = Column(Text, nullable=True, comment="复核意见")
    reviewed_at = Column(DateTime, nullable=True)

    status = Column(String(20), default="pending",
                    comment="状态: pending待审核/approved已批准并生效/rejected已驳回/cancelled已取消")
    applied_at = Column(DateTime, nullable=True, comment="实际写入数据库的时间")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
