"""工作台模型 - 待办事项、通知公告"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class TodoItem(Base):
    """待办事项表"""

    __tablename__ = "todo_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID")
    title = Column(String(200), nullable=False, comment="待办标题")
    content = Column(Text, nullable=True, comment="待办内容")
    category = Column(String(50), nullable=True, comment="分类: approval/notification/task")
    resource_type = Column(String(50), nullable=True, comment="关联资源类型")
    resource_id = Column(Integer, nullable=True, comment="关联资源ID")
    priority = Column(Integer, default=0, nullable=False, comment="优先级: 0-普通 1-重要 2-紧急")
    status = Column(String(20), default="pending", nullable=False, comment="状态: pending/done/expired")
    due_date = Column(DateTime, nullable=True, comment="截止日期")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="todo_items")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<TodoItem {self.title[:20]}...>"


class Notice(Base):
    """通知公告表"""

    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, nullable=True, comment="通知内容(支持HTML)")
    category = Column(String(50), nullable=False, default="notification", comment="分类: notification/announcement/news")
    publisher_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="发布人ID")
    is_top = Column(Boolean, default=False, nullable=False, comment="是否置顶")
    is_published = Column(Boolean, default=False, nullable=False, comment="是否已发布")
    published_at = Column(DateTime, nullable=True, comment="发布时间")
    attachments = Column(JSON, nullable=True, comment="附件列表")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    publisher = relationship("User", foreign_keys=[publisher_id])
    read_records = relationship("NoticeRead", back_populates="notice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notice {self.title[:20]}...>"


class NoticeRead(Base):
    """通知阅读记录表"""

    __tablename__ = "notice_reads"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(Integer, ForeignKey("notices.id"), nullable=False, index=True, comment="通知ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="阅读时间")

    notice = relationship("Notice", back_populates="read_records")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<NoticeRead notice={self.notice_id} user={self.user_id}>"


class Message(Base):
    """统一站内消息中心表

    整合：通知公告、待办、审批提醒、智能表格填写任务、@我 等各类消息
    统一入口：顶部铃铛 / 消息中心页面
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="接收用户ID")

    # 消息类型：notice（通知公告）/ approval（审批待办）/ smart_form（智能表格任务）/ todo（待办新增）/ mention（@我）/ system（系统消息）
    msg_type = Column(String(32), nullable=False, index=True, comment="消息类型")

    title = Column(String(200), nullable=False, comment="消息标题")
    content = Column(Text, nullable=True, comment="消息摘要")

    # 关联资源：前端点击跳转时使用
    resource_type = Column(String(50), nullable=True, comment="关联资源类型: notice/workflow/smart_form/todo")
    resource_id = Column(Integer, nullable=True, comment="关联资源ID")
    extra = Column(JSON, nullable=True, comment="扩展数据（如跳转路由路径）")

    # 状态
    is_read = Column(Boolean, default=False, nullable=False, index=True, comment="是否已读")
    read_at = Column(DateTime, nullable=True, comment="阅读时间")

    # 消息来源（谁触发的）
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="发送人ID")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id], backref="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message user={self.user_id} type={self.msg_type} read={self.is_read} title={self.title[:20]}>"