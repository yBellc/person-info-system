"""组织架构路由 - 部门、岗位、职级、人员岗位"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Department, Position, Rank, PersonPosition
from app.models.person import Person
from app.models.user import User
from app.schemas.organization import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTreeResponse,
    RankCreate, RankUpdate, RankResponse,
    PositionCreate, PositionUpdate, PositionResponse,
    PersonPositionCreate, PersonPositionUpdate, PersonPositionResponse,
)
from app.core.permissions import require_role

router = APIRouter(prefix="/departments", tags=["组织架构-部门"])


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(
    unit_id: Optional[int] = Query(None, description="单位ID"),
    is_active: Optional[bool] = Query(True, description="是否启用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取部门列表"""
    query = db.query(Department)
    if unit_id:
        query = query.filter(Department.unit_id == unit_id)
    if is_active is not None:
        query = query.filter(Department.is_active == is_active)
    departments = query.order_by(Department.level, Department.sort).all()
    return departments


@router.get("/tree", response_model=List[DepartmentTreeResponse])
def get_department_tree(
    unit_id: Optional[int] = Query(None, description="单位ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取部门树结构"""
    query = db.query(Department).filter(Department.is_active == True)
    if unit_id:
        query = query.filter(Department.unit_id == unit_id)
    departments = query.order_by(Department.level, Department.sort).all()

    # 构建树结构
    dept_map = {}
    roots = []
    for dept in departments:
        dept_dict = {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "level": dept.level,
            "sort": dept.sort,
            "is_active": dept.is_active,
            "children": [],
            "manager_id": dept.manager_id,
            "manager_name": None,
            "person_count": db.query(PersonPosition).filter(
                PersonPosition.department_id == dept.id,
                PersonPosition.is_current == True
            ).count(),
        }
        if dept.manager_id:
            manager = db.query(Person).filter(Person.id == dept.manager_id).first()
            if manager:
                dept_dict["manager_name"] = manager.name
        dept_map[dept.id] = dept_dict

    for dept_id, dept_data in dept_map.items():
        parent_id = next((d.parent_id for d in departments if d.id == dept_id), None)
        if parent_id and parent_id in dept_map:
            dept_map[parent_id]["children"].append(dept_data)
        else:
            roots.append(dept_data)

    return roots


@router.post("/", response_model=DepartmentResponse)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """创建部门"""
    # 检查同级下是否重名
    existing = db.query(Department).filter(
        Department.name == data.name,
        Department.parent_id == data.parent_id,
        Department.unit_id == data.unit_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="同级下已存在同名部门")

    # 计算层级
    level = data.level
    if data.parent_id:
        parent = db.query(Department).filter(Department.id == data.parent_id).first()
        if parent:
            level = parent.level + 1

    dept = Department(
        **data.model_dump(exclude={"level"}),
        level=level,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取部门详情"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    return dept


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """更新部门"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除部门（软删除）"""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")

    # 检查是否有子部门
    children = db.query(Department).filter(Department.parent_id == dept_id, Department.is_active == True).count()
    if children > 0:
        raise HTTPException(status_code=400, detail="存在子部门，无法删除")

    # 检查是否有人员关联
    person_count = db.query(PersonPosition).filter(PersonPosition.department_id == dept_id, PersonPosition.is_current == True).count()
    if person_count > 0:
        raise HTTPException(status_code=400, detail="存在关联人员，无法删除")

    dept.is_active = False
    db.commit()
    return {"message": "部门已删除"}


# ============ 职级路由 ============

rank_router = APIRouter(prefix="/ranks", tags=["组织架构-职级"])


@rank_router.get("/", response_model=List[RankResponse])
def list_ranks(
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取职级列表"""
    query = db.query(Rank)
    if is_active is not None:
        query = query.filter(Rank.is_active == is_active)
    return query.order_by(Rank.level).all()


@rank_router.post("/", response_model=RankResponse)
def create_rank(
    data: RankCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """创建职级"""
    existing = db.query(Rank).filter(Rank.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="职级编码已存在")
    rank = Rank(**data.model_dump())
    db.add(rank)
    db.commit()
    db.refresh(rank)
    return rank


@rank_router.put("/{rank_id}", response_model=RankResponse)
def update_rank(
    rank_id: int,
    data: RankUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """更新职级"""
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(status_code=404, detail="职级不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rank, key, value)

    db.commit()
    db.refresh(rank)
    return rank


@rank_router.delete("/{rank_id}")
def delete_rank(
    rank_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除职级"""
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(status_code=404, detail="职级不存在")
    rank.is_active = False
    db.commit()
    return {"message": "职级已删除"}


# ============ 岗位路由 ============

position_router = APIRouter(prefix="/positions", tags=["组织架构-岗位"])


@position_router.get("/", response_model=List[PositionResponse])
def list_positions(
    is_active: Optional[bool] = Query(True),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取岗位列表"""
    query = db.query(Position)
    if is_active is not None:
        query = query.filter(Position.is_active == is_active)
    if category:
        query = query.filter(Position.category == category)
    return query.order_by(Position.name).all()


@position_router.post("/", response_model=PositionResponse)
def create_position(
    data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """创建岗位"""
    existing = db.query(Position).filter(Position.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="岗位编码已存在")
    position = Position(**data.model_dump())
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@position_router.put("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: int,
    data: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """更新岗位"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="岗位不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(position, key, value)

    db.commit()
    db.refresh(position)
    return position


@position_router.delete("/{position_id}")
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除岗位"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="岗位不存在")
    position.is_active = False
    db.commit()
    return {"message": "岗位已删除"}


# ============ 人员岗位路由 ============

person_position_router = APIRouter(prefix="/person-positions", tags=["组织架构-人员岗位"])


@person_position_router.get("/", response_model=List[PersonPositionResponse])
def list_person_positions(
    person_id: Optional[int] = Query(None, description="人员ID"),
    department_id: Optional[int] = Query(None, description="部门ID"),
    is_current: Optional[bool] = Query(None, description="是否当前任职"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取人员岗位列表"""
    query = db.query(PersonPosition)
    if person_id:
        query = query.filter(PersonPosition.person_id == person_id)
    if department_id:
        query = query.filter(PersonPosition.department_id == department_id)
    if is_current is not None:
        query = query.filter(PersonPosition.is_current == is_current)

    results = query.order_by(PersonPosition.person_id, PersonPosition.start_date.desc()).all()

    # 获取关联名称
    response_list = []
    for pp in results:
        pp_dict = {
            "id": pp.id,
            "person_id": pp.person_id,
            "department_id": pp.department_id,
            "position_id": pp.position_id,
            "rank_id": pp.rank_id,
            "is_primary": pp.is_primary,
            "start_date": pp.start_date,
            "end_date": pp.end_date,
            "is_current": pp.is_current,
            "appointment_no": pp.appointment_no,
            "remark": pp.remark,
            "created_at": pp.created_at,
            "department_name": None,
            "position_name": None,
            "rank_name": None,
        }
        if pp.department_id:
            dept = db.query(Department).filter(Department.id == pp.department_id).first()
            if dept:
                pp_dict["department_name"] = dept.name
        if pp.position_id:
            pos = db.query(Position).filter(Position.id == pp.position_id).first()
            if pos:
                pp_dict["position_name"] = pos.name
        if pp.rank_id:
            rank = db.query(Rank).filter(Rank.id == pp.rank_id).first()
            if rank:
                pp_dict["rank_name"] = rank.name
        response_list.append(pp_dict)

    return response_list


@person_position_router.post("/", response_model=PersonPositionResponse)
def create_person_position(
    data: PersonPositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """创建人员岗位"""
    # 检查人员是否存在
    person = db.query(Person).filter(Person.id == data.person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")

    # 如果设为主岗位，取消其他主岗位
    if data.is_primary:
        db.query(PersonPosition).filter(
            PersonPosition.person_id == data.person_id,
            PersonPosition.is_primary == True,
        ).update({PersonPosition.is_primary: False})

    pp = PersonPosition(**data.model_dump())
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return pp


@person_position_router.put("/{pp_id}", response_model=PersonPositionResponse)
def update_person_position(
    pp_id: int,
    data: PersonPositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """更新人员岗位"""
    pp = db.query(PersonPosition).filter(PersonPosition.id == pp_id).first()
    if not pp:
        raise HTTPException(status_code=404, detail="人员岗位记录不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果设为主岗位，取消其他主岗位
    if update_data.get("is_primary"):
        db.query(PersonPosition).filter(
            PersonPosition.person_id == pp.person_id,
            PersonPosition.id != pp_id,
            PersonPosition.is_primary == True,
        ).update({PersonPosition.is_primary: False})

    for key, value in update_data.items():
        setattr(pp, key, value)

    db.commit()
    db.refresh(pp)
    return pp


@person_position_router.delete("/{pp_id}")
def delete_person_position(
    pp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("unit_admin")),
):
    """删除人员岗位记录"""
    pp = db.query(PersonPosition).filter(PersonPosition.id == pp_id).first()
    if not pp:
        raise HTTPException(status_code=404, detail="人员岗位记录不存在")

    # 结束当前任职
    if pp.is_current:
        raise HTTPException(status_code=400, detail="当前任职记录，请先设置结束日期或标记为非当前任职")

    db.delete(pp)
    db.commit()
    return {"message": "人员岗位记录已删除"}