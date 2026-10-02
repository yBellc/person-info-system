"""工作台路由 - 待办事项、通知公告"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workspace import TodoItem, Notice, NoticeRead, Message
from app.models.user import Unit, User
from app.services.message_center import send_messages
from app.schemas.workspace import (
    TodoItemCreate, TodoItemUpdate, TodoItemResponse,
    NoticeCreate, NoticeUpdate, NoticeResponse, NoticeListResponse,
    TodoListResponse, WorkspaceStatsResponse,
    MessageResponse, MessageListResponse, MessageStats,
)
from app.core.permissions import require_role
from app.services.message_center import send_message

router = APIRouter(tags=["工作台"])


# ============ 待办事项路由 ============

@router.get("/todos", response_model=TodoListResponse)
def list_my_todos(
    status: Optional[str] = Query(None, description="状态: pending/done/expired"),
    category: Optional[str] = Query(None, description="分类"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取我的待办列表（支持分页）"""
    query = db.query(TodoItem).filter(TodoItem.user_id == current_user.id)
    if status:
        query = query.filter(TodoItem.status == status)
    if category:
        query = query.filter(TodoItem.category == category)

    # 过期自动标记
    now = datetime.utcnow()
    expired_todos = query.filter(TodoItem.status == "pending", TodoItem.due_date < now).all()
    for todo in expired_todos:
        todo.status = "expired"
    if expired_todos:
        db.commit()

    # 总数
    total = query.count()
    # 分页查询
    todos = (
        query.order_by(TodoItem.priority.desc(), TodoItem.due_date.asc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    pending_count = db.query(TodoItem).filter(
        TodoItem.user_id == current_user.id,
        TodoItem.status == "pending",
    ).count()

    return {
        "items": todos,
        "total": total,
        "pending_count": pending_count,
        "page": page,
        "size": size,
    }


@router.post("/todos", response_model=TodoItemResponse)
def create_todo(
    data: TodoItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """创建待办事项"""
    todo = TodoItem(
        user_id=current_user.id,
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(todo)
    send_message(db, todo.user_id, msg_type="todo", title=f"新的待办: {todo.title}", content=todo.content or "您有一条新的待办事项", resource_type="todo" if not todo.resource_type else todo.resource_type, resource_id=todo.resource_id, sender_id=current_user.id, extra={"router": "/todos"})
    db.commit()
    db.refresh(todo)
    return todo


@router.put("/todos/{todo_id}", response_model=TodoItemResponse)
def update_todo(
    todo_id: int,
    data: TodoItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """更新待办事项"""
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.user_id == current_user.id,
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] == "done":
        update_data["completed_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(todo, key, value)

    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """删除待办事项"""
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.user_id == current_user.id,
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    db.delete(todo)
    db.commit()
    return {"message": "待办事项已删除"}


@router.post("/todos/{todo_id}/complete", response_model=TodoItemResponse)
def complete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """完成待办事项"""
    todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.user_id == current_user.id,
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    todo.status = "done"
    todo.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(todo)
    return todo


# ============ 通知公告路由 ============

@router.get("/notices", response_model=NoticeListResponse)
def list_notices(
    category: Optional[str] = Query(None, description="分类"),
    is_top: Optional[bool] = Query(None, description="是否置顶"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取通知列表"""
    query = db.query(Notice).filter(Notice.is_published == True)
    if category:
        query = query.filter(Notice.category == category)
    if is_top is not None:
        query = query.filter(Notice.is_top == is_top)

    total = query.count()
    notices = query.order_by(Notice.is_top.desc(), Notice.published_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # 获取未读数量
    unread_count = db.query(Notice).filter(
        Notice.is_published == True,
        Notice.id.notin_(
            db.query(NoticeRead.notice_id).filter(NoticeRead.user_id == current_user.id)
        ),
    ).count()

    # 获取阅读记录
    notice_ids = [n.id for n in notices]
    read_records = db.query(NoticeRead).filter(
        NoticeRead.notice_id.in_(notice_ids),
    ).all() if notice_ids else []

    read_map = {}
    for rr in read_records:
        read_map[rr.notice_id] = True

    # 构建响应
    items = []
    for notice in notices:
        publisher = db.query(User).filter(User.id == notice.publisher_id).first()
        notice_dict = {
            "id": notice.id,
            "title": notice.title,
            "content": notice.content,
            "category": notice.category,
            "publisher_id": notice.publisher_id,
            "publisher_name": publisher.username if publisher else None,
            "is_top": notice.is_top,
            "is_published": notice.is_published,
            "published_at": notice.published_at,
            "attachments": notice.attachments,
            "created_at": notice.created_at,
            "updated_at": notice.updated_at,
            "is_read": notice.id in read_map,
            "read_count": db.query(NoticeRead).filter(NoticeRead.notice_id == notice.id).count(),
            "total_count": total,
        }
        items.append(notice_dict)

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
    }


@router.post("/notices", response_model=NoticeResponse)
def create_notice(
    data: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """创建通知公告"""
    notice = Notice(
        publisher_id=current_user.id,
        **data.model_dump(),
    )
    if data.is_published:
        notice.published_at = datetime.utcnow()
    db.add(notice)
    if data.is_published:
        db.flush()
        users = db.query(User).filter(User.is_active == True).all()
        user_ids = [u.id for u in users]
        content = notice.content[:100] if notice.content else None
        send_messages(db, user_ids, msg_type="notice", title=notice.title, content=content, resource_type="notice", resource_id=notice.id, sender_id=current_user.id, extra={"router": "/notices"})
    db.commit()
    db.refresh(notice)
    return notice


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
def update_notice(
    notice_id: int,
    data: NoticeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """更新通知公告"""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="通知公告不存在")
    if notice.publisher_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权限修改此通知")

    update_data = data.model_dump(exclude_unset=True)
    if "is_published" in update_data and update_data["is_published"] and not notice.published_at:
        update_data["published_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(notice, key, value)

    if "is_published" in update_data and update_data["is_published"] and "published_at" in update_data:
        users = db.query(User).filter(User.is_active == True).all()
        user_ids = [u.id for u in users]
        content = notice.content[:100] if notice.content else None
        send_messages(db, user_ids, msg_type="notice", title=notice.title, content=content, resource_type="notice", resource_id=notice.id, sender_id=current_user.id, extra={"router": "/notices"})

    db.commit()
    db.refresh(notice)
    return notice


@router.delete("/notices/{notice_id}")
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """删除通知公告"""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="通知公告不存在")
    if notice.publisher_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权限删除此通知")

    db.delete(notice)
    db.commit()
    return {"message": "通知公告已删除"}


@router.post("/notices/{notice_id}/read")
def mark_notice_as_read(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """标记通知为已读"""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="通知公告不存在")

    # 检查是否已读
    existing = db.query(NoticeRead).filter(
        NoticeRead.notice_id == notice_id,
        NoticeRead.user_id == current_user.id,
    ).first()
    if existing:
        return {"message": "已标记为已读"}

    read_record = NoticeRead(
        notice_id=notice_id,
        user_id=current_user.id,
    )
    db.add(read_record)
    db.commit()
    return {"message": "已标记为已读"}


@router.post("/notices/read-all")
def mark_all_notices_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """标记所有通知为已读"""
    unread_notices = db.query(Notice).filter(
        Notice.is_published == True,
        Notice.id.notin_(
            db.query(NoticeRead.notice_id).filter(NoticeRead.user_id == current_user.id)
        ),
    ).all()

    for notice in unread_notices:
        read_record = NoticeRead(
            notice_id=notice.id,
            user_id=current_user.id,
        )
        db.add(read_record)

    db.commit()
    return {"message": f"已标记 {len(unread_notices)} 条通知为已读"}


# ============ 工作台统计 ============

@router.get("/stats", response_model=WorkspaceStatsResponse)
def get_workspace_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取工作台统计数据"""
    # 待办统计
    pending_todos = db.query(TodoItem).filter(
        TodoItem.user_id == current_user.id,
        TodoItem.status == "pending",
    ).count()

    urgent_todos = db.query(TodoItem).filter(
        TodoItem.user_id == current_user.id,
        TodoItem.status == "pending",
        TodoItem.priority >= 1,
    ).count()

    # 未读通知
    unread_notices = db.query(Notice).filter(
        Notice.is_published == True,
        Notice.id.notin_(
            db.query(NoticeRead.notice_id).filter(NoticeRead.user_id == current_user.id)
        ),
    ).count()

    # 最近活动
    recent_notices = db.query(Notice).filter(Notice.is_published == True).order_by(
        Notice.published_at.desc()
    ).limit(5).all()

    recent_activities = []
    for notice in recent_notices:
        publisher = db.query(User).filter(User.id == notice.publisher_id).first()
        recent_activities.append({
            "type": "notice",
            "id": notice.id,
            "title": notice.title,
            "publisher": publisher.username if publisher else "系统",
            "time": notice.published_at.isoformat() if notice.published_at else None,
        })

    return {
        "pending_todos": pending_todos,
        "urgent_todos": urgent_todos,
        "unread_notices": unread_notices,
        "my_approvals": 0,  # 待流程引擎实现后对接
        "recent_activities": recent_activities,
    }


# ============ 消息中心路由 ============

@router.get("/messages", response_model=MessageListResponse)
def list_my_messages(
    msg_type: Optional[str] = Query(None, description="消息类型"),
    is_read: Optional[bool] = Query(None, description="是否已读"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    page: int = Query(1, ge=1, description="页码"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取我的消息列表"""
    query = db.query(Message).filter(Message.user_id == current_user.id)
    if msg_type:
        query = query.filter(Message.msg_type == msg_type)
    if is_read is not None:
        query = query.filter(Message.is_read == is_read)

    total = query.count()
    messages = query.order_by(Message.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    unread_count = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
    ).count()

    sender_ids = [m.sender_id for m in messages if m.sender_id]
    senders = db.query(User).filter(User.id.in_(sender_ids)).all() if sender_ids else []
    sender_map = {u.id: u.username for u in senders}

    items = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "user_id": msg.user_id,
            "msg_type": msg.msg_type,
            "title": msg.title,
            "content": msg.content,
            "resource_type": msg.resource_type,
            "resource_id": msg.resource_id,
            "extra": msg.extra,
            "sender_id": msg.sender_id,
            "sender_name": sender_map.get(msg.sender_id) if msg.sender_id else None,
            "is_read": msg.is_read,
            "read_at": msg.read_at,
            "created_at": msg.created_at,
        }
        items.append(msg_dict)

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
    }


@router.get("/messages/stats", response_model=MessageStats)
def get_message_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取当前用户消息统计"""
    total = db.query(Message).filter(Message.user_id == current_user.id).count()
    unread = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
    ).count()

    by_type = {
        "notice": 0,
        "approval": 0,
        "smart_form": 0,
        "todo": 0,
        "mention": 0,
        "system": 0,
    }
    unread_by_type = db.query(
        Message.msg_type,
        func.count(Message.id)
    ).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
    ).group_by(Message.msg_type).all()

    for msg_type, cnt in unread_by_type:
        if msg_type in by_type:
            by_type[msg_type] = cnt
        else:
            by_type[msg_type] = cnt

    return {
        "total": total,
        "unread": unread,
        "by_type": by_type,
    }


@router.get("/messages/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取未读消息数量（顶部铃铛轮询）"""
    unread_count = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
    ).count()
    return {"unread_count": unread_count}


@router.put("/messages/{msg_id}/read", response_model=MessageResponse)
def mark_message_as_read(
    msg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """标记单条消息为已读（只能标记自己的消息）"""
    msg = db.query(Message).filter(
        Message.id == msg_id,
        Message.user_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    if not msg.is_read:
        msg.is_read = True
        msg.read_at = datetime.utcnow()
        db.commit()
        db.refresh(msg)

    sender = db.query(User).filter(User.id == msg.sender_id).first() if msg.sender_id else None

    return {
        "id": msg.id,
        "user_id": msg.user_id,
        "msg_type": msg.msg_type,
        "title": msg.title,
        "content": msg.content,
        "resource_type": msg.resource_type,
        "resource_id": msg.resource_id,
        "extra": msg.extra,
        "sender_id": msg.sender_id,
        "sender_name": sender.username if sender else None,
        "is_read": msg.is_read,
        "read_at": msg.read_at,
        "created_at": msg.created_at,
    }


@router.put("/messages/read-all")
def mark_all_messages_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """将所有未读消息标记为已读"""
    unread_msgs = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.is_read == False,
    ).all()

    now = datetime.utcnow()
    for msg in unread_msgs:
        msg.is_read = True
        msg.read_at = now

    db.commit()
    return {"marked": len(unread_msgs)}


@router.delete("/messages/{msg_id}")
def delete_message(
    msg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """删除自己的一条消息"""
    msg = db.query(Message).filter(
        Message.id == msg_id,
        Message.user_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    db.delete(msg)
    db.commit()
    return {"success": True}