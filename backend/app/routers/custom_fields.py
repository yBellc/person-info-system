"""自定义字段管理路由（模块 2 字段动态扩展）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import require_admin
from app.models import User, CustomFieldDefinition
from app.schemas.person import CustomFieldCreate, CustomFieldUpdate, CustomFieldOut

router = APIRouter(prefix="/custom-fields", tags=["自定义字段"])


@router.get("", response_model=list[CustomFieldOut], summary="字段定义列表")
def list_fields(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(CustomFieldDefinition).order_by(
        CustomFieldDefinition.group_name, CustomFieldDefinition.sort
    ).all()


@router.post("", response_model=CustomFieldOut, summary="新增字段定义")
def create_field(
    req: CustomFieldCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # field_key 查重
    if db.query(CustomFieldDefinition).filter(CustomFieldDefinition.field_key == req.field_key).first():
        raise HTTPException(status_code=400, detail="字段key已存在")
    field = CustomFieldDefinition(**req.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.put("/{field_id}", response_model=CustomFieldOut, summary="修改字段定义")
def update_field(
    field_id: int,
    req: CustomFieldUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    field = db.query(CustomFieldDefinition).get(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(field, k, v)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", summary="删除字段定义")
def delete_field(
    field_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    field = db.query(CustomFieldDefinition).get(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="字段不存在")
    db.delete(field)  # 级联删除值
    db.commit()
    return {"msg": "已删除"}
