# -*- coding: utf-8 -*-
"""智能表格模型：文档识别 → 在线表单 → 下发收集 → 自动汇总"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship

from app.database import Base


class SmartForm(Base):
    """智能表格（模板）"""
    __tablename__ = "smart_forms"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="表单标题")
    description = Column(Text, nullable=True, comment="表单说明")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="创建人")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="所属单位")

    source_filename = Column(String(255), nullable=True, comment="原始文件名")
    source_type = Column(String(10), nullable=True, comment="源文件类型: docx/pdf/xlsx")
    source_file_path = Column(String(500), nullable=True, comment="原始文件存储路径")
    preview_text = Column(Text, nullable=True, comment="原文预览文本（前2000字）")

    status = Column(String(20), default="draft", nullable=False, comment="状态: draft/active/closed")
    deadline = Column(DateTime, nullable=True, comment="默认截止时间")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = relationship("SmartFormField", back_populates="form", cascade="all, delete-orphan",
                          order_by="SmartFormField.sort_order")
    distributions = relationship("SmartFormDistribution", back_populates="form", cascade="all, delete-orphan")


class SmartFormField(Base):
    """智能表格字段"""
    __tablename__ = "smart_form_fields"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("smart_forms.id", ondelete="CASCADE"), nullable=False, index=True)

    field_key = Column(String(50), nullable=False, comment="字段标识")
    field_label = Column(String(100), nullable=False, comment="字段标签/显示名")
    field_type = Column(String(20), default="text", nullable=False,
                        comment="类型: text/number/date/textarea/select/radio/checkbox")
    field_options = Column(JSON, nullable=True, comment="选项列表(select/radio/checkbox用)")
    is_required = Column(Boolean, default=False, comment="是否必填")
    is_readonly = Column(Boolean, default=False, comment="是否只读(自动填充字段)")
    auto_fill_key = Column(String(50), nullable=True, comment="自动填充的系统字段key, 如name/gender")
    default_value = Column(String(500), nullable=True, comment="默认值")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序")
    placeholder = Column(String(200), nullable=True, comment="输入提示")
    source_cell_path = Column(String(200), nullable=True, comment="源文件中的单元格路径，如 table:0,row:2,col:1 或 sheet:Sheet1,row:5,col:2")

    form = relationship("SmartForm", back_populates="fields")


class SmartFormDistribution(Base):
    """表单下发任务"""
    __tablename__ = "smart_form_distributions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("smart_forms.id", ondelete="CASCADE"), nullable=False, index=True)
    distributor_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="下发人")

    title = Column(String(200), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务说明")
    deadline = Column(DateTime, nullable=True, comment="截止时间")

    target_type = Column(String(20), nullable=False, comment="下发范围: all/department/individual")
    target_ids = Column(JSON, nullable=True, comment="目标ID列表(部门ID或用户ID)")

    status = Column(String(20), default="collecting", nullable=False, comment="状态: collecting/closed")
    total_count = Column(Integer, default=0, nullable=False, comment="下发总数")
    submitted_count = Column(Integer, default=0, nullable=False, comment="已提交数")

    created_at = Column(DateTime, default=datetime.utcnow)

    form = relationship("SmartForm", back_populates="distributions")
    tasks = relationship("SmartFormTask", back_populates="distribution", cascade="all, delete-orphan")


class SmartFormTask(Base):
    """个人填写任务"""
    __tablename__ = "smart_form_tasks"

    id = Column(Integer, primary_key=True, index=True)
    distribution_id = Column(Integer, ForeignKey("smart_form_distributions.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    form_id = Column(Integer, ForeignKey("smart_forms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="被分配人")
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, comment="关联人员档案")

    status = Column(String(20), default="pending", nullable=False, comment="状态: pending/submitted/returned")
    response_data = Column(JSON, nullable=True, comment="填写的数据 {field_key: value}")

    assigned_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    return_note = Column(Text, nullable=True, comment="退回说明")

    distribution = relationship("SmartFormDistribution", back_populates="tasks")
    form = relationship("SmartForm")
