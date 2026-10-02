# -*- coding: utf-8 -*-
"""报销管理 Schemas"""
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    instance_id: int
    filename: str
    stored_filename: Optional[str] = None
    file_size: int = 0
    file_type: Optional[str] = None
    attachment_type: Optional[str] = None
    is_invoice: bool = False
    uploaded_by: Optional[int] = None
    created_at: Optional[datetime] = None
    download_url: Optional[str] = None


class InvoiceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    attachment_id: Optional[int] = None
    instance_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_code: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    seller_name: Optional[str] = None
    seller_tax_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    invoice_type: Optional[str] = None
    is_verified: bool = False
    verify_result: Optional[str] = None
    is_duplicate: bool = False
    ocr_raw_text: Optional[str] = None
    parsed_data: Optional[dict] = None
    created_at: Optional[datetime] = None


class VoucherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    instance_id: int
    voucher_number: str
    voucher_date: str
    voucher_type: str
    summary: Optional[str] = None
    total_amount: float = 0
    debit_items: Optional[list] = None
    credit_items: Optional[list] = None
    status: str = "draft"
    created_at: Optional[datetime] = None


class InvoiceOCRResponse(BaseModel):
    """OCR识别结果"""
    success: bool
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None
    seller_name: Optional[str] = None
    buyer_name: Optional[str] = None
    invoice_type: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0
    message: Optional[str] = None


class InvoiceVerifyRequest(BaseModel):
    """发票验真请求"""
    invoice_number: str
    invoice_code: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None


class VoucherGenerateRequest(BaseModel):
    """凭证生成请求"""
    instance_id: int
    voucher_date: Optional[str] = None
    voucher_type: str = "转账凭证"
    summary: Optional[str] = None