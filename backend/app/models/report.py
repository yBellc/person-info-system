"""统计表模板与字段映射模型（模块 3）"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class ReportTemplate(Base):
    """统计表模板 - 上级下发的固定格式 Excel"""

    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    file_path = Column(String(500), nullable=False, comment="Excel 文件存储路径")
    header_row = Column(Integer, default=1, nullable=False, comment="表头所在行号")
    data_start_row = Column(Integer, default=2, nullable=False, comment="数据起始行")
    data_start_col = Column(Integer, default=1, nullable=False, comment="数据起始列")
    is_public = Column(Boolean, default=False, nullable=False, comment="是否公开模板（超管建的公开）")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="所属单位（私有模板）")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    mappings = relationship("TemplateFieldMapping", back_populates="template", cascade="all, delete-orphan")


class TemplateFieldMapping(Base):
    """模板字段映射 - 模板单元格位置 → 系统字段"""

    __tablename__ = "template_field_mappings"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False, index=True)
    col_index = Column(Integer, nullable=False, comment="列序号(0-based)")
    template_field_name = Column(String(100), nullable=False, comment="模板表头原文")
    system_field_key = Column(String(100), nullable=True, comment="映射的系统字段key")
    confidence = Column(Float, default=0.0, nullable=False, comment="自动匹配置信度")
    confirmed = Column(Boolean, default=False, nullable=False, comment="是否人工确认")

    template = relationship("ReportTemplate", back_populates="mappings")
