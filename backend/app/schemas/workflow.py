"""OA流程引擎 Schemas"""
from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict


# ============ 流程模板 ============

class WorkflowTemplateBase(BaseModel):
    name: str
    code: str
    category: str
    description: Optional[str] = None
    form_schema: Optional[List[dict]] = None
    flow_nodes: Optional[List[dict]] = None
    is_active: bool = True


class WorkflowTemplateCreate(WorkflowTemplateBase):
    pass


class WorkflowTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    form_schema: Optional[List[dict]] = None
    flow_nodes: Optional[List[dict]] = None
    is_active: Optional[bool] = None


class WorkflowTemplateResponse(WorkflowTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ 流程节点记录 ============

class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    instance_id: int
    seq: int
    node_key: str
    node_name: str
    node_type: str
    handler_id: Optional[int] = None
    handler_name: Optional[str] = None
    status: str
    opinion: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ============ 流程实例 ============

class WorkflowInstanceCreate(BaseModel):
    """发起流程"""
    template_id: int
    title: str
    form_data: Optional[dict] = None


class WorkflowInstanceApprove(BaseModel):
    """审批操作"""
    opinion: Optional[str] = None
    action: str  # approve / reject / return (退回修改)


class WorkflowInstanceModify(BaseModel):
    """退回后修改表单重新提交"""
    form_data: Optional[dict] = None
    title: Optional[str] = None


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    applicant_id: int
    applicant_name: Optional[str] = None
    title: str
    form_data: Optional[dict] = None
    status: str
    current_node_key: Optional[str] = None
    current_node_name: Optional[str] = None
    current_handler_id: Optional[int] = None
    current_handler_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    form_schema: Optional[List[dict]] = None
    attachments: Optional[List[dict]] = None
    nodes: List[WorkflowNodeResponse] = []


class WorkflowInstanceListResponse(BaseModel):
    """流程实例列表"""
    items: List[WorkflowInstanceResponse]
    total: int
