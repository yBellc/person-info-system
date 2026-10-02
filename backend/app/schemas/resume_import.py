"""简历表导入相关 Pydantic 模型（模块 5）"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class CellMappingItem(BaseModel):
    """字段-单元格映射项"""
    field_name: str
    system_field_key: Optional[str] = None
    label_row: int
    label_col: int
    value_row: int
    value_col: int
    sort: int = 0


class ListGroupColumn(BaseModel):
    """列表组列配置"""
    field_name: str
    system_field_key: Optional[str] = None
    label_row: Optional[int] = None
    label_col: Optional[int] = None
    value_row: int
    value_col: int


class ListGroupItem(BaseModel):
    """列表组配置（子表）"""
    group_name: str
    target_table: Optional[str] = None  # family/work/edu/reward
    columns: list[ListGroupColumn]


class SaveResumeTemplateRequest(BaseModel):
    """保存提取模板"""
    name: str
    file_type: str  # docx/xlsx
    table_index: int = 0
    is_public: bool = False
    cell_mappings: list[CellMappingItem]
    list_groups: list[ListGroupItem] = []


class ResumeTemplateOut(BaseModel):
    """模板输出"""
    id: int
    name: str
    file_type: str
    table_index: int
    is_public: bool
    unit_id: Optional[int] = None
    created_at: datetime
    cell_mappings: list[CellMappingItem] = []
    list_groups: list[ListGroupItem] = []

    class Config:
        from_attributes = True


class ExtractedPerson(BaseModel):
    """提取出的人员数据（待确认入库）"""
    source_file: Optional[str] = None
    status: str = "success"  # success/conflict/failed
    error: Optional[str] = None
    person_id: Optional[int] = None  # 冲突时已存在的person_id
    flat_fields: dict = {}
    sub_tables: dict = {}


class ImportRequest(BaseModel):
    """确认入库请求"""
    unit_id: Optional[int] = None
    persons: list[ExtractedPerson]
