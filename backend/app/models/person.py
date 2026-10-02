"""人员主表、子表、自定义字段模型（模块 2）"""
from datetime import date

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Person(Base):
    """人员主表 - 存核心字段，派生字段（年龄/工龄）实时计算不落库"""

    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True, comment="所属单位")

    # === 基本信息 ===
    name = Column(String(50), nullable=False, index=True, comment="姓名")
    gender = Column(String(10), nullable=True, comment="性别")
    birth_date = Column(Date, nullable=True, index=True, comment="出生日期")
    ethnicity = Column(String(20), nullable=True, comment="民族")
    native_place = Column(String(100), nullable=True, comment="现籍贯")
    birth_place = Column(String(100), nullable=True, comment="出生地")
    id_card = Column(String(18), unique=True, nullable=True, index=True, comment="身份证号")
    political_status = Column(String(20), nullable=True, comment="政治面貌")

    # === 政治面貌详情 ===
    party_join_date = Column(Date, nullable=True, comment="入党时间")
    party_apply_date = Column(Date, nullable=True, comment="申请入党时间")

    # === 联系方式 ===
    phone = Column(String(20), nullable=True, comment="手机号")
    office_phone = Column(String(20), nullable=True, comment="办公电话")
    emergency_contact = Column(String(100), nullable=True, comment="紧急联系人及电话")

    # === 工作信息 ===
    department = Column(String(100), nullable=True, comment="部门")
    position = Column(String(50), nullable=True, comment="职务")
    rank = Column(String(50), nullable=True, comment="职级")
    work_start_date = Column(Date, nullable=True, comment="参加工作时间")
    join_unit_date = Column(Date, nullable=True, comment="入职本单位时间")

    # === 学历学位 ===
    education_level = Column(String(20), nullable=True, comment="最高学历")
    degree = Column(String(20), nullable=True, comment="学位")
    school = Column(String(100), nullable=True, comment="毕业院校")
    major = Column(String(100), nullable=True, comment="所学专业")
    graduation_date = Column(Date, nullable=True, comment="毕业时间")

    # === 家庭信息 ===
    marital_status = Column(String(20), nullable=True, comment="婚姻状况")
    spouse_name = Column(String(50), nullable=True, comment="配偶姓名")
    children_count = Column(Integer, default=0, nullable=True, comment="子女数")
    home_address = Column(Text, nullable=True, comment="家庭住址")

    # === 元数据 ===
    data_status = Column(String(20), default="confirmed", nullable=False, comment="数据状态: draft/confirmed")
    security_level = Column(Integer, default=1, nullable=False, comment="涉密等级: 0=公开 1=内部 2=秘密 3=机密")

    # === 软删除 ===
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    deleted_by = Column(Integer, nullable=True, comment="删除人ID")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=__import__("datetime").datetime.utcnow,
        onupdate=__import__("datetime").datetime.utcnow,
        nullable=False,
    )

    # 关系
    unit = relationship("Unit", back_populates="persons")
    family_members = relationship("FamilyMember", back_populates="person", cascade="all, delete-orphan", order_by="FamilyMember.sort")
    education_records = relationship("EducationRecord", back_populates="person", cascade="all, delete-orphan", order_by="EducationRecord.start_date.desc()")
    work_records = relationship("WorkRecord", back_populates="person", cascade="all, delete-orphan", order_by="WorkRecord.start_date.desc()")
    rewards = relationship("RewardPunishment", back_populates="person", cascade="all, delete-orphan", order_by="RewardPunishment.date.desc()")
    custom_values = relationship("CustomFieldValue", back_populates="person", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Person {self.name}>"


class FamilyMember(Base):
    """家庭主要成员 - 一人多条"""

    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    relation = Column(String(20), nullable=True, comment="称谓")
    name = Column(String(50), nullable=True, comment="姓名")
    birth_date = Column(Date, nullable=True, comment="出生年月")
    political_status = Column(String(20), nullable=True, comment="政治面貌")
    work_info = Column(String(200), nullable=True, comment="工作单位及职务")
    phone = Column(String(20), nullable=True, comment="联系电话")
    sort = Column(Integer, default=0, nullable=False, comment="排序")

    person = relationship("Person", back_populates="family_members")


class EducationRecord(Base):
    """学历经历 - 一人多条，倒序展示"""

    __tablename__ = "education_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=True, comment="开始时间")
    end_date = Column(Date, nullable=True, comment="结束时间")
    school = Column(String(100), nullable=True, comment="学校")
    major = Column(String(100), nullable=True, comment="专业")
    education_level = Column(String(20), nullable=True, comment="学历")
    degree = Column(String(20), nullable=True, comment="学位")
    is_full_time = Column(Boolean, nullable=True, comment="是否全日制")
    sort = Column(Integer, default=0, nullable=False, comment="排序")

    person = relationship("Person", back_populates="education_records")


class WorkRecord(Base):
    """工作经历 - 一人多条，倒序展示"""

    __tablename__ = "work_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=True, comment="开始时间")
    end_date = Column(Date, nullable=True, comment="结束时间")
    unit = Column(String(100), nullable=True, comment="工作单位")
    position = Column(String(50), nullable=True, comment="职务")
    witness = Column(String(50), nullable=True, comment="证明人")
    sort = Column(Integer, default=0, nullable=False, comment="排序")

    person = relationship("Person", back_populates="work_records")


class RewardPunishment(Base):
    """奖惩记录 - 一人多条"""

    __tablename__ = "reward_punishment"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    type = Column(String(20), nullable=True, comment="类型: reward/punishment")
    date = Column(Date, nullable=True, comment="时间")
    name = Column(String(100), nullable=True, comment="名称")
    approval_authority = Column(String(100), nullable=True, comment="批准机关")
    document_no = Column(String(50), nullable=True, comment="文号")
    sort = Column(Integer, default=0, nullable=False, comment="排序")

    person = relationship("Person", back_populates="rewards")


class CustomFieldDefinition(Base):
    """自定义字段定义 - 动态扩展"""

    __tablename__ = "custom_field_definitions"

    id = Column(Integer, primary_key=True, index=True)
    field_key = Column(String(50), unique=True, nullable=False, comment="字段key，英文标识")
    display_name = Column(String(50), nullable=False, comment="显示名")
    data_type = Column(String(20), nullable=False, default="text", comment="类型: text/number/date/select/textarea")
    group_name = Column(String(50), default="自定义", nullable=False, comment="所属分组")
    sort = Column(Integer, default=0, nullable=False, comment="排序")
    is_required = Column(Boolean, default=False, nullable=False, comment="是否必填")
    options = Column(JSON, nullable=True, comment="下拉选项列表")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    security_level = Column(Integer, default=1, nullable=False, comment="涉密等级: 0=公开 1=内部 2=秘密 3=机密")
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow, nullable=False)


class CustomFieldValue(Base):
    """自定义字段值 - 键值对存储，统一存文本按类型解析"""

    __tablename__ = "custom_field_values"
    __table_args__ = (UniqueConstraint("person_id", "field_id", name="uq_person_field"),)

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("custom_field_definitions.id"), nullable=False, index=True)
    value = Column(Text, nullable=True, comment="值，统一存文本")

    person = relationship("Person", back_populates="custom_values")
    field = relationship("CustomFieldDefinition")


class ChangeLog(Base):
    """字段变更历史 - 模块 4 审计追踪"""

    __tablename__ = "change_logs"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_name = Column(String(50), nullable=False, comment="操作人（冗余）")
    field_key = Column(String(50), nullable=False, comment="变更字段")
    change_type = Column(String(20), nullable=False, comment="create/update/delete")
    old_value = Column(Text, nullable=True, comment="旧值")
    new_value = Column(Text, nullable=True, comment="新值")
    reason = Column(String(200), nullable=True, comment="变更原因")
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow, nullable=False)
