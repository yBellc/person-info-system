"""在职管理路由：考勤、绩效、奖惩、调岗、合同、培训（P0-1）
所有接口均需管理员或超管权限，严格审计
"""
from datetime import date as _date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import get_current_user, require_admin, require_super_admin
from app.models.user import User, Unit
from app.models.person import Person, RewardPunishment
from app.models.hr_management import (
    AttendanceRecord, PerformanceRecord, TransferRecord,
    ContractRecord, TrainingRecord,
)
from app.models.user import OperationLog

router = APIRouter(prefix="/hr", tags=["在职人事管理"])


def _log(db: Session, user: User, action: str, detail: str, target_type=None, target_id=None,
        old_value=None, new_value=None):
    log = OperationLog(
        operator_id=user.id, operator_name=user.username,
        action=action, target_type=target_type, target_id=target_id,
        detail=detail, old_value=old_value, new_value=new_value,
    )
    db.add(log)


# ======================================================================
# 考勤记录
# ======================================================================

@router.get("/attendance", summary="考勤记录列表（支持按人/年月筛选）")
def list_attendance(
    person_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AttendanceRecord)
    if person_id:
        q = q.filter(AttendanceRecord.person_id == person_id)
    if year:
        q = q.filter(AttendanceRecord.year == year)
    if month:
        q = q.filter(AttendanceRecord.month == month)
    total = q.count()
    items = q.order_by(AttendanceRecord.year.desc(), AttendanceRecord.month.desc()) \
        .offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
        })
    return {"total": total, "items": data}


@router.post("/attendance", summary="新增/录入考勤记录")
def create_attendance(
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    pid = data.get("person_id")
    y = data.get("year")
    m = data.get("month")
    if not (pid and y and m):
        raise HTTPException(400, "缺少人员/年月")
    # 去重校验
    exist = db.query(AttendanceRecord).filter(
        AttendanceRecord.person_id == pid,
        AttendanceRecord.year == y,
        AttendanceRecord.month == m,
    ).first()
    if exist:
        raise HTTPException(400, "该人员当月考勤已存在，请用更新接口修改")

    rec = AttendanceRecord(created_by=current_user.id)
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "updated_at", "created_by"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(pid)
    _log(db, current_user, "create_attendance",
         f"录入考勤: {p.name if p else pid} {y}年{m}月",
         target_type="attendance", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已录入"}


@router.put("/attendance/{rid}", summary="更新考勤记录")
def update_attendance(
    rid: int,
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(AttendanceRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    old_val = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "updated_at", "created_by"):
            setattr(rec, k, v)
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "update_attendance",
         f"更新考勤: {p.name if p else rec.person_id} {rec.year}年{rec.month}月",
         target_type="attendance", target_id=rid, old_value=old_val, new_value=data)
    db.commit()
    return {"message": "已更新"}


# ======================================================================
# 绩效考核
# ======================================================================

@router.get("/performance", summary="绩效考核列表")
def list_performance(
    person_id: Optional[int] = Query(None),
    period_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(PerformanceRecord)
    if person_id:
        q = q.filter(PerformanceRecord.person_id == person_id)
    if period_type:
        q = q.filter(PerformanceRecord.period_type == period_type)
    if year:
        q = q.filter(PerformanceRecord.year == year)
    total = q.count()
    items = q.order_by(PerformanceRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "evaluate_date": r.evaluate_date.isoformat() if r.evaluate_date else None,
        })
    return {"total": total, "items": data}


@router.post("/performance", summary="新增绩效考核")
def create_performance(
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not data.get("person_id") or not data.get("period_name"):
        raise HTTPException(400, "缺少人员/考核周期")
    rec = PerformanceRecord(created_by=current_user.id)
    if data.get("evaluate_date"):
        data["evaluate_date"] = _date.fromisoformat(data["evaluate_date"][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(data["person_id"])
    _log(db, current_user, "create_performance",
         f"新增考核: {p.name if p else data['person_id']} {data.get('period_name')}",
         target_type="performance", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已新增"}


@router.put("/performance/{rid}", summary="更新考核记录")
def update_performance(
    rid: int, data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rec = db.query(PerformanceRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    if data.get("evaluate_date") and isinstance(data["evaluate_date"], str):
        data["evaluate_date"] = _date.fromisoformat(data["evaluate_date"][:10])
    old_val = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at"):
            setattr(rec, k, v)
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "update_performance",
         f"更新考核: {p.name if p else rec.person_id} {rec.period_name}",
         target_type="performance", target_id=rid, old_value=old_val, new_value=data)
    db.commit()
    return {"message": "已更新"}


@router.delete("/performance/{rid}", summary="删除考核记录")
def delete_performance(rid: int, current_user: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    rec = db.query(PerformanceRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "delete_performance",
         f"删除考核: {p.name if p else rec.person_id} {rec.period_name}",
         target_type="performance", target_id=rid,
         old_value={c.name: getattr(rec, c.name) for c in rec.__table__.columns})
    db.delete(rec)
    db.commit()
    return {"message": "已删除"}


# ======================================================================
# 奖惩记录（沿用 RewardPunishment 模型，补充增删改查）
# ======================================================================

@router.get("/rewards", summary="奖惩记录列表")
def list_rewards(
    person_id: Optional[int] = Query(None),
    rtype: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(RewardPunishment)
    if person_id:
        q = q.filter(RewardPunishment.person_id == person_id)
    if rtype:
        q = q.filter(RewardPunishment.type == rtype)
    total = q.count()
    items = q.order_by(RewardPunishment.date.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "date": r.date.isoformat() if r.date else None,
        })
    return {"total": total, "items": data}


@router.post("/rewards", summary="新增奖惩记录")
def create_reward(data: dict = Body(...),
                  current_user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    if not data.get("person_id"):
        raise HTTPException(400, "缺少人员")
    rec = RewardPunishment()
    if data.get("date"):
        data["date"] = _date.fromisoformat(data["date"][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k != "id":
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(data["person_id"])
    _log(db, current_user, "create_reward",
         f"新增奖惩: {p.name if p else data['person_id']} {data.get('type')} {data.get('name')}",
         target_type="reward_punishment", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已新增"}


@router.put("/rewards/{rid}", summary="更新奖惩记录")
def update_reward(rid: int, data: dict = Body(...),
                  current_user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    rec = db.query(RewardPunishment).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    if data.get("date") and isinstance(data["date"], str):
        data["date"] = _date.fromisoformat(data["date"][:10])
    old = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for k, v in data.items():
        if hasattr(rec, k) and k != "id":
            setattr(rec, k, v)
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "update_reward",
         f"更新奖惩: {p.name if p else rec.person_id}",
         target_type="reward_punishment", target_id=rid, old_value=old, new_value=data)
    db.commit()
    return {"message": "已更新"}


@router.delete("/rewards/{rid}", summary="删除奖惩记录")
def delete_reward(rid: int, current_user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    rec = db.query(RewardPunishment).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "delete_reward",
         f"删除奖惩: {p.name if p else rec.person_id} {rec.type} {rec.name}",
         target_type="reward_punishment", target_id=rid,
         old_value={c.name: getattr(rec, c.name) for c in rec.__table__.columns})
    db.delete(rec)
    db.commit()
    return {"message": "已删除"}


# ======================================================================
# 调岗/调动记录
# ======================================================================

@router.get("/transfers", summary="调动记录列表")
def list_transfers(
    person_id: Optional[int] = Query(None),
    transfer_type: Optional[str] = Query(None),
    is_approved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(TransferRecord)
    if person_id:
        q = q.filter(TransferRecord.person_id == person_id)
    if transfer_type:
        q = q.filter(TransferRecord.transfer_type == transfer_type)
    if is_approved is not None:
        q = q.filter(TransferRecord.is_approved == is_approved)
    total = q.count()
    items = q.order_by(TransferRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "approved_at": r.approved_at.strftime("%Y-%m-%d %H:%M:%S") if r.approved_at else None,
        })
    return {"total": total, "items": data}


@router.post("/transfers", summary="新增调动（需双人复核才生效）")
def create_transfer(
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not data.get("person_id") or not data.get("transfer_type"):
        raise HTTPException(400, "缺少人员或类型")
    rec = TransferRecord(created_by=current_user.id, is_approved=False)
    if data.get("effective_date"):
        data["effective_date"] = _date.fromisoformat(data["effective_date"][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "created_by", "is_approved",
                                          "approved_by", "approved_at"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(data["person_id"])
    _log(db, current_user, "create_transfer",
         f"新增调动申请{data['transfer_type']}: {p.name if p else data['person_id']}，等待复核",
         target_type="transfer", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已提交，等待复核生效"}


@router.post("/transfers/{rid}/approve", summary="复核通过调动并写入人员档案")
def approve_transfer(
    rid: int,
    payload: dict = Body(...),
    current_user: User = Depends(require_super_admin),  # 必须比录入者权限更高
    db: Session = Depends(get_db),
):
    rec = db.query(TransferRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    if rec.is_approved:
        raise HTTPException(400, "已复核过")

    # 写入 Person 档案
    p = db.query(Person).get(rec.person_id)
    if not p:
        raise HTTPException(404, "人员不存在")

    old_person = {k: getattr(p, k) for k in ("department", "position", "rank", "unit_id")}

    if rec.to_department:
        p.department = rec.to_department
    if rec.to_position:
        p.position = rec.to_position
    if rec.to_rank:
        p.rank = rec.to_rank
    if rec.to_unit_id is not None:
        p.unit_id = rec.to_unit_id
    # 薪资属于敏感信息，建议通过自定义字段扩展，这里仅记录在 transfer record

    rec.is_approved = True
    rec.approved_by = current_user.id
    rec.approved_at = __import__("datetime").datetime.utcnow()

    _log(db, current_user, "approve_transfer",
         f"复核通过调动，已写入人员档案: {p.name} {rec.transfer_type}",
         target_type="person", target_id=p.id,
         old_value=old_person,
         new_value={k: getattr(p, k) for k in ("department", "position", "rank", "unit_id")})
    db.commit()
    return {"message": "复核通过，档案已更新"}


# ======================================================================
# 合同记录
# ======================================================================

@router.get("/contracts", summary="合同列表")
def list_contracts(
    person_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    expired_in_days: Optional[int] = Query(None, description="即将到期，多少天内"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(ContractRecord)
    if person_id:
        q = q.filter(ContractRecord.person_id == person_id)
    if status:
        q = q.filter(ContractRecord.status == status)
    if expired_in_days is not None:
        from datetime import timedelta
        cutoff = _date.today() + timedelta(days=expired_in_days)
        q = q.filter(
            ContractRecord.end_date.isnot(None),
            ContractRecord.end_date <= cutoff,
            ContractRecord.status == "active",
        )
    total = q.count()
    items = q.order_by(ContractRecord.end_date.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "sign_date": r.sign_date.isoformat() if r.sign_date else None,
        })
    return {"total": total, "items": data}


@router.post("/contracts", summary="新增合同记录")
def create_contract(data: dict = Body(...),
                    current_user: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    if not data.get("person_id"):
        raise HTTPException(400, "缺少人员")
    rec = ContractRecord(created_by=current_user.id)
    for fld in ("start_date", "end_date", "sign_date"):
        if data.get(fld) and isinstance(data[fld], str):
            data[fld] = _date.fromisoformat(data[fld][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "created_by"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(data["person_id"])
    _log(db, current_user, "create_contract",
         f"新增合同: {p.name if p else data['person_id']} {data.get('contract_type')} {data.get('contract_no')}",
         target_type="contract", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已新增"}


@router.put("/contracts/{rid}", summary="更新合同")
def update_contract(rid: int, data: dict = Body(...),
                    current_user: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    rec = db.query(ContractRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    old = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for fld in ("start_date", "end_date", "sign_date"):
        if data.get(fld) and isinstance(data[fld], str):
            data[fld] = _date.fromisoformat(data[fld][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "created_by"):
            setattr(rec, k, v)
    p = db.query(Person).get(rec.person_id)
    _log(db, current_user, "update_contract",
         f"更新合同: {p.name if p else rec.person_id}",
         target_type="contract", target_id=rid, old_value=old, new_value=data)
    db.commit()
    return {"message": "已更新"}


# ======================================================================
# 培训记录
# ======================================================================

@router.get("/trainings", summary="培训记录列表")
def list_trainings(
    person_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(TrainingRecord)
    if person_id:
        q = q.filter(TrainingRecord.person_id == person_id)
    total = q.count()
    items = q.order_by(TrainingRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in items:
        p = db.query(Person).get(r.person_id)
        data.append({
            **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            "person_name": p.name if p else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
        })
    return {"total": total, "items": data}


@router.post("/trainings", summary="新增培训记录")
def create_training(data: dict = Body(...),
                    current_user: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    if not data.get("person_id") or not data.get("training_name"):
        raise HTTPException(400, "缺少必要字段")
    rec = TrainingRecord(created_by=current_user.id)
    for fld in ("start_date", "end_date"):
        if data.get(fld) and isinstance(data[fld], str):
            data[fld] = _date.fromisoformat(data[fld][:10])
    for k, v in data.items():
        if hasattr(rec, k) and k not in ("id", "created_at", "created_by"):
            setattr(rec, k, v)
    db.add(rec)
    db.flush()
    p = db.query(Person).get(data["person_id"])
    _log(db, current_user, "create_training",
         f"新增培训: {p.name if p else data['person_id']} {data['training_name']}",
         target_type="training", target_id=rec.id, new_value=data)
    db.commit()
    return {"id": rec.id, "message": "已新增"}


@router.delete("/trainings/{rid}", summary="删除培训记录")
def delete_training(rid: int, current_user: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    rec = db.query(TrainingRecord).get(rid)
    if not rec:
        raise HTTPException(404, "记录不存在")
    db.delete(rec)
    _log(db, current_user, "delete_training", f"删除培训 id={rid}",
         target_type="training", target_id=rid)
    db.commit()
    return {"message": "已删除"}
