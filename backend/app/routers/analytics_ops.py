"""驾驶舱、审批数据分析、批量操作、三员分立相关路由（P1-1 / P1-3 / P1-4 / P1-2）
涉密内网专用，不依赖外网数据
"""
from collections import Counter
from datetime import date as _date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import (
    get_current_user, require_admin, require_super_admin,
)
from app.models.user import User, Unit
from app.models.person import Person
from app.models.workflow import WorkflowInstance, WorkflowNode
from app.models.hr_management import (
    ContractRecord, TransferRecord, ResignationApplication,
    AttendanceRecord, PerformanceRecord, KEY_CHANGE_FIELDS,
)
from app.models.user import OperationLog
from app.models.security import LoginLog
from app.models.organization import Department
from app import settings

router = APIRouter(tags=["驾驶舱与运营分析"])


# ======================================================================
# P1-1: 领导驾驶舱
# ======================================================================

@router.get("/dashboard/overview", summary="驾驶舱总览（领导首页）")
def dashboard_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    today = _date.today()
    # 1. 人员基础数据
    total_person = db.query(Person).filter(Person.is_deleted == False).count()

    gender_q = db.query(Person.gender, func.count(Person.id)) \
        .filter(Person.is_deleted == False) \
        .group_by(Person.gender).all()
    gender_stats = {g or "未知": c for g, c in gender_q}

    edu_q = db.query(Person.education_level, func.count(Person.id)) \
        .filter(Person.is_deleted == False, Person.education_level.isnot(None)) \
        .group_by(Person.education_level).order_by(func.count(Person.id).desc()).all()
    edu_stats = [{"name": e, "value": c} for e, c in edu_q]

    polit_q = db.query(Person.political_status, func.count(Person.id)) \
        .filter(Person.is_deleted == False, Person.political_status.isnot(None)) \
        .group_by(Person.political_status).order_by(func.count(Person.id).desc()).all()
    polit_stats = [{"name": p, "value": c} for p, c in polit_q]

    # 年龄分布（5档）
    ages_raw = [p.birth_date for p in db.query(Person.birth_date)
                .filter(Person.is_deleted == False, Person.birth_date.isnot(None)).all()]
    age_buckets = {"30岁及以下": 0, "31-40岁": 0, "41-50岁": 0, "51-60岁": 0, "60岁以上": 0}
    for bd in ages_raw:
        try:
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception:
            continue
        if age <= 30:
            age_buckets["30岁及以下"] += 1
        elif age <= 40:
            age_buckets["31-40岁"] += 1
        elif age <= 50:
            age_buckets["41-50岁"] += 1
        elif age <= 60:
            age_buckets["51-60岁"] += 1
        else:
            age_buckets["60岁以上"] += 1

    # 部门人数 TOP
    dept_q = db.query(Person.department, func.count(Person.id)) \
        .filter(Person.is_deleted == False, Person.department.isnot(None)) \
        .group_by(Person.department).order_by(func.count(Person.id).desc()).limit(10).all()
    dept_stats = [{"name": d, "value": c} for d, c in dept_q]

    # 2. 流程审批概览
    total_instances = db.query(WorkflowInstance).count()
    pending_count = db.query(WorkflowInstance).filter(WorkflowInstance.status == "pending").count()
    today_start = datetime.combine(today, datetime.min.time())
    today_done = db.query(WorkflowInstance).filter(
        WorkflowInstance.finished_at.isnot(None),
        WorkflowInstance.finished_at >= today_start,
    ).count()

    # 平均审批时长
    finished = db.query(WorkflowInstance.submitted_at, WorkflowInstance.finished_at) \
        .filter(WorkflowInstance.submitted_at.isnot(None),
                WorkflowInstance.finished_at.isnot(None)).limit(1000).all()
    if finished:
        durations = [(f[1] - f[0]).total_seconds() for f in finished if f[0] and f[1]]
        avg_hours = round(sum(durations) / len(durations) / 3600, 1) if durations else 0
    else:
        avg_hours = 0

    # 3. 预警提醒
    #   合同到期（30天内）
    soon_days = 30
    cutoff = today + timedelta(days=soon_days)
    expiring_contracts = db.query(ContractRecord).join(Person).filter(
        ContractRecord.status == "active",
        ContractRecord.end_date.isnot(None),
        ContractRecord.end_date <= cutoff,
        Person.is_deleted == False,
    ).order_by(ContractRecord.end_date.asc()).limit(10).all()
    expiring_list = []
    for cr in expiring_contracts:
        p = db.query(Person).get(cr.person_id)
        expiring_list.append({
            "person_name": p.name if p else None,
            "contract_type": cr.contract_type,
            "contract_no": cr.contract_no,
            "end_date": cr.end_date.isoformat(),
            "days_left": (cr.end_date - today).days,
        })

    #   即将退休（男60、女55，以身份证号出生日期估算）
    retire_soon = []
    persons = db.query(Person).filter(Person.is_deleted == False,
                                       Person.birth_date.isnot(None)).all()
    for p in persons:
        if not p.gender or not p.birth_date:
            continue
        retire_age = 60 if p.gender == "男" else 55
        age = today.year - p.birth_date.year - ((today.month, today.day) < (p.birth_date.month, p.birth_date.day))
        years_left = retire_age - age
        if 0 <= years_left <= 2:
            retire_soon.append({
                "person_name": p.name, "gender": p.gender,
                "birth_date": p.birth_date.isoformat(),
                "department": p.department,
                "years_left": years_left,
                "retire_age": retire_age,
            })
    retire_soon.sort(key=lambda x: x["years_left"])
    retire_soon = retire_soon[:10]

    # 合同过期
    expired_contracts_count = db.query(ContractRecord).filter(
        ContractRecord.status == "active",
        ContractRecord.end_date.isnot(None),
        ContractRecord.end_date < today,
    ).count()

    # 4. 今日动态
    today_ops = db.query(OperationLog).filter(
        OperationLog.created_at >= today_start
    ).order_by(OperationLog.created_at.desc()).limit(10).all()
    today_op_list = [{
        "action": o.action, "operator_name": o.operator_name,
        "detail": o.detail,
        "time": o.created_at.strftime("%H:%M:%S"),
    } for o in today_ops]

    return {
        "overview": {
            "total_person": total_person,
            "male": gender_stats.get("男", 0),
            "female": gender_stats.get("女", 0),
            "unknown_gender": gender_stats.get("未知", 0),
            "total_users": db.query(User).filter(User.is_active == True).count(),
            "total_units": db.query(Unit).count(),
        },
        "demographics": {
            "age_distribution": [{"name": k, "value": v} for k, v in age_buckets.items()],
            "education_distribution": edu_stats,
            "political_distribution": polit_stats,
            "department_top": dept_stats,
        },
        "approval": {
            "total_instances": total_instances,
            "pending_count": pending_count,
            "today_done_count": today_done,
            "avg_approval_hours": avg_hours,
        },
        "warnings": {
            "expiring_contracts": expiring_list,
            "expiring_contracts_total": db.query(ContractRecord).filter(
                ContractRecord.status == "active",
                ContractRecord.end_date.isnot(None),
                ContractRecord.end_date <= cutoff,
            ).count(),
            "expired_contracts": expired_contracts_count,
            "retire_soon": retire_soon,
        },
        "today_operations": today_op_list,
    }


# ======================================================================
# P1-3: 历史审批数据分析
# ======================================================================

@router.get("/analytics/approval", summary="审批流程优化分析")
def analytics_approval(
    days: int = Query(90, ge=7, le=3650, description="分析多少天内的数据"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    # 1. 各模板统计
    from app.models.workflow import WorkflowTemplate
    rows = db.query(WorkflowInstance, WorkflowTemplate).join(
        WorkflowTemplate, WorkflowInstance.template_id == WorkflowTemplate.id
    ).filter(WorkflowInstance.created_at >= cutoff).all()

    by_template = {}
    durations_by_template = {}
    for inst, tmpl in rows:
        by_template.setdefault(tmpl.name, {"total": 0, "approved": 0, "rejected": 0,
                                            "pending": 0, "withdrawn": 0})
        by_template[tmpl.name]["total"] += 1
        st = inst.status
        if st in by_template[tmpl.name]:
            by_template[tmpl.name][st] += 1
        if inst.submitted_at and inst.finished_at and st == "approved":
            dur = (inst.finished_at - inst.submitted_at).total_seconds() / 3600
            durations_by_template.setdefault(tmpl.name, []).append(dur)

    for name, d in by_template.items():
        durs = durations_by_template.get(name, [])
        d["avg_hours"] = round(sum(durs) / len(durs), 1) if durs else 0
        d["reject_rate"] = round(d["rejected"] / d["total"] * 100, 1) if d["total"] else 0

    # 2. 流程节点瓶颈分析（哪个节点最慢）
    nodes = db.query(WorkflowNode, WorkflowTemplate.name).join(
        WorkflowInstance, WorkflowNode.instance_id == WorkflowInstance.id
    ).join(
        WorkflowTemplate, WorkflowInstance.template_id == WorkflowTemplate.id
    ).filter(
        WorkflowNode.status == "approved",
        WorkflowNode.handled_at.isnot(None),
        WorkflowInstance.created_at >= cutoff,
    ).limit(5000).all()

    node_waits = []
    for node, tmpl_name in nodes:
        # 节点耗时：handled_at - 上一个节点的 handled_at 或 submitted_at
        prev = db.query(WorkflowInstance).get(node.instance_id)
        if not prev:
            continue
        # 找同实例 seq < node.seq 的最后一条已处理节点
        prev_nodes = db.query(WorkflowNode).filter(
            WorkflowNode.instance_id == node.instance_id,
            WorkflowNode.seq < node.seq,
            WorkflowNode.handled_at.isnot(None),
        ).order_by(WorkflowNode.seq.desc()).first()
        start = prev_nodes.handled_at if prev_nodes else prev.submitted_at
        if start and node.handled_at:
            hours = (node.handled_at - start).total_seconds() / 3600
            if hours >= 0:
                node_waits.append({
                    "template": tmpl_name,
                    "node_name": node.node_name,
                    "hours": hours,
                    "handler_id": node.handler_id,
                })

    # 按(模板, 节点)聚合平均耗时
    agg = {}
    for nw in node_waits:
        key = (nw["template"], nw["node_name"])
        agg.setdefault(key, []).append(nw["hours"])
    bottleneck = []
    for (tmpl, node), hrs in agg.items():
        bottleneck.append({
            "template": tmpl, "node_name": node,
            "count": len(hrs),
            "avg_hours": round(sum(hrs) / len(hrs), 1),
            "max_hours": round(max(hrs), 1),
        })
    bottleneck.sort(key=lambda x: x["avg_hours"], reverse=True)
    bottleneck = bottleneck[:20]

    # 优化建议
    suggestions = []
    slow_threshold_hours = 24
    for b in bottleneck[:5]:
        if b["avg_hours"] >= slow_threshold_hours:
            suggestions.append(
                f"【{b['template']}】的「{b['node_name']}」环节平均耗时 {b['avg_hours']} 小时，"
                f"建议：检查该节点审批人是否有空、是否需要设置代审批或AB角，或调整节点顺序。"
            )
    for name, d in by_template.items():
        if d.get("reject_rate", 0) >= 20 and d["total"] >= 5:
            suggestions.append(
                f"【{name}】驳回率 {d['reject_rate']}%（共 {d['total']} 件，驳回 {d['rejected']} 件），"
                f"建议：检查表单项是否清楚、提示文案是否完善，或组织一次填报培训。"
            )
    if not suggestions:
        suggestions.append("当前各项流程运行良好，暂未发现明显瓶颈，继续保持。")

    return {
        "analyzed_days": days,
        "template_stats": [{"name": k, **v} for k, v in by_template.items()],
        "node_bottleneck": bottleneck,
        "optimization_suggestions": suggestions,
    }


# ======================================================================
# P1-4: 批量操作
# ======================================================================

@router.post("/batch/transfer-department", summary="批量调整部门/岗位/职级")
def batch_transfer(
    payload: dict = Body(...),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    payload:
      person_ids: [int]  目标人员列表
      to_department: str (可选)
      to_position: str (可选)
      to_rank: str (可选)
      effective_date: str YYYY-MM-DD
      reason: str
    """
    pids = payload.get("person_ids") or []
    if not pids:
        raise HTTPException(400, "未选择人员")
    effective = payload.get("effective_date")
    if effective:
        effective = _date.fromisoformat(effective[:10])

    count = 0
    for pid in pids:
        p = db.query(Person).filter(Person.id == pid, Person.is_deleted == False).first()
        if not p:
            continue
        # 生成调岗记录（待复核）
        rec = TransferRecord(
            person_id=pid,
            transfer_type="department",
            from_department=p.department,
            from_position=p.position,
            from_rank=p.rank,
            to_department=payload.get("to_department"),
            to_position=payload.get("to_position"),
            to_rank=payload.get("to_rank"),
            effective_date=effective,
            reason=payload.get("reason", "批量调整"),
            created_by=current_user.id,
            is_approved=False,
        )
        db.add(rec)
        count += 1

    _log(db, current_user, "batch_transfer",
         f"批量提交 {count} 人部门/岗位/职级调整，等待复核",
         new_value={"count": count, "targets": pids[:50]})
    db.commit()
    return {"message": f"已提交 {count} 条调动记录，等待超管复核生效"}


@router.post("/batch/import-excel-attendance", summary="批量导入考勤（Excel）")
async def batch_import_attendance(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Excel 列：姓名(必填) / 身份证(或人员ID) / 应出勤 / 实出勤 / 迟到 / 早退 / ...
    第一行表头，系统按姓名或身份证匹配人员。
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise HTTPException(500, "未安装 openpyxl")

    content = await file.read()
    import io
    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(400, "Excel 为空")

    headers = [str(c).strip() if c is not None else "" for c in rows[0]]
    idx_name = headers.index("姓名") if "姓名" in headers else None
    idx_idcard = headers.index("身份证") if "身份证" in headers else None
    if idx_name is None and idx_idcard is None:
        raise HTTPException(400, "表头必须包含「姓名」或「身份证」列")

    def col(name):
        return headers.index(name) if name in headers else None

    total = ok = fail = 0
    fail_msgs = []
    for row in rows[1:]:
        if not row or all(v is None or str(v).strip() == "" for v in row):
            continue
        total += 1
        # 匹配人员
        p = None
        if idx_idcard is not None and row[idx_idcard]:
            idc = str(row[idx_idcard]).strip()
            p = db.query(Person).filter(Person.id_card == idc,
                                         Person.is_deleted == False).first()
        if not p and idx_name is not None and row[idx_name]:
            nm = str(row[idx_name]).strip()
            p = db.query(Person).filter(Person.name == nm,
                                         Person.is_deleted == False).first()
        if not p:
            fail += 1
            fail_msgs.append(f"第 {total + 1} 行未找到匹配人员")
            continue

        try:
            exist = db.query(AttendanceRecord).filter(
                AttendanceRecord.person_id == p.id,
                AttendanceRecord.year == year,
                AttendanceRecord.month == month,
            ).first()
            if exist:
                rec = exist
            else:
                rec = AttendanceRecord(person_id=p.id, year=year, month=month,
                                       created_by=current_user.id)
                db.add(rec)

            mapping = [
                ("应出勤天数", "work_days", float),
                ("实出勤天数", "actual_days", float),
                ("迟到次数", "late_count", int),
                ("早退次数", "early_leave_count", int),
                ("旷工天数", "absenteeism_days", float),
                ("事假天数", "personal_leave_days", float),
                ("病假天数", "sick_leave_days", float),
                ("年假天数", "annual_leave_days", float),
                ("出差天数", "business_trip_days", float),
                ("加班小时数", "overtime_hours", float),
            ]
            for (hdr, attr, conv) in mapping:
                i = col(hdr)
                if i is None:
                    continue
                v = row[i]
                try:
                    if v is not None and str(v).strip() != "":
                        setattr(rec, attr, conv(v))
                except Exception:
                    pass
            ok += 1
        except Exception as e:
            fail += 1
            fail_msgs.append(f"第 {total + 1} 行处理失败: {e}")

    db.commit()
    _log(db, current_user, "batch_import_attendance",
         f"导入考勤 {year}年{month}月: 总计{total} 成功{ok} 失败{fail}",
         new_value={"year": year, "month": month, "total": total, "ok": ok, "fail": fail})
    return {"total": total, "ok": ok, "fail": fail, "fail_details": fail_msgs[:20]}


@router.post("/batch/create-persons", summary="批量入职（按模板批量创建人员+自动关联名单）")
def batch_create_persons(
    persons: List[dict] = Body(...),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    批量新增人员。每个元素:
    { name, gender, id_card, department, position, rank, unit_id, birth_date, join_unit_date, phone }
    对身份证号做唯一性校验。
    """
    count, errs = 0, []
    for idx, d in enumerate(persons, 1):
        if not d.get("name") or not d.get("id_card"):
            errs.append(f"第{idx}条缺少姓名或身份证号，跳过")
            continue
        idc = str(d["id_card"]).strip()
        exist = db.query(Person).filter(Person.id_card == idc).first()
        if exist:
            errs.append(f"第{idx}条身份证号 {idc} 已存在（{exist.name}），跳过")
            continue
        if len(idc) != 18:
            errs.append(f"第{idx}条身份证号长度不是18位，跳过")
            continue
        p = Person(created_by=current_user.id, data_status="confirmed")
        date_fields = ("birth_date", "join_unit_date", "work_start_date",
                       "party_join_date", "graduation_date")
        for fld in date_fields:
            v = d.get(fld)
            if isinstance(v, str) and v:
                try:
                    d[fld] = _date.fromisoformat(v[:10])
                except Exception:
                    d[fld] = None
        for k, v in d.items():
            if hasattr(p, k) and k not in ("id", "created_at", "updated_at",
                                            "is_deleted", "deleted_at", "deleted_by"):
                setattr(p, k, v)
        db.add(p)
        count += 1

    _log(db, current_user, "batch_create_persons",
         f"批量入职: 成功{count} 失败{len(errs)}",
         new_value={"count": count, "errors": errs[:30]})
    db.commit()
    return {"success_count": count, "fail_count": len(errs), "fail_details": errs[:30]}


# ======================================================================
# P1-2: 三员分立 — 角色验证辅助接口（角色分配仍用 users 路由，此处细化权限）
# 三员角色:
#   system_admin (原 super_admin 功能子集: 配置系统/用户/组织结构)
#   security_officer (保密管理员: 配置密码策略、密级、数据权限)
#   auditor (审计员: 只读日志，不能改配置和数据)
# ======================================================================

TRI_ROLES = ["super_admin", "system_admin", "security_officer", "auditor",
             "unit_admin", "person"]

@router.post("/tri-officer/assign", summary="三员分立：为用户分配三员角色（需超管）")
def assign_tri_role(
    user_id: int = Query(...),
    tri_role: str = Query(..., description="system_admin / security_officer / auditor"),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if tri_role not in ("system_admin", "security_officer", "auditor"):
        raise HTTPException(400, "无效的三员角色")
    # 禁止给自己分配三员角色
    if user_id == current_user.id:
        raise HTTPException(400, "不能为自己分配三员角色")
    u = db.query(User).get(user_id)
    if not u:
        raise HTTPException(404, "用户不存在")

    # 一人只允许一个三员角色，用 role 字段直接存放（person 级账号不允许兼任三员）
    u.role = tri_role
    _log(db, current_user, "assign_tri_role",
         f"为用户{u.username}分配三员角色: {tri_role}",
         target_type="user", target_id=user_id,
         old_value={"role": u.role}, new_value={"role": tri_role})
    db.commit()
    return {"message": f"已分配 {tri_role} 角色"}


@router.get("/tri-officer/whoami", summary="查看当前用户的三员角色权限边界")
def tri_whoami(
    current_user: User = Depends(get_current_user),
):
    role_map = {
        "super_admin": {
            "role": "超级管理员", "desc": "拥有所有权限，但仍受三员约束（不能删除自己的审计记录）",
            "perms": ["全部"],
        },
        "system_admin": {
            "role": "系统管理员", "desc": "管理用户、组织架构、系统配置",
            "perms": ["用户和组织结构CRUD", "基础参数配置", "不能看审计日志"],
        },
        "security_officer": {
            "role": "安全保密管理员", "desc": "配置密码策略、密级、数据权限",
            "perms": ["密码策略配置", "密级设置", "数据权限", "不能改组织结构"],
        },
        "auditor": {
            "role": "安全审计员", "desc": "只读审计日志与登录日志，不能修改任何业务数据",
            "perms": ["查看操作日志", "查看登录日志", "日志统计与导出"],
        },
        "unit_admin": {
            "role": "单位管理员", "desc": "管理本单位人员档案与业务流程",
            "perms": ["本单位人员CRUD", "本单位流程审批配置"],
        },
        "person": {
            "role": "普通用户", "desc": "个人档案查看、发起流程、填写表格",
            "perms": ["个人信息", "审批发起", "智能表格填写"],
        },
    }
    return role_map.get(current_user.role, {"role": current_user.role, "desc": "未知"})
