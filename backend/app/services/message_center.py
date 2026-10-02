"""消息中心服务 - 统一站内消息发送"""
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.workspace import Message


def send_message(
    db: Session,
    user_id: int,
    msg_type: str,
    title: str,
    content: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    extra: Optional[dict] = None,
    sender_id: Optional[int] = None,
) -> Message:
    """发送单条站内消息

    Args:
        db: 数据库会话
        user_id: 接收用户ID
        msg_type: 消息类型: notice/approval/smart_form/todo/mention/system
        title: 消息标题
        content: 消息摘要
        resource_type: 关联资源类型: notice/workflow/smart_form/todo
        resource_id: 关联资源ID
        extra: 扩展数据（如跳转路由路径）
        sender_id: 发送人ID

    Returns:
        已 add 并 flush 的 Message 对象（未 commit）
    """
    message = Message(
        user_id=user_id,
        msg_type=msg_type,
        title=title,
        content=content,
        resource_type=resource_type,
        resource_id=resource_id,
        extra=extra,
        sender_id=sender_id,
    )
    db.add(message)
    db.flush()
    return message


def send_messages(
    db: Session,
    user_ids: List[int],
    msg_type: str,
    title: str,
    content: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    extra: Optional[dict] = None,
    sender_id: Optional[int] = None,
) -> List[Message]:
    """批量发送站内消息给多个用户

    Args:
        db: 数据库会话
        user_ids: 接收用户ID列表
        msg_type: 消息类型: notice/approval/smart_form/todo/mention/system
        title: 消息标题
        content: 消息摘要
        resource_type: 关联资源类型: notice/workflow/smart_form/todo
        resource_id: 关联资源ID
        extra: 扩展数据（如跳转路由路径）
        sender_id: 发送人ID

    Returns:
        已 add 并 flush 的 Message 对象列表（未 commit）
    """
    messages = []
    for user_id in user_ids:
        message = send_message(
            db=db,
            user_id=user_id,
            msg_type=msg_type,
            title=title,
            content=content,
            resource_type=resource_type,
            resource_id=resource_id,
            extra=extra,
            sender_id=sender_id,
        )
        messages.append(message)
    return messages
