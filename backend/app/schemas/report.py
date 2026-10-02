"""报表相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MappingItem(BaseModel):
    col_index: int
    template_name: str
    system_field_key: Optional[str] = None
    confidence: float = 0.0
    confirmed: bool = False


class SaveMappingRequest(BaseModel):
    """保存映射关系"""
    name: str
    header_row: int = 1
    data_start_row: int = 2
    data_start_col: int = 1
    is_public: bool = False
    mappings: list[MappingItem]


class GenerateReportRequest(BaseModel):
    """生成报表"""
    template_id: int
    unit_id: Optional[int] = None


class TemplateOut(BaseModel):
    id: int
    name: str
    header_row: int
    data_start_row: int
    data_start_col: int
    is_public: bool
    unit_id: Optional[int] = None
    created_at: datetime
    mappings: list[MappingItem] = []

    class Config:
        from_attributes = True
