"""OA流程引擎模型 - 流程模板、流程实例、流程节点"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class WorkflowTemplate(Base):
    """流程模板"""

    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="流程名称")
    code = Column(String(50), unique=True, nullable=False, comment="流程编码")
    category = Column(String(50), nullable=False, comment="流程类别: leave/expense/seal/travel")
    description = Column(Text, nullable=True, comment="流程描述")
    form_schema = Column(JSON, nullable=True, comment="表单字段定义(JSON)")
    flow_nodes = Column(JSON, nullable=True, comment="流程节点配置(JSON)")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    instances = relationship("WorkflowInstance", back_populates="template")

    def __repr__(self):
        return f"<WorkflowTemplate {self.name}>"


class WorkflowInstance(Base):
    """流程实例"""

    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("workflow_templates.id"), nullable=False, index=True, comment="模板ID")
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="申请人ID")
    title = Column(String(200), nullable=False, comment="申请标题")
    form_data = Column(JSON, nullable=True, comment="表单数据")
    status = Column(String(20), default="draft", nullable=False, comment="状态: draft/pending/approved/rejected/withdrawn")
    current_node_key = Column(String(50), nullable=True, comment="当前节点key")
    current_node_name = Column(String(100), nullable=True, comment="当前节点名称")
    current_handler_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="当前处理人ID")
    submitted_at = Column(DateTime, nullable=True, comment="提交时间")
    finished_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    template = relationship("WorkflowTemplate", back_populates="instances")
    applicant = relationship("User", foreign_keys=[applicant_id])
    current_handler = relationship("User", foreign_keys=[current_handler_id])
    nodes = relationship("WorkflowNode", back_populates="instance", cascade="all, delete-orphan", order_by="WorkflowNode.seq")

    def __repr__(self):
        return f"<WorkflowInstance {self.title}>"


class WorkflowNode(Base):
    """流程节点记录"""

    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=False, index=True, comment="流程实例ID")
    seq = Column(Integer, default=0, nullable=False, comment="节点序号")
    node_key = Column(String(50), nullable=False, comment="节点key")
    node_name = Column(String(100), nullable=False, comment="节点名称")
    node_type = Column(String(20), default="approval", nullable=False, comment="节点类型: start/approval/end")
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="处理人ID")
    status = Column(String(20), default="pending", nullable=False, comment="状态: pending/approved/rejected/skipped")
    opinion = Column(Text, nullable=True, comment="审批意见")
    handled_at = Column(DateTime, nullable=True, comment="处理时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    instance = relationship("WorkflowInstance", back_populates="nodes")
    handler = relationship("User", foreign_keys=[handler_id])

    def __repr__(self):
        return f"<WorkflowNode {self.node_name} status={self.status}>"
