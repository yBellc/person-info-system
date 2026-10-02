"""组织架构 Schemas"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DepartmentBase(BaseModel):
    """部门基础信息"""
    unit_id: Optional[int] = None
    parent_id: Optional[int] = None
    name: str
    code: Optional[str] = None
    manager_id: Optional[int] = None
    level: int = 1
    sort: int = 0
    is_active: bool = True
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    """创建部门"""
    pass


class DepartmentUpdate(BaseModel):
    """更新部门"""
    name: Optional[str] = None
    code: Optional[str] = None
    manager_id: Optional[int] = None
    parent_id: Optional[int] = None
    level: Optional[int] = None
    sort: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    """部门响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List["DepartmentResponse"] = []
    manager_name: Optional[str] = None


class DepartmentTreeResponse(BaseModel):
    """部门树响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str] = None
    level: int
    sort: int
    is_active: bool
    children: List["DepartmentTreeResponse"] = []
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    person_count: int = 0


DepartmentResponse.model_rebuild()


class RankBase(BaseModel):
    """职级基础信息"""
    name: str
    code: str
    category: Optional[str] = None
    level: int = 1
    is_active: bool = True
    description: Optional[str] = None


class RankCreate(RankBase):
    """创建职级"""
    pass


class RankUpdate(BaseModel):
    """更新职级"""
    name: Optional[str] = None
    category: Optional[str] = None
    level: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class RankResponse(RankBase):
    """职级响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


class PositionBase(BaseModel):
    """岗位基础信息"""
    name: str
    code: str
    category: Optional[str] = None
    allowed_ranks: Optional[List[int]] = None
    is_leadership: bool = False
    is_active: bool = True
    description: Optional[str] = None


class PositionCreate(PositionBase):
    """创建岗位"""
    pass


class PositionUpdate(BaseModel):
    """更新岗位"""
    name: Optional[str] = None
    category: Optional[str] = None
    allowed_ranks: Optional[List[int]] = None
    is_leadership: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class PositionResponse(PositionBase):
    """岗位响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None


class PersonPositionBase(BaseModel):
    """人员岗位基础信息"""
    person_id: int
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    rank_id: Optional[int] = None
    is_primary: bool = True
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = True
    appointment_no: Optional[str] = None
    remark: Optional[str] = None


class PersonPositionCreate(PersonPositionBase):
    """创建人员岗位"""
    pass


class PersonPositionUpdate(BaseModel):
    """更新人员岗位"""
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    rank_id: Optional[int] = None
    is_primary: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    appointment_no: Optional[str] = None
    remark: Optional[str] = None


class PersonPositionResponse(PersonPositionBase):
    """人员岗位响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    department_name: Optional[str] = None
    position_name: Optional[str] = None
    rank_name: Optional[str] = None