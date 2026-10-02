"""简历表提取模板与映射模型（模块 5）"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class ResumeTemplate(Base):
    """简历提取模板 - 一次配置，批量套用"""

    __tablename__ = "resume_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    file_type = Column(String(10), nullable=False, comment="文件类型: docx/xlsx")
    table_index = Column(Integer, default=0, nullable=False, comment="目标表格序号(0-based)")
    is_public = Column(Boolean, default=False, nullable=False, comment="是否公开模板")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="所属单位(私有模板)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    cell_mappings = relationship("CellMapping", back_populates="template", cascade="all, delete-orphan")
    list_groups = relationship("ListGroupMapping", back_populates="template", cascade="all, delete-orphan")


class CellMapping(Base):
    """字段-单元格映射（扁平字段：标签格 + 值格）"""

    __tablename__ = "resume_cell_mappings"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("resume_templates.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, comment="字段名(取自标签格文本)")
    system_field_key = Column(String(100), nullable=True, comment="映射的系统字段key")
    label_row = Column(Integer, nullable=False, comment="标签格行号(0-based)")
    label_col = Column(Integer, nullable=False, comment="标签格列号(0-based)")
    value_row = Column(Integer, nullable=False, comment="值格行号(0-based)")
    value_col = Column(Integer, nullable=False, comment="值格列号(0-based)")
    sort = Column(Integer, default=0, nullable=False, comment="排序")

    template = relationship("ResumeTemplate", back_populates="cell_mappings")


class ListGroupMapping(Base):
    """列表组映射（子表：如家庭成员/工作经历，多行结构）"""

    __tablename__ = "resume_list_groups"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("resume_templates.id"), nullable=False, index=True)
    group_name = Column(String(50), nullable=False, comment="列表组名称")
    target_table = Column(String(30), nullable=True, comment="目标子表: family/work/edu/reward")
    columns = Column(JSON, nullable=False, comment="列配置: [{field_name, system_field_key, label_row, label_col, value_row, value_col}]")

    template = relationship("ResumeTemplate", back_populates="list_groups")
