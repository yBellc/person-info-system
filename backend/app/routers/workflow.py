"""OA流程引擎路由 - 流程模板、流程实例（支持动态审批人、退回修改、请假余额）"""
from datetime import datetime, date
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workflow import WorkflowTemplate, WorkflowInstance, WorkflowNode
from app.models.user import User, OperationLog
from app.models.person import Person
from app.models.organization import Department, PersonPosition
from app.models.permission import Role, UserRole
from app.models.workspace import TodoItem
from app.models.security import LoginLog, LeaveBalance, LeaveRecord
from app.schemas.workflow import (
    WorkflowTemplateCreate, WorkflowTemplateUpdate, WorkflowTemplateResponse,
    WorkflowInstanceCreate, WorkflowInstanceApprove, WorkflowInstanceResponse,
    WorkflowInstanceListResponse, WorkflowNodeResponse, WorkflowInstanceModify,
)
from app.core.permissions import require_role
from app.services.message_center import send_message

router = APIRouter(tags=["OA流程"])


# ============ 动态审批人解析 ============

def _resolve_dynamic_handler(db: Session, applicant: User, node_cfg: dict) -> Optional[int]:
    """
    解析动态审批人：
    - handler_type=fixed: 直接用 handler_id
    - handler_type=dynamic: 按 handler_rule 自动匹配
      - dept_manager: 申请人所在部门的负责人
      - dept_leader: 申请人所在部门的分管领导（上级部门负责人）
      - unit_admin: 申请人所在单位的管理员
      - role:hr: 有hr角色的用户
      - role:finance: 有finance角色的用户
      - role:super_admin: 超级管理员
      - applicant_supervisor: 申请人的直属上级（PersonPosition中主岗位的上级）
    """
    handler_type = node_cfg.get("handler_type", "fixed")

    if handler_type == "fixed":
        return node_cfg.get("handler_id")

    rule = node_cfg.get("handler_rule", "")

    # 获取申请人的人员档案
    person = None
    if applicant.person_id:
        person = db.query(Person).filter(Person.id == applicant.person_id).first()

    if rule == "dept_manager":
        # 找申请人所在部门的负责人
        if person:
            # 通过PersonPosition找到当前主岗位的部门
            pp = db.query(PersonPosition).filter(
                PersonPosition.person_id == person.id,
                PersonPosition.is_current == True,
                PersonPosition.is_primary == True,
            ).first()
            if pp and pp.department_id:
                dept = db.query(Department).filter(Department.id == pp.department_id).first()
                if dept and dept.manager_id:
                    # manager_id是Person ID，需要找到对应的User
                    mgr_user = db.query(User).filter(User.person_id == dept.manager_id, User.is_active == True).first()
                    if mgr_user:
                        return mgr_user.id
        # fallback: 如果找不到部门负责人，用单位管理员
        if applicant.unit_id:
            admin = db.query(User).filter(
                User.unit_id == applicant.unit_id,
                User.role == "unit_admin",
                User.is_active == True,
            ).first()
            if admin:
                return admin.id

    elif rule == "dept_leader":
        # 找上级部门的负责人（分管领导）
        if person:
            pp = db.query(PersonPosition).filter(
                PersonPosition.person_id == person.id,
                PersonPosition.is_current == True,
                PersonPosition.is_primary == True,
            ).first()
            if pp and pp.department_id:
                dept = db.query(Department).filter(Department.id == pp.department_id).first()
                if dept and dept.parent_id:
                    parent_dept = db.query(Department).filter(Department.id == dept.parent_id).first()
                    if parent_dept and parent_dept.manager_id:
                        mgr_user = db.query(User).filter(User.person_id == parent_dept.manager_id, User.is_active == True).first()
                        if mgr_user:
                            return mgr_user.id
        # fallback: 超级管理员
        super_admin = db.query(User).filter(User.role == "super_admin", User.is_active == True).first()
        if super_admin:
            return super_admin.id

    elif rule == "unit_admin":
        if applicant.unit_id:
            admin = db.query(User).filter(
                User.unit_id == applicant.unit_id,
                User.role == "unit_admin",
                User.is_active == True,
            ).first()
            if admin:
                return admin.id

    elif rule.startswith("role:"):
        # 按角色查找: role:hr / role:finance / role:super_admin
        role_code = rule.split(":")[1]
        # 先找有该角色的用户
        role = db.query(Role).filter(Role.code == role_code).first()
        if role:
            user_roles = db.query(UserRole).filter(UserRole.role_id == role.id).all()
            for ur in user_roles:
                u = db.query(User).filter(User.id == ur.user_id, User.is_active == True).first()
                if u:
                    return u.id
        # fallback: 按User.role字段找
        u = db.query(User).filter(User.role == role_code, User.is_active == True).first()
        if u:
            return u.id

    elif rule == "super_admin":
        u = db.query(User).filter(User.role == "super_admin", User.is_active == True).first()
        if u:
            return u.id

    # 最终fallback: 固定handler_id
    return node_cfg.get("handler_id")


def _log_workflow_op(db: Session, user: User, action: str, inst: WorkflowInstance, detail: str = None, old_value: dict = None, new_value: dict = None):
    """记录流程操作审计日志"""
    log = OperationLog(
        operator_id=user.id, operator_name=user.username, action=action,
        detail=detail, target_type="workflow", target_id=inst.id,
        old_value=old_value, new_value=new_value,
    )
    db.add(log)


# ============ 请假余额检查与扣减 ============

LEAVE_TYPE_MAP = {
    "年假": "annual", "事假": "personal", "病假": "sick",
    "婚假": "marriage", "产假": "maternity", "丧假": "compassionate", "调休": "compensatory",
}

def _check_leave_balance(db: Session, user_id: int, leave_type: str, days: float) -> tuple[bool, str]:
    """检查请假余额是否充足"""
    balance_type = LEAVE_TYPE_MAP.get(leave_type)
    if not balance_type:
        return True, ""  # 未映射的类型不检查余额

    # 事假和病假不检查余额（无上限），但记录
    if balance_type in ("personal", "sick"):
        return True, ""

    year = date.today().year
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == user_id,
        LeaveBalance.year == year,
        LeaveBalance.leave_type == balance_type,
    ).first()

    if not balance:
        return False, f"您{year}年{leave_type}余额未初始化，请联系人事管理员"

    if balance.remaining_days < days:
        return False, f"{leave_type}余额不足：剩余{balance.remaining_days}天，申请{days}天"

    return True, ""


def _deduct_leave_balance(db: Session, user_id: int, leave_type: str, days: float, instance_id: int):
    """扣减请假余额并记录"""
    balance_type = LEAVE_TYPE_MAP.get(leave_type)
    if not balance_type or balance_type in ("personal", "sick"):
        # 事假/病假不扣余额，但记录
        record = LeaveRecord(
            workflow_instance_id=instance_id, user_id=user_id,
            leave_type=balance_type or "other",
            start_date=date.today(), end_date=date.today(),
            days=days, deducted=False,
        )
        db.add(record)
        return

    year = date.today().year
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == user_id,
        LeaveBalance.year == year,
        LeaveBalance.leave_type == balance_type,
    ).first()

    if balance:
        balance.used_days += days
        balance.remaining_days -= days

    # 记录扣减
    form_data = db.query(WorkflowInstance).get(instance_id).form_data or {}
    # form_data 中的日期是字符串，需要转换为 date 对象
    raw_start = form_data.get("start_date", date.today())
    raw_end = form_data.get("end_date", date.today())
    if isinstance(raw_start, str):
        try:
            raw_start = date.fromisoformat(raw_start)
        except ValueError:
            raw_start = date.today()
    if isinstance(raw_end, str):
        try:
            raw_end = date.fromisoformat(raw_end)
        except ValueError:
            raw_end = date.today()
    record = LeaveRecord(
        workflow_instance_id=instance_id, user_id=user_id,
        leave_type=balance_type,
        start_date=raw_start,
        end_date=raw_end,
        days=days, deducted=True,
    )
    db.add(record)


# ============ 流程模板路由 ============

@router.get("/workflow-templates", response_model=List[WorkflowTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None, description="流程类别"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取流程模板列表"""
    query = db.query(WorkflowTemplate)
    if category:
        query = query.filter(WorkflowTemplate.category == category)
    if is_active is not None:
        query = query.filter(WorkflowTemplate.is_active == is_active)
    return query.order_by(WorkflowTemplate.category, WorkflowTemplate.name).all()


@router.post("/workflow-templates", response_model=WorkflowTemplateResponse)
def create_template(
    data: WorkflowTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """创建流程模板"""
    existing = db.query(WorkflowTemplate).filter(WorkflowTemplate.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="流程编码已存在")
    template = WorkflowTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
def update_template(
    template_id: int,
    data: WorkflowTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """更新流程模板"""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="流程模板不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/workflow-templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """删除流程模板（软删除）"""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="流程模板不存在")
    template.is_active = False
    db.commit()
    return {"message": "流程模板已禁用"}


# ============ 流程实例路由 ============

def _build_instance_response(db: Session, inst: WorkflowInstance) -> dict:
    """构建流程实例响应"""
    applicant = db.query(User).filter(User.id == inst.applicant_id).first()
    handler = db.query(User).filter(User.id == inst.current_handler_id).first() if inst.current_handler_id else None
    template = inst.template

    from app.models.expense import WorkflowAttachment
    attachments = db.query(WorkflowAttachment).filter(
        WorkflowAttachment.instance_id == inst.id
    ).order_by(WorkflowAttachment.created_at.desc()).all()

    nodes = []
    for node in inst.nodes:
        handler_name = None
        if node.handler_id:
            h = db.query(User).filter(User.id == node.handler_id).first()
            handler_name = h.username if h else None
        nodes.append({
            "id": node.id,
            "instance_id": node.instance_id,
            "seq": node.seq,
            "node_key": node.node_key,
            "node_name": node.node_name,
            "node_type": node.node_type,
            "handler_id": node.handler_id,
            "handler_name": handler_name,
            "status": node.status,
            "opinion": node.opinion,
            "handled_at": node.handled_at,
            "created_at": node.created_at,
        })

    return {
        "id": inst.id,
        "template_id": inst.template_id,
        "applicant_id": inst.applicant_id,
        "applicant_name": applicant.username if applicant else None,
        "title": inst.title,
        "form_data": inst.form_data,
        "status": inst.status,
        "current_node_key": inst.current_node_key,
        "current_node_name": inst.current_node_name,
        "current_handler_id": inst.current_handler_id,
        "current_handler_name": handler.username if handler else None,
        "submitted_at": inst.submitted_at,
        "finished_at": inst.finished_at,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at,
        "template_name": template.name if template else None,
        "template_category": template.category if template else None,
        "form_schema": template.form_schema if template else None,
        "attachments": [{
            "id": a.id,
            "filename": a.filename,
            "file_size": a.file_size,
            "file_type": a.file_type,
            "attachment_type": a.attachment_type,
            "is_invoice": a.is_invoice,
            "uploaded_by": a.uploaded_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "download_url": f"/api/v1/attachments/{a.id}/download",
        } for a in attachments],
        "nodes": nodes,
    }


@router.get("/workflow-instances", response_model=WorkflowInstanceListResponse)
def list_instances(
    status: Optional[str] = Query(None, description="状态筛选"),
    category: Optional[str] = Query(None, description="流程类别"),
    tab: Optional[str] = Query(None, description="标签: my_apply/my_approve/my_handled/approval_record/all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取流程实例列表"""
    query = db.query(WorkflowInstance)

    # 标签筛选
    if tab == "my_apply":
        query = query.filter(WorkflowInstance.applicant_id == current_user.id)
    elif tab == "my_approve":
        # 待我审批：只有当前处理人是我且状态为 pending 的流程
        query = query.filter(
            WorkflowInstance.current_handler_id == current_user.id,
            WorkflowInstance.status == "pending",
        )
    elif tab == "my_handled":
        # 我已审批：我作为处理人已处理过的所有流程（含已通过和已拒绝）
        handled_ids = db.query(WorkflowNode.instance_id).filter(
            WorkflowNode.handler_id == current_user.id,
            WorkflowNode.status.in_(["approved", "rejected", "done", "skipped"]),
        )
        query = query.filter(WorkflowInstance.id.in_(handled_ids))
    elif tab == "approval_record":
        # 审批记录（仅管理员/领导可见）：所有已完成的流程，供领导查看历史审批
        if current_user.role in ("super_admin", "unit_admin"):
            query = query.filter(WorkflowInstance.status.in_(["approved", "rejected"]))
        else:
            # 普通用户只能看自己参与过的已完成流程
            handled_ids = db.query(WorkflowNode.instance_id).filter(
                WorkflowNode.handler_id == current_user.id,
                WorkflowNode.status.in_(["approved", "rejected"]),
            )
            query = query.filter(WorkflowInstance.id.in_(handled_ids))
    elif tab == "all":
        if current_user.role not in ("super_admin", "unit_admin"):
            raise HTTPException(status_code=403, detail="无权查看所有流程")
    else:
        # 默认：我发起的 + 我当前待审批的 + 我历史参与过的
        handled_ids = db.query(WorkflowNode.instance_id).filter(
            WorkflowNode.handler_id == current_user.id
        )
        query = query.filter(
            (WorkflowInstance.applicant_id == current_user.id) |
            (WorkflowInstance.current_handler_id == current_user.id) |
            (WorkflowInstance.id.in_(handled_ids))
        )

    if status:
        query = query.filter(WorkflowInstance.status == status)

    if category:
        query = query.join(WorkflowTemplate).filter(WorkflowTemplate.category == category)

    total = query.count()
    instances = query.order_by(WorkflowInstance.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [_build_instance_response(db, inst) for inst in instances]
    return {"items": items, "total": total}


@router.get("/workflow-instances/{instance_id}", response_model=WorkflowInstanceResponse)
def get_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """获取流程实例详情"""
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")
    return _build_instance_response(db, inst)


@router.post("/workflow-instances", response_model=WorkflowInstanceResponse)
def create_instance(
    data: WorkflowInstanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """发起流程（支持动态审批人 + 请假余额检查）"""
    template = db.query(WorkflowTemplate).filter(
        WorkflowTemplate.id == data.template_id,
        WorkflowTemplate.is_active == True,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="流程模板不存在或已禁用")

    flow_nodes = template.flow_nodes or []
    if not flow_nodes:
        raise HTTPException(status_code=400, detail="流程模板未配置审批节点")

    # 请假流程：检查余额
    if template.category == "leave" and data.form_data:
        leave_type = data.form_data.get("leave_type", "")
        days = float(data.form_data.get("days", 0))
        if leave_type and days > 0:
            ok, msg = _check_leave_balance(db, current_user.id, leave_type, days)
            if not ok:
                raise HTTPException(status_code=400, detail=msg)

    # 创建流程实例
    inst = WorkflowInstance(
        template_id=template.id,
        applicant_id=current_user.id,
        title=data.title,
        form_data=data.form_data,
        status="pending",
        submitted_at=datetime.utcnow(),
    )
    db.add(inst)
    db.flush()

    # 创建节点记录（解析动态审批人）
    for i, node_cfg in enumerate(flow_nodes):
        handler_id = _resolve_dynamic_handler(db, current_user, node_cfg)
        node = WorkflowNode(
            instance_id=inst.id,
            seq=i,
            node_key=node_cfg.get("key", f"node_{i}"),
            node_name=node_cfg.get("name", f"节点{i}"),
            node_type=node_cfg.get("type", "approval"),
            handler_id=handler_id,
            status="pending",
        )
        db.add(node)

    # 设置当前节点为第一个审批节点
    first_node = flow_nodes[0]
    first_handler_id = _resolve_dynamic_handler(db, current_user, first_node)
    inst.current_node_key = first_node.get("key", "node_0")
    inst.current_node_name = first_node.get("name", "节点0")
    inst.current_handler_id = first_handler_id

    # 给审批人创建待办
    if inst.current_handler_id:
        todo = TodoItem(
            user_id=inst.current_handler_id,
            title=f"审批: {data.title}",
            content=f"流程类别: {template.name}\n申请人: {current_user.username}",
            category="approval",
            resource_type="workflow",
            resource_id=inst.id,
            priority=1,
        )
        db.add(todo)
        send_message(db, inst.current_handler_id, msg_type="approval", title=f"待审批: {data.title}", content=f"申请人: {current_user.username}\n请前往审批流程页面处理", resource_type="workflow", resource_id=inst.id, sender_id=current_user.id, extra={"router": "/workflow"})

    # 审计日志
    ip = request.client.host if request.client else None
    _log_workflow_op(db, current_user, "workflow_submit", inst,
                     f"提交流程: {data.title}", new_value=data.form_data)

    db.commit()
    db.refresh(inst)
    return _build_instance_response(db, inst)


@router.post("/workflow-instances/{instance_id}/approve", response_model=WorkflowInstanceResponse)
def approve_instance(
    instance_id: int,
    data: WorkflowInstanceApprove,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """审批流程（同意/拒绝/退回修改）"""
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    if inst.status not in ("pending",):
        raise HTTPException(status_code=400, detail="该流程不在待审批状态")

    if inst.current_handler_id != current_user.id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="您不是当前审批人")

    current_node = db.query(WorkflowNode).filter(
        WorkflowNode.instance_id == inst.id,
        WorkflowNode.node_key == inst.current_node_key,
    ).first()

    if not current_node:
        raise HTTPException(status_code=400, detail="当前节点不存在")

    now = datetime.utcnow()
    old_status = inst.status

    if data.action == "approve":
        current_node.status = "approved"
        current_node.opinion = data.opinion
        current_node.handled_at = now

        all_nodes = db.query(WorkflowNode).filter(
            WorkflowNode.instance_id == inst.id
        ).order_by(WorkflowNode.seq).all()

        next_node = None
        for n in all_nodes:
            if n.seq > current_node.seq and n.status == "pending":
                next_node = n
                break

        if next_node:
            inst.current_node_key = next_node.node_key
            inst.current_node_name = next_node.node_name
            inst.current_handler_id = next_node.handler_id
            if next_node.handler_id:
                todo = TodoItem(
                    user_id=next_node.handler_id,
                    title=f"审批: {inst.title}",
                    content=f"流程类别: {inst.template.name}\n申请人: {inst.applicant.username if inst.applicant else ''}",
                    category="approval", resource_type="workflow", resource_id=inst.id, priority=1,
                )
                db.add(todo)
                send_message(db, next_node.handler_id, "approval", f"待审批: {inst.title}", f"上一节点已审批通过，请您处理", resource_id=inst.id, sender_id=current_user.id, extra={"router": "/workflow"})
        else:
            # 流程完成
            inst.status = "approved"
            inst.current_node_key = None
            inst.current_node_name = None
            inst.current_handler_id = None
            inst.finished_at = now

            # 请假流程：扣减余额
            if inst.template and inst.template.category == "leave" and inst.form_data:
                leave_type = inst.form_data.get("leave_type", "")
                days = float(inst.form_data.get("days", 0))
                if leave_type and days > 0:
                    _deduct_leave_balance(db, inst.applicant_id, leave_type, days, inst.id)

            todo = TodoItem(
                user_id=inst.applicant_id,
                title=f"流程已通过: {inst.title}",
                content="您的申请已审批通过",
                category="notification", resource_type="workflow", resource_id=inst.id,
            )
            db.add(todo)
            send_message(db, inst.applicant_id, msg_type="approval", title=f"申请已通过: {inst.title}", content="您的流程申请已全部审批通过，请到流程页面查看", resource_type="workflow", resource_id=inst.id, sender_id=current_user.id, extra={"router": "/workflow"})

        _log_workflow_op(db, current_user, "workflow_approve", inst,
                         f"审批同意: {data.opinion or '无'}", old_value={"status": old_status}, new_value={"status": inst.status})

    elif data.action == "reject":
        current_node.status = "rejected"
        current_node.opinion = data.opinion
        current_node.handled_at = now
        inst.status = "rejected"
        inst.current_node_key = None
        inst.current_node_name = None
        inst.current_handler_id = None
        inst.finished_at = now

        todo = TodoItem(
            user_id=inst.applicant_id,
            title=f"流程被拒绝: {inst.title}",
            content=f"审批意见: {data.opinion or '无'}",
            category="notification", resource_type="workflow", resource_id=inst.id,
        )
        db.add(todo)
        send_message(db, inst.applicant_id, "approval", f"申请被拒绝: {inst.title}", f"审批意见: {data.opinion or '无'}", resource_id=inst.id, sender_id=current_user.id, extra={"router": "/workflow"})

        _log_workflow_op(db, current_user, "workflow_reject", inst,
                         f"审批拒绝: {data.opinion or '无'}", old_value={"status": old_status}, new_value={"status": "rejected"})

    elif data.action == "return":
        # 退回修改：流程不结束，状态变为 returned，等申请人修改后重新提交
        current_node.status = "returned"
        current_node.opinion = data.opinion
        current_node.handled_at = now
        inst.status = "returned"
        inst.current_handler_id = inst.applicant_id  # 退回给申请人

        todo = TodoItem(
            user_id=inst.applicant_id,
            title=f"流程需修改: {inst.title}",
            content=f"审批人要求修改: {data.opinion or '请补充完善信息'}",
            category="approval", resource_type="workflow", resource_id=inst.id, priority=2,
        )
        db.add(todo)
        send_message(db, inst.applicant_id, "approval", f"流程需修改: {inst.title}", f"退回原因: {data.opinion or '请补充完善信息'}", resource_id=inst.id, sender_id=current_user.id, extra={"router": "/workflow"})

        _log_workflow_op(db, current_user, "workflow_return", inst,
                         f"退回修改: {data.opinion or '无'}", old_value={"status": old_status}, new_value={"status": "returned"})

    else:
        raise HTTPException(status_code=400, detail="无效的审批操作")

    db.commit()
    db.refresh(inst)
    return _build_instance_response(db, inst)


@router.post("/workflow-instances/{instance_id}/resubmit", response_model=WorkflowInstanceResponse)
def resubmit_instance(
    instance_id: int,
    data: WorkflowInstanceModify,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """退回后修改表单并重新提交（从退回节点继续审批，不从头开始）"""
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    if inst.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有申请人可以修改")

    if inst.status != "returned":
        raise HTTPException(status_code=400, detail="只有被退回的流程才能重新提交")

    old_form = inst.form_data
    old_title = inst.title

    # 更新表单数据
    if data.form_data:
        inst.form_data = data.form_data
    if data.title:
        inst.title = data.title

    # 找到被退回的节点，重新设为pending
    returned_node = db.query(WorkflowNode).filter(
        WorkflowNode.instance_id == inst.id,
        WorkflowNode.status == "returned",
    ).order_by(WorkflowNode.seq.desc()).first()

    if returned_node:
        returned_node.status = "pending"
        returned_node.opinion = None
        returned_node.handled_at = None
        inst.current_node_key = returned_node.node_key
        inst.current_node_name = returned_node.node_name
        inst.current_handler_id = returned_node.handler_id

        # 给审批人重新创建待办
        if returned_node.handler_id:
            todo = TodoItem(
                user_id=returned_node.handler_id,
                title=f"重新审批: {inst.title}",
                content=f"申请人已修改，请重新审批\n流程: {inst.template.name if inst.template else ''}",
                category="approval", resource_type="workflow", resource_id=inst.id, priority=1,
            )
            db.add(todo)

    inst.status = "pending"

    _log_workflow_op(db, current_user, "workflow_resubmit", inst,
                     f"修改后重新提交",
                     old_value={"form": old_form, "title": old_title},
                     new_value={"form": inst.form_data, "title": inst.title})

    db.commit()
    db.refresh(inst)
    return _build_instance_response(db, inst)


@router.post("/workflow-instances/{instance_id}/withdraw")
def withdraw_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("person")),
):
    """撤回流程（仅申请人，且在审批中）"""
    inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="流程实例不存在")

    if inst.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能撤回自己的流程")

    if inst.status != "pending":
        raise HTTPException(status_code=400, detail="只能在审批中撤回")

    inst.status = "withdrawn"
    inst.finished_at = datetime.utcnow()
    inst.current_handler_id = None
    inst.current_node_key = None
    inst.current_node_name = None

    # 取消相关待办
    db.query(TodoItem).filter(
        TodoItem.resource_type == "workflow",
        TodoItem.resource_id == inst.id,
        TodoItem.status == "pending",
    ).update({TodoItem.status: "done"})

    db.commit()
    return {"message": "流程已撤回"}
