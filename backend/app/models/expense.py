# -*- coding: utf-8 -*-
"""报销管理模型 - 附件、发票、凭证"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from app.database import Base


class WorkflowAttachment(Base):
    """流程附件（关联到流程实例，支持多附件）"""
    __tablename__ = "workflow_attachments"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=False, index=True, comment="流程实例ID")
    filename = Column(String(255), nullable=False, comment="原始文件名")
    stored_filename = Column(String(255), nullable=False, comment="存储后的文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(Integer, default=0, comment="文件大小(字节)")
    file_type = Column(String(100), nullable=True, comment="文件MIME类型")
    attachment_type = Column(String(50), nullable=True, comment="附件类型: invoice/ticket/itinerary/approval_form/other")
    is_invoice = Column(Boolean, default=False, comment="是否为发票文件")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="上传人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    instance = relationship("WorkflowInstance")
    uploader = relationship("User")


class InvoiceRecord(Base):
    """发票记录（OCR识别结果 + 验真状态 + 查重）"""
    __tablename__ = "invoice_records"

    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey("workflow_attachments.id"), nullable=True, index=True, comment="附件ID")
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=True, index=True, comment="流程实例ID")
    invoice_number = Column(String(50), nullable=True, index=True, comment="发票号码")
    invoice_code = Column(String(50), nullable=True, comment="发票代码")
    invoice_date = Column(String(20), nullable=True, comment="开票日期")
    invoice_amount = Column(Float, nullable=True, comment="发票金额(含税)")
    tax_amount = Column(Float, nullable=True, comment="税额")
    total_amount = Column(Float, nullable=True, comment="价税合计")
    seller_name = Column(String(200), nullable=True, comment="销售方名称")
    seller_tax_id = Column(String(50), nullable=True, comment="销售方税号")
    buyer_name = Column(String(200), nullable=True, comment="购买方名称")
    buyer_tax_id = Column(String(50), nullable=True, comment="购买方税号")
    invoice_type = Column(String(50), nullable=True, comment="发票类型: 增值税普通/增值税专用/电子普通等")
    is_verified = Column(Boolean, default=False, comment="是否已验真")
    verify_result = Column(String(20), nullable=True, comment="验真结果: real/fake/unknown")
    verify_detail = Column(JSON, nullable=True, comment="验真详细信息")
    is_duplicate = Column(Boolean, default=False, comment="是否为重复发票")
    duplicate_check_detail = Column(JSON, nullable=True, comment="查重详情")
    ocr_raw_text = Column(Text, nullable=True, comment="OCR原始文本")
    ocr_confidence = Column(Float, nullable=True, comment="OCR置信度")
    parsed_data = Column(JSON, nullable=True, comment="解析后的结构化数据")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    attachment = relationship("WorkflowAttachment")
    instance = relationship("WorkflowInstance")


class Voucher(Base):
    """会计凭证（报销通过后自动生成）"""
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"), nullable=False, index=True, comment="流程实例ID")
    voucher_number = Column(String(50), unique=True, nullable=False, comment="凭证编号")
    voucher_date = Column(String(20), nullable=False, comment="凭证日期")
    voucher_type = Column(String(20), default="转账凭证", comment="凭证类型: 转账/收款/付款")
    summary = Column(String(500), nullable=True, comment="凭证摘要")
    total_amount = Column(Float, nullable=False, default=0, comment="凭证总金额")
    debit_items = Column(JSON, nullable=True, comment="借方科目明细")
    credit_items = Column(JSON, nullable=True, comment="贷方科目明细")
    status = Column(String(20), default="draft", comment="状态: draft/posted/cancelled")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    posted_at = Column(DateTime, nullable=True, comment="过账时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    instance = relationship("WorkflowInstance")
    creator = relationship("User")