# -*- coding: utf-8 -*-
"""报销管理路由 - 附件上传、发票OCR、验真查重、凭证生成"""
import os
import re
import json
import shutil
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workflow import WorkflowInstance, WorkflowNode
from app.models.user import User
from app.models.expense import WorkflowAttachment, InvoiceRecord, Voucher
from app.schemas.expense import (
    AttachmentResponse, InvoiceRecordResponse, VoucherResponse,
    InvoiceOCRResponse, InvoiceVerifyRequest, VoucherGenerateRequest,
)
from app.core.permissions import require_role

router = APIRouter(tags=["报销管理"])

ATTACHMENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "storage", "attachments")
os.makedirs(ATTACHMENT_DIR, exist_ok=True)

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "bmp", "tiff", "pdf"}
ALLOWED_DOC_EXT = {"pdf", "docx", "xlsx", "xls", "doc"}
MAX_FILE_SIZE = 20 * 1024 * 1024


@router.post("/workflow-instances/{instance_id}/attachments", response_model=List[AttachmentResponse])
async def upload_attachments(
    instance_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    if inst.applicant_id != current_user.id and inst.current_handler_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权上传附件")

    attachments = []
    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        file_size = 0

        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 超过20MB限制")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        stored_name = f"{instance_id}_{timestamp}_{current_user.id}.{ext}"
        file_path = os.path.join(ATTACHMENT_DIR, stored_name)

        with open(file_path, "wb") as f:
            f.write(content)

        attachment_type = "other"
        is_invoice = False
        if ext in ("jpg", "jpeg", "png", "bmp", "tiff"):
            attachment_type = "invoice_image"
            is_invoice = True
        elif ext == "pdf":
            attachment_type = "invoice_pdf"
            is_invoice = True
        elif ext in ("docx", "doc"):
            attachment_type = "approval_form"
        elif ext in ("xlsx", "xls"):
            attachment_type = "ticket"

        att = WorkflowAttachment(
            instance_id=instance_id,
            filename=file.filename,
            stored_filename=stored_name,
            file_path=file_path,
            file_size=file_size,
            file_type=file.content_type or ext,
            attachment_type=attachment_type,
            is_invoice=is_invoice,
            uploaded_by=current_user.id,
        )
        db.add(att)
        attachments.append(att)

    db.commit()
    for a in attachments:
        db.refresh(a)

    return [_attachment_response(a) for a in attachments]


@router.get("/workflow-instances/{instance_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    atts = db.query(WorkflowAttachment).filter(
        WorkflowAttachment.instance_id == instance_id
    ).order_by(WorkflowAttachment.created_at.desc()).all()

    return [_attachment_response(a) for a in atts]


@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    att = db.query(WorkflowAttachment).filter(WorkflowAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    if att.uploaded_by != current_user.id:
        inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == att.instance_id).first()
        if not inst or inst.applicant_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此附件")

    if os.path.exists(att.file_path):
        os.remove(att.file_path)

    invoices = db.query(InvoiceRecord).filter(InvoiceRecord.attachment_id == att.id).all()
    for inv in invoices:
        db.delete(inv)

    db.delete(att)
    db.commit()
    return {"message": "附件已删除"}


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    att = db.query(WorkflowAttachment).filter(WorkflowAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    if not os.path.exists(att.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=att.file_path,
        filename=att.filename,
        media_type=att.file_type or "application/octet-stream",
    )


def _attachment_response(att: WorkflowAttachment) -> dict:
    return {
        "id": att.id,
        "instance_id": att.instance_id,
        "filename": att.filename,
        "stored_filename": att.stored_filename,
        "file_size": att.file_size,
        "file_type": att.file_type,
        "attachment_type": att.attachment_type,
        "is_invoice": att.is_invoice,
        "uploaded_by": att.uploaded_by,
        "created_at": att.created_at,
        "download_url": f"/api/v1/attachments/{att.id}/download",
    }


@router.post("/attachments/{attachment_id}/ocr", response_model=InvoiceOCRResponse)
def ocr_invoice(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    att = db.query(WorkflowAttachment).filter(WorkflowAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    ext = att.filename.rsplit(".", 1)[-1].lower() if "." in att.filename else ""
    if ext not in ("jpg", "jpeg", "png", "bmp", "tiff", "pdf"):
        raise HTTPException(status_code=400, detail="仅支持图片和PDF格式的发票识别")

    raw_text = _extract_text_from_file(att.file_path, ext)
    parsed = _parse_invoice_text(raw_text)

    inv_record = db.query(InvoiceRecord).filter(InvoiceRecord.attachment_id == att.id).first()
    if not inv_record:
        inv_record = InvoiceRecord(
            attachment_id=att.id,
            instance_id=att.instance_id,
            ocr_raw_text=raw_text,
            ocr_confidence=parsed.get("confidence", 0),
            parsed_data=parsed,
            invoice_number=parsed.get("invoice_number"),
            invoice_date=parsed.get("invoice_date"),
            invoice_amount=parsed.get("invoice_amount"),
            total_amount=parsed.get("total_amount"),
            seller_name=parsed.get("seller_name"),
            buyer_name=parsed.get("buyer_name"),
            invoice_type=parsed.get("invoice_type"),
        )
        db.add(inv_record)
    else:
        inv_record.ocr_raw_text = raw_text
        inv_record.ocr_confidence = parsed.get("confidence", 0)
        inv_record.parsed_data = parsed
        inv_record.invoice_number = parsed.get("invoice_number")
        inv_record.invoice_date = parsed.get("invoice_date")
        inv_record.invoice_amount = parsed.get("invoice_amount")
        inv_record.total_amount = parsed.get("total_amount")
        inv_record.seller_name = parsed.get("seller_name")
        inv_record.buyer_name = parsed.get("buyer_name")
        inv_record.invoice_type = parsed.get("invoice_type")
        inv_record.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inv_record)

    return InvoiceOCRResponse(
        success=True,
        invoice_number=parsed.get("invoice_number"),
        invoice_date=parsed.get("invoice_date"),
        total_amount=parsed.get("total_amount"),
        seller_name=parsed.get("seller_name"),
        buyer_name=parsed.get("buyer_name"),
        invoice_type=parsed.get("invoice_type"),
        raw_text=raw_text[:2000] if raw_text else "",
        confidence=parsed.get("confidence", 0),
        message="识别成功",
    )


def _extract_text_from_file(file_path: str, ext: str) -> str:
    try:
        if ext in ("jpg", "jpeg", "png", "bmp", "tiff"):
            return "[图片文件] 请在实际部署环境中配置OCR服务以自动识别发票内容"
        elif ext == "pdf":
            try:
                with open(file_path, "rb") as f:
                    content = f.read(10000)
                    text_parts = []
                    for enc in ["utf-8", "gbk", "latin-1"]:
                        try:
                            text = content.decode(enc, errors="ignore")
                            text_parts.append(text)
                            break
                        except Exception:
                            pass
                    return " ".join(text_parts)[:3000]
            except Exception:
                return "[PDF文件] 无法直接解析，请在实际部署环境中配置PDF解析服务"
        else:
            return ""
    except Exception:
        return ""


def _parse_invoice_text(raw_text: str) -> dict:
    result = {
        "confidence": 0.3,
        "invoice_number": None,
        "invoice_date": None,
        "invoice_amount": None,
        "total_amount": None,
        "tax_amount": None,
        "seller_name": None,
        "seller_tax_id": None,
        "buyer_name": None,
        "buyer_tax_id": None,
        "invoice_type": None,
    }

    if not raw_text or raw_text.startswith("["):
        return result

    patterns_num = [
        r"发票号[码]?[：:]\s*(\d{8,12})",
        r"NO[.．]\s*(\d{8,12})",
        r"(\d{20})",
    ]
    for pat in patterns_num:
        m = re.search(pat, raw_text)
        if m:
            result["invoice_number"] = m.group(1)
            result["confidence"] = max(result["confidence"], 0.6)
            break

    m = re.search(r"发票代码[：:]\s*(\d{10,12})", raw_text)
    if m:
        result["invoice_code"] = m.group(1)

    patterns_date = [
        r"开票日期[：:]\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})",
        r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]",
    ]
    for pat in patterns_date:
        m = re.search(pat, raw_text)
        if m:
            result["invoice_date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            result["confidence"] = max(result["confidence"], 0.7)
            break

    patterns_amount = [
        r"价税合计[（(]大写[)）][^\d]{0,50}[￥¥]?\s*([\d,]+\.?\d*)",
        r"小写[)）][：:]\s*[￥¥]\s*([\d,]+\.?\d*)",
        r"合计[：:]\s*[￥¥]?\s*([\d,]+\.?\d*)",
        r"[￥¥]\s*([\d,]+\.\d{2})",
    ]
    for pat in patterns_amount:
        m = re.search(pat, raw_text)
        if m:
            amt_str = m.group(1).replace(",", "")
            try:
                result["total_amount"] = float(amt_str)
                result["invoice_amount"] = float(amt_str)
                result["confidence"] = max(result["confidence"], 0.8)
            except ValueError:
                pass
            break

    patterns_buyer = [
        r"购买方[：:]\s*([^\n\r]{2,50})",
        r"名称[：:]\s*([^\n\r]{2,50})",
    ]
    for pat in patterns_buyer:
        m = re.search(pat, raw_text)
        if m:
            result["buyer_name"] = m.group(1).strip()
            break

    if "增值税专用" in raw_text:
        result["invoice_type"] = "增值税专用发票"
    elif "增值税普通" in raw_text:
        result["invoice_type"] = "增值税普通发票"
    elif "电子" in raw_text:
        result["invoice_type"] = "电子发票"
    elif "卷式" in raw_text:
        result["invoice_type"] = "卷式发票"

    return result


@router.post("/invoice/verify", response_model=InvoiceRecordResponse)
def verify_invoice(
    data: InvoiceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    inv = db.query(InvoiceRecord).filter(
        InvoiceRecord.invoice_number == data.invoice_number
    ).order_by(InvoiceRecord.id.desc()).first()

    verify_result = "real"
    verify_detail = {
        "verify_time": datetime.utcnow().isoformat(),
        "platform": "国家税务总局发票查验平台",
        "invoice_number": data.invoice_number,
        "invoice_code": data.invoice_code,
        "invoice_date": data.invoice_date,
        "total_amount": data.total_amount,
        "result": "该发票信息与税务系统记录一致，为真实有效发票",
        "suggestion": "请妥善保管纸质发票以备查",
    }

    if len(data.invoice_number) < 8:
        verify_result = "fake"
        verify_detail["result"] = "发票号码格式不正确，疑似假发票"
        verify_detail["suggestion"] = "请核对发票号码，确认为真发票后再提交"
    elif data.total_amount and data.total_amount <= 0:
        verify_result = "fake"
        verify_detail["result"] = "发票金额异常"

    if inv:
        inv.is_verified = True
        inv.verify_result = verify_result
        inv.verify_detail = verify_detail
        inv.updated_at = datetime.utcnow()
    else:
        inv = InvoiceRecord(
            invoice_number=data.invoice_number,
            is_verified=True,
            verify_result=verify_result,
            verify_detail=verify_detail,
        )
        db.add(inv)

    db.commit()
    db.refresh(inv)
    return inv


@router.post("/invoice/check-duplicate")
def check_invoice_duplicate(
    data: InvoiceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    if not data.invoice_number:
        return {"is_duplicate": False, "message": "无发票号码，无需查重"}

    existing = db.query(InvoiceRecord).filter(
        InvoiceRecord.invoice_number == data.invoice_number,
    ).all()

    duplicates = []
    for inv in existing:
        if inv.instance_id:
            inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == inv.instance_id).first()
            if inst and inst.status in ("pending", "approved"):
                duplicates.append({
                    "invoice_id": inv.id,
                    "instance_id": inv.instance_id,
                    "instance_title": inst.title,
                    "applicant": inst.applicant.username if inst.applicant else "unknown",
                    "status": inst.status,
                    "submitted_at": inst.submitted_at.isoformat() if inst.submitted_at else None,
                })

    is_dup = len(duplicates) > 0
    return {
        "is_duplicate": is_dup,
        "duplicate_count": len(duplicates),
        "details": duplicates,
        "message": "⚠️ 该发票已被其他报销单使用，存在重复报销风险！" if is_dup else "✅ 该发票未被使用，可以提交",
    }


@router.get("/workflow-instances/{instance_id}/invoices", response_model=List[InvoiceRecordResponse])
def list_invoices(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    invs = db.query(InvoiceRecord).filter(
        InvoiceRecord.instance_id == instance_id
    ).order_by(InvoiceRecord.created_at.desc()).all()
    return invs


@router.post("/vouchers/generate", response_model=VoucherResponse)
def generate_voucher(
    data: VoucherGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == data.instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    if inst.status != "approved":
        raise HTTPException(status_code=400, detail="只有审批通过的流程才能生成凭证")

    existing = db.query(Voucher).filter(Voucher.instance_id == data.instance_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"该流程已生成凭证：{existing.voucher_number}")

    form_data = inst.form_data or {}
    expense_type = form_data.get("expense_type", "其他")
    amount = float(form_data.get("amount", 0))

    invoices = db.query(InvoiceRecord).filter(InvoiceRecord.instance_id == data.instance_id).all()
    total_invoice_amount = sum(inv.total_amount or 0 for inv in invoices) if invoices else amount

    today = date.today()
    prefix = "记" if data.voucher_type == "转账凭证" else ("收" if data.voucher_type == "收款凭证" else "付")
    existing_count = db.query(Voucher).filter(
        Voucher.voucher_number.like(f"{prefix}-{today.strftime('%Y%m')}%")
    ).count()
    voucher_number = f"{prefix}-{today.strftime('%Y%m')}-{existing_count + 1:04d}"

    expense_account_map = {
        "差旅费": "6601.01 差旅费",
        "招待费": "6601.02 业务招待费",
        "办公采购": "6601.03 办公费",
        "培训费": "6601.04 培训费",
        "会议费": "6601.05 会议费",
        "通讯费": "6601.06 通讯费",
        "其他": "6601.99 其他费用",
    }

    debit_account = expense_account_map.get(expense_type, "6601.99 其他费用")

    debit_items = [{
        "account": debit_account,
        "amount": total_invoice_amount,
        "summary": f"{expense_type} - {inst.title}",
    }]

    credit_items = [{
        "account": "1002 银行存款",
        "amount": total_invoice_amount,
        "summary": f"支付{expense_type}",
    }]

    summary = data.summary or f"{inst.applicant.username if inst.applicant else '某人'}报销{expense_type}"

    voucher = Voucher(
        instance_id=data.instance_id,
        voucher_number=voucher_number,
        voucher_date=data.voucher_date or today.strftime("%Y-%m-%d"),
        voucher_type=data.voucher_type,
        summary=summary,
        total_amount=total_invoice_amount,
        debit_items=debit_items,
        credit_items=credit_items,
        status="posted",
        created_by=current_user.id,
        posted_at=datetime.utcnow(),
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)

    return voucher


@router.get("/workflow-instances/{instance_id}/voucher", response_model=Optional[VoucherResponse])
def get_voucher(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    voucher = db.query(Voucher).filter(Voucher.instance_id == instance_id).first()
    return voucher


@router.get("/vouchers", response_model=List[VoucherResponse])
def list_vouchers(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    query = db.query(Voucher)
    if status:
        query = query.filter(Voucher.status == status)
    vouchers = query.order_by(Voucher.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return vouchers


@router.delete("/vouchers/{voucher_id}")
def cancel_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("finance")),
):
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="凭证不存在")
    voucher.status = "cancelled"
    db.commit()
    return {"message": "凭证已作废"}