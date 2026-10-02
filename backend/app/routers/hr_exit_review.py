"""离职管理 & 数据变更复核（P0-2 / P0-3）
离职审批三级 + 交接三方确认 + 账号停用；关键字段双人复核
"""
from datetime import date as _date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import (
    get_current_user, require_admin, require_super_admin,
    _get_descendant_unit_ids,
)
from app.core.security import hash_password
from app.models.user import User, Unit
from app.models.person import Person
from app.models.hr_management import (
    ResignationApplication, HandoverItem, DataChangeReview, KEY_CHANGE_FIELDS,
)
from app.models.user import OperationLog

router = APIRouter(prefix="/hr-exit", tags=["离职与复核"])


def _log(db, user: User, action: str, detail: str, ttype=None, tid=None,
        old=None, new=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username,
        action=action, target_type=ttype, target_id=tid,
        detail=detail, old_value=old, new_value=new,
    ))


# ======================================================================
# 离职申请
# ======================================================================

RESIGN_STATES = {
    "pending": "待审批",
    "dept_approved": "部门已批",
    "hr_approved": "人事已批",
    "lead_approved": "领导已批",
    "approved": "全部批准",
    "rejected": "已驳回",
    "withdrawn": "已撤回",
}


@router.get("/resignations", summary="离职申请列表")
def list_resignations(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(ResignationApplication)
    if status:
        q = q.filter(ResignationApplication.status == status)
    total = q.count()
    items = q.order_by(ResignationApplication.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "status_label": RESIGN_STATES.get(r.status, r.status),
            "apply_date": r.apply_date.isoformat() if r.apply_date else None,
            "last_work_date": r.last_work_date.isoformat() if r.last_work_date else None,
        })
    return {"total": total, "items": data}


@router.post("/resignations", summary="提交离职申请")
def create_resignation(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pid = data.get("person_id")
    if not pid:
        raise HTTPException(400, "缺少人员ID")
    # 允许员工为自己发起，或管理员为他人发起
    if current_user.role == "person" and current_user.person_id != pid:
        raise HTTPException(403, "普通用户只能为自己申请")

    rec = ResignationApplication(
        status="pending",
        applicant_user_id=current_user.id,
    )
    for fld in ("apply_date", "last_work_date"):
        if data.get(fld) and isinstance(data[fld], str):
            data[fld] = _date.fromisoformat(data[fld][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "updated_at"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(pid)
    _log(db, current_user, "create_resignation",
         f"提交离职申请: {p.name if p else pid} {data.get('resign_type')}",
         target_type="resignation", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已提交"}


@router.post("/resignations/{rid}/dept-approve", summary="部门负责人审批")
def dept_approve(rid: int, payload: dict = Body(...),
                 current_user: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    rec = db.query(ResignationApplication).get(rid)
    if not rec or rec.status != "pending":
        raise HTTPException(400, "状态异常")
    approved = payload.get("approved", True)
    opinion = payload.get("opinion", "")
    rec.dept_head_id = current_user.id
    rec.dept_head_opinion = opinion
    rec.status = "dept_approved" if approved else "rejected"
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "dept_approve_resignation",
         f"部门负责人审批: {p.name if p else rec.person_id} {'通过' if approved else '驳回'}",
         target_type="resignation", target_id=rid)
    db.commit()
    return {"message": "已审批"}


@router.post("/resignations/{rid}/hr-approve", summary="人事审批")
def hr_approve(rid: int, payload: dict = Body(...),
               current_user: User = Depends(require_admin),
               db: Session = Depends(get_db)):
    rec = db.query(ResignationApplication).get(rid)
    if not rec or rec.status != "dept_approved":
        raise HTTPException(400, "需先通过部门负责人审批")
    approved = payload.get("approved", True)
    opinion = payload.get("opinion", "")
    rec.hr_id = current_user.id
    rec.hr_opinion = opinion
    rec.status = "hr_approved" if approved else "rejected"
    db.commit()
    return {"message": "已审批"}


@router.post("/resignations/{rid}/lead-approve", summary="领导最终审批")
def lead_approve(rid: int, payload: dict = Body(...),
                 current_user: User = Depends(require_super_admin),
                 db: Session = Depends(get_db)):
    rec = db.query(ResignationApplication).get(rid)
    if not rec or rec.status != "hr_approved":
        raise HTTPException(400, "需先通过人事审批")
    approved = payload.get("approved", True)
    opinion = payload.get("opinion", "")
    rec.lead_id = current_user.id
    rec.lead_opinion = opinion
    if approved:
        rec.status = "approved"
        rec.approved_date = datetime.utcnow()
        # 若离职日期已过，自动标记为交接待办
    else:
        rec.status = "rejected"
    _log(db, current_user, "lead_approve_resignation",
         f"领导最终审批离职: id={rid} {'通过' if approved else '驳回'}",
         target_type="resignation", target_id=rid)
    db.commit()
    return {"message": "已审批"}


@router.post("/resignations/{rid}/disable-account",
             summary="离职完成：停用关联账号（仅超管）")
def disable_resignation_account(
    rid: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(ResignationApplication).get(rid)
    if not rec:
        raise HTTPException(404, "申请不存在")
    if rec.status != "approved":
        raise HTTPException(400, "需最终审批通过")
    if not rec.handover_completed:
        raise HTTPException(400, "需先完成工作交接")
    if rec.account_disabled:
        raise HTTPException(400, "账号已停用")

    # 停用 person_id 关联的 user 账号
    user = db.query(User).filter(User.person_id == rec.person_id,
                                  User.is_active == True).first()
    if user:
        user.is_active = False
        rec.account_disabled = True
        rec.account_disabled_at = datetime.utcnow()
        rec.account_disabled_by = current_user.id
        _log(db, current_user, "disable_account_on_resignation",
             f"离职停用账号: {user.username}",
             target_type="user", target_id=user.id,
             old={"is_active": True}, new={"is_active": False})
        db.commit()
        return {"message": f"账号 {user.username} 已停用"}
    return {"message": "未找到关联账号"}


# ======================================================================
# 工作交接
# ======================================================================

@router.get("/resignations/{rid}/handover-items", summary="离职申请的交接项目")
def get_handover_items(rid: int,
                       current_user: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    items = db.query(HandoverItem).filter(HandoverItem.resignation_id == rid) \
        .order_by(HandoverItem.id).all()
    return {"items": [{
        **{c.name: getattr(it, c.name) for c in it.__table__.columns},
    } for it in items]}


@router.post("/resignations/{rid}/handover-items", summary="添加交接项")
def add_handover_item(rid: int, data: dict = Body(...),
                      current_user: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    if not data.get("item_category") or not data.get("item_name"):
        raise HTTPException(400, "缺少类别或名称")
    item = HandoverItem(resignation_id=rid)
    for k, v in data.items():
        if hasattr(item, k) and k not in ("id", "created_at"):
            setattr(item, k, v)
    db.add(item)
    db.commit()
    return {"id": item.id, "message": "已添加"}


@router.post("/handover-items/{hid}/confirm-handover", summary="交接人确认")
def confirm_handover(hid: int,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    it = db.query(HandoverItem).get(hid)
    if not it:
        raise HTTPException(404, "不存在")
    it.handover_user_id = current_user.id
    it.handover_confirmed_at = datetime.utcnow()
    _check_all_confirmed(db, it)
    db.commit()
    return {"message": "交接人已确认"}


@router.post("/handover-items/{hid}/confirm-receiver", summary="接收人确认")
def confirm_receiver(hid: int,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    it = db.query(HandoverItem).get(hid)
    if not it:
        raise HTTPException(404, "不存在")
    it.receiver_user_id = current_user.id
    it.receiver_confirmed_at = datetime.utcnow()
    _check_all_confirmed(db, it)
    db.commit()
    return {"message": "接收人已确认"}


@router.post("/handover-items/{hid}/confirm-supervisor", summary="监交人确认")
def confirm_supervisor(hid: int,
                       current_user: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    it = db.query(HandoverItem).get(hid)
    if not it:
        raise HTTPException(404, "不存在")
    it.supervisor_user_id = current_user.id
    it.supervisor_confirmed_at = datetime.utcnow()
    _check_all_confirmed(db, it)
    db.commit()
    return {"message": "监交人已确认"}


def _check_all_confirmed(db, it: HandoverItem):
    if (it.handover_confirmed_at and it.receiver_confirmed_at
            and it.supervisor_confirmed_at and not it.all_confirmed):
        it.all_confirmed = True
        # 若该离职申请所有交接项都已确认，标记交接完成
        remaining = db.query(HandoverItem).filter(
            HandoverItem.resignation_id == it.resignation_id,
            HandoverItem.all_confirmed == False,
        ).count()
        if remaining == 0:
            ra = db.query(ResignationApplication).get(it.resignation_id)
            if ra and not ra.handover_completed:
                ra.handover_completed = True
                ra.handover_completed_at = datetime.utcnow()


# ======================================================================
# 关键数据变更双人复核
# ======================================================================

PERSON_FIELD_LABELS = {
    "name": "姓名", "id_card": "身份证号", "gender": "性别",
    "department": "部门", "position": "职务", "rank": "职级",
    "unit_id": "单位", "political_status": "政治面貌",
    "education_level": "最高学历", "degree": "学位",
    "join_unit_date": "入职本单位时间", "birth_date": "出生日期",
    "phone": "手机号",
}


@router.get("/change-reviews", summary="待复核的数据变更列表")
def list_change_reviews(
    status: str = Query("pending"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    q = db.query(DataChangeReview).filter(DataChangeReview.status == status)
    total = q.count()
    items = q.order_by(DataChangeReview.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": [{
        **{c.name: getattr(r, c.name) for c in r.__table__.columns},
        "proposed_at": r.proposed_at.strftime("%Y-%m-%d %H:%M:%S") if r.proposed_at else None,
        "reviewed_at": r.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if r.reviewed_at else None,
    } for r in items]}


@router.post("/change-reviews/propose",
             summary="提交人员关键字段修改申请（需要复核）")
def propose_change(
    payload: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    payload 结构:
      person_id: int
      changes: [{field, new_value, label}]
      reason: str
    """
    pid = payload.get("person_id")
    changes = payload.get("changes") or []
    if not pid or not changes:
        raise HTTPException(400, "缺少必要参数")

    # 过滤只允许 KEY_CHANGE_FIELDS
    valid_changes = [c for c in changes if c.get("field") in KEY_CHANGE_FIELDS]
    if not valid_changes:
        raise HTTPException(400, "无可修改字段")

    p = db.query(Person).get(pid)
    if not p:
        raise HTTPException(404, "人员不存在")

    # 读取旧值
    for c in valid_changes:
        f = c["field"]
        old = getattr(p, f, None)
        if hasattr(old, "isoformat"):
            old = old.isoformat()
        c["old"] = old
        c["label"] = PERSON_FIELD_LABELS.get(f, f)

    # 自动跳过未变更项
    valid_changes = [c for c in valid_changes if str(c["old"] or "") != str(c["new_value"] or "")]
    if not valid_changes:
        return {"message": "没有检测到值变化", "skipped": True}

    review = DataChangeReview(
        target_type="person",
        target_id=pid,
        target_display=p.name,
        field_changes=valid_changes,
        proposer_id=current_user.id,
        proposer_name=current_user.username,
        proposer_reason=payload.get("reason") or "",
        status="pending",
    )
    db.add(review)
    _log(db, current_user, "propose_data_change",
         f"提交人员{p.name}关键字段修改申请，{len(valid_changes)}个字段，等待复核",
         target_type="person", target_id=pid, new_value=valid_changes)
    db.commit()
    return {"id": review.id, "message": "已提交，等待超管复核"}


@router.post("/change-reviews/{rid}/approve",
             summary="复核通过并写入实际数据")
def approve_change(
    rid: int,
    payload: dict = Body(...),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    rev = db.query(DataChangeReview).get(rid)
    if not rev or rev.status != "pending":
        raise HTTPException(400, "状态异常")

    p = db.query(Person).filter(Person.id == rev.target_id).first()
    if not p:
        raise HTTPException(404, "目标人员已不存在")

    old_vals, new_vals = {}, {}
    for ch in rev.field_changes:
        f = ch["field"]
        old_vals[f] = ch["old"]
        nv = ch["new_value"]
        # 日期字段
        if f in ("birth_date", "join_unit_date") and isinstance(nv, str) and nv:
            nv = _date.fromisoformat(nv[:10])
        if f == "unit_id" and nv is not None:
            nv = int(nv)
        setattr(p, f, nv)
        new_vals[f] = nv.isoformat() if hasattr(nv, "isoformat") else nv

    rev.status = "approved"
    rev.reviewer_id = current_user.id
    rev.reviewer_name = current_user.username
    rev.reviewer_opinion = payload.get("opinion", "")
    rev.reviewed_at = datetime.utcnow()
    rev.applied_at = datetime.utcnow()

    _log(db, current_user, "approve_data_change",
         f"复核通过人员{p.name}的字段修改，已写入档案",
         target_type="person", target_id=p.id, old_value=old_vals, new_value=new_vals)
    db.commit()
    return {"message": "复核通过，档案已更新"}


@router.post("/change-reviews/{rid}/reject", summary="驳回修改申请")
def reject_change(rid: int, payload: dict = Body(...),
                  current_user: User = Depends(require_super_admin),
                  db: Session = Depends(get_db)):
    rev = db.query(DataChangeReview).get(rid)
    if not rev or rev.status != "pending":
        raise HTTPException(400, "状态异常")
    rev.status = "rejected"
    rev.reviewer_id = current_user.id
    rev.reviewer_name = current_user.username
    rev.reviewer_opinion = payload.get("opinion", "")
    rev.reviewed_at = datetime.utcnow()
    _log(db, current_user, "reject_data_change",
         f"驳回人员{rev.target_display}的字段修改申请，原因: {payload.get('opinion', '')}",
         target_type=rev.target_type, target_id=rev.target_id)
    db.commit()
    return {"message": "已驳回"}
