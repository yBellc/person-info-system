"""单位与名单管理路由（模块 1）"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import get_current_user, require_super_admin, require_admin
from app.core.idcard import validate_id_card, mask_id_card
from app.core.permissions import can_access_unit
from app.models import User, Unit, UnitRoster, Person, OperationLog
from app.schemas.unit import (
    UnitCreate, UnitUpdate, UnitOut, RosterBatchCreate, RosterOut,
)

router = APIRouter(prefix="/units", tags=["单位管理"])


def log_op(db, user, action, detail=None, target_type=None, target_id=None):
    db.add(OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
    ))


# ===== 单位 CRUD（仅超管）=====
@router.get("", response_model=list[UnitOut], summary="单位列表")
def list_units(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    units = db.query(Unit).order_by(Unit.id).all()
    result = []
    for u in units:
        parent_name = db.query(Unit.name).filter(Unit.id == u.parent_id).scalar() if u.parent_id else None
        result.append(UnitOut(
            id=u.id, name=u.name, code=u.code, parent_id=u.parent_id,
            is_active=u.is_active, created_at=u.created_at, parent_name=parent_name,
        ))
    return result


@router.post("", response_model=UnitOut, summary="创建单位（超管）")
def create_unit(
    req: UnitCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    unit = Unit(name=req.name, code=req.code, parent_id=req.parent_id, is_active=req.is_active)
    db.add(unit)
    db.flush()
    log_op(db, current_user, "create_unit", f"创建单位 {unit.name}", target_type="unit", target_id=unit.id)
    db.commit()
    db.refresh(unit)
    return UnitOut(**{c.name: getattr(unit, c.name) for c in unit.__table__.columns}, parent_name=None)


@router.put("/{unit_id}", response_model=UnitOut, summary="修改单位（超管）")
def update_unit(
    unit_id: int,
    req: UnitUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    unit = db.query(Unit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(unit, k, v)
    log_op(db, current_user, "update_unit", f"修改单位 {unit.name}", target_type="unit", target_id=unit.id)
    db.commit()
    db.refresh(unit)
    parent_name = db.query(Unit.name).filter(Unit.id == unit.parent_id).scalar() if unit.parent_id else None
    return UnitOut(
        id=unit.id, name=unit.name, code=unit.code, parent_id=unit.parent_id,
        is_active=unit.is_active, created_at=unit.created_at, parent_name=parent_name,
    )


@router.delete("/{unit_id}", summary="删除单位（超管）")
def delete_unit(
    unit_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    unit = db.query(Unit).get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")
    # 检查是否有子单位
    child_count = db.query(Unit).filter(Unit.parent_id == unit_id).count()
    if child_count > 0:
        raise HTTPException(status_code=400, detail=f"该单位下有 {child_count} 个子单位，请先删除或迁移子单位")
    # 检查是否有关联人员
    person_count = db.query(Person).filter(Person.unit_id == unit_id).count()
    if person_count > 0:
        raise HTTPException(status_code=400, detail=f"该单位下有 {person_count} 名人员，无法删除")
    log_op(db, current_user, "delete_unit", f"删除单位 {unit.name}", target_type="unit", target_id=unit.id)
    db.delete(unit)
    db.commit()
    return {"msg": "已删除"}


# ===== 单位名单（单位管理员）=====
@router.get("/{unit_id}/roster", response_model=list[RosterOut], summary="单位名单")
def get_roster(
    unit_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 数据隔离：非超管只能看本单位及下属单位
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权访问该单位名单")
    items = db.query(UnitRoster).filter(UnitRoster.unit_id == unit_id).all()
    return [
        RosterOut(
            id=i.id, name=i.name, id_card_masked=mask_id_card(i.id_card),
            is_registered=i.is_registered, unit_id=i.unit_id,
        )
        for i in items
    ]


@router.post("/{unit_id}/roster", summary="批量导入名单（单位管理员）")
def import_roster(
    unit_id: int,
    req: RosterBatchCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not can_access_unit(current_user, unit_id, db):
        raise HTTPException(status_code=403, detail="无权操作该单位")

    added, skipped, invalid = 0, 0, 0
    for item in req.items:
        # 校验身份证
        if not validate_id_card(item.id_card):
            invalid += 1
            continue
        # 查重（同单位+同身份证）
        exists = db.query(UnitRoster).filter(
            UnitRoster.unit_id == unit_id,
            UnitRoster.id_card == item.id_card,
        ).first()
        if exists:
            skipped += 1
            continue
        db.add(UnitRoster(unit_id=unit_id, name=item.name, id_card=item.id_card))
        added += 1

    log_op(db, current_user, "import_roster",
           f"单位{unit_id}导入名单: 新增{added} 跳过{skipped} 无效{invalid}",
           target_type="unit", target_id=unit_id)
    db.commit()
    return {"added": added, "skipped": skipped, "invalid": invalid}


@router.delete("/roster/{roster_id}", summary="删除名单条目")
def delete_roster(
    roster_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(UnitRoster).get(roster_id)
    if not item:
        raise HTTPException(status_code=404, detail="名单条目不存在")
    if item.is_registered:
        raise HTTPException(status_code=400, detail="该人员已注册，无法删除名单")
    if not can_access_unit(current_user, item.unit_id, db):
        raise HTTPException(status_code=403, detail="无权操作")
    db.delete(item)
    db.commit()
    return {"msg": "已删除"}
