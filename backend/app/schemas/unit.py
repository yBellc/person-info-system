"""单位相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UnitBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[int] = None
    is_active: bool = True


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class UnitOut(UnitBase):
    id: int
    created_at: datetime
    parent_name: Optional[str] = None

    class Config:
        from_attributes = True


class RosterItem(BaseModel):
    """名单条目"""
    name: str
    id_card: str


class RosterBatchCreate(BaseModel):
    """批量导入名单"""
    items: list[RosterItem]


class RosterOut(BaseModel):
    id: int
    name: str
    id_card_masked: str
    is_registered: bool
    unit_id: int

    class Config:
        from_attributes = True
