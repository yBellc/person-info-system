"""统计聚合接口（模块 3 - 聚合统计表）

内置常用维度：年龄结构、性别比、学历结构、各单位人数、职级分布
"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import get_current_user, require_admin
from app.core.idcard import calc_age
from app.models import User, Person, Unit

router = APIRouter(prefix="/statistics", tags=["统计报表"])


def base_query(current_user: User, db: Session, unit_id: int = None):
    """按权限过滤后的基础查询（支持层级）"""
    from app.core.permissions import get_accessible_unit_ids, can_access_unit
    q = db.query(Person)
    if current_user.role != "super_admin":
        accessible_ids = get_accessible_unit_ids(current_user, db)
        if not accessible_ids:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="未绑定单位")
        q = q.filter(Person.unit_id.in_(accessible_ids))
        # 如果指定了单位，进一步过滤（需校验权限）
        if unit_id:
            if not can_access_unit(current_user, unit_id, db):
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="无权访问该单位")
            q = q.filter(Person.unit_id == unit_id)
    elif unit_id:
        q = q.filter(Person.unit_id == unit_id)
    return q


@router.get("/overview", summary="总览数据")
def overview(
    unit_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = base_query(current_user, db, unit_id)
    persons = q.all()
    total = len(persons)
    male = sum(1 for p in persons if p.gender == "男")
    female = sum(1 for p in persons if p.gender == "女")
    ages = [calc_age(p.birth_date) for p in persons if p.birth_date]
    avg_age = round(sum(ages) / len(ages), 1) if ages else 0
    return {
        "total": total, "male": male, "female": female,
        "avg_age": avg_age,
    }


@router.get("/by-gender", summary="性别分布")
def by_gender(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), unit_id: int = None):
    persons = base_query(current_user, db, unit_id).all()
    c = Counter(p.gender or "未填" for p in persons)
    return [{"label": k, "count": v} for k, v in c.items()]


@router.get("/by-age", summary="年龄段分布")
def by_age(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), unit_id: int = None):
    persons = base_query(current_user, db, unit_id).all()
    buckets = {"30岁以下": 0, "30-40岁": 0, "40-50岁": 0, "50岁以上": 0}
    for p in persons:
        age = calc_age(p.birth_date)
        if age is None:
            continue
        if age < 30: buckets["30岁以下"] += 1
        elif age < 40: buckets["30-40岁"] += 1
        elif age < 50: buckets["40-50岁"] += 1
        else: buckets["50岁以上"] += 1
    return [{"label": k, "count": v} for k, v in buckets.items()]


@router.get("/by-education", summary="学历结构")
def by_education(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), unit_id: int = None):
    persons = base_query(current_user, db, unit_id).all()
    c = Counter(p.education_level or "未填" for p in persons)
    return [{"label": k, "count": v} for k, v in c.items()]


@router.get("/by-unit", summary="各单位人数")
def by_unit(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    from app.core.permissions import get_accessible_unit_ids
    accessible_ids = get_accessible_unit_ids(current_user, db)
    if not accessible_ids:
        return []
    units = db.query(Unit).filter(Unit.id.in_(accessible_ids)).all()
    result = []
    for u in units:
        count = db.query(Person).filter(Person.unit_id == u.id).count()
        result.append({"unit_id": u.id, "unit_name": u.name, "count": count})
    return result


@router.get("/by-rank", summary="职级分布")
def by_rank(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), unit_id: int = None):
    persons = base_query(current_user, db, unit_id).all()
    c = Counter(p.rank or "未填" for p in persons)
    return [{"label": k, "count": v} for k, v in c.items()]


@router.get("/by-political-status", summary="政治面貌分布")
def by_political(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), unit_id: int = None):
    persons = base_query(current_user, db, unit_id).all()
    c = Counter(p.political_status or "未填" for p in persons)
    return [{"label": k, "count": v} for k, v in c.items()]
