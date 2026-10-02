"""工作台 Schemas"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TodoItemBase(BaseModel):
    """待办事项基础信息"""
    title: str
    content: Optional[str] = None
    category: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    priority: int = 0
    due_date: Optional[datetime] = None


class TodoItemCreate(TodoItemBase):
    """创建待办事项"""
    pass


class TodoItemUpdate(BaseModel):
    """更新待办事项"""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class TodoItemResponse(TodoItemBase):
    """待办事项响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    status: str = "pending"
    completed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None


class NoticeBase(BaseModel):
    """通知公告基础信息"""
    title: str
    content: Optional[str] = None
    category: str = "notification"
    is_top: bool = False
    is_published: bool = False
    attachments: Optional[List[dict]] = None


class NoticeCreate(NoticeBase):
    """创建通知公告"""
    pass


class NoticeUpdate(BaseModel):
    """更新通知公告"""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_top: Optional[bool] = None
    is_published: Optional[bool] = None
    attachments: Optional[List[dict]] = None


class NoticeResponse(NoticeBase):
    """通知公告响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    publisher_id: int
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    publisher_name: Optional[str] = None
    is_read: bool = False
    read_count: int = 0
    total_count: int = 0


class NoticeListResponse(BaseModel):
    """通知列表响应"""
    items: List[NoticeResponse]
    total: int
    unread_count: int


class TodoListResponse(BaseModel):
    """待办列表响应"""
    items: List[TodoItemResponse]
    total: int
    pending_count: int
    page: int = 1
    size: int = 20


class WorkspaceStatsResponse(BaseModel):
    """工作台统计响应"""
    pending_todos: int = 0
    urgent_todos: int = 0
    unread_notices: int = 0
    my_approvals: int = 0
    recent_activities: List[dict] = []


class MessageBase(BaseModel):
    """消息基础信息"""
    msg_type: str
    title: str
    content: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    extra: Optional[dict] = None
    sender_id: Optional[int] = None


class MessageResponse(MessageBase):
    """消息响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    sender_name: Optional[str] = None


class MessageListResponse(BaseModel):
    """消息列表响应"""
    items: List[MessageResponse]
    total: int
    unread_count: int


class MessageStats(BaseModel):
    """消息统计响应"""
    total: int = 0
    unread: int = 0
    by_type: dict = {
        "notice": 0,
        "approval": 0,
        "smart_form": 0,
        "todo": 0,
        "mention": 0,
        "system": 0,
    }