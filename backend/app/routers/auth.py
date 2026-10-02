"""认证路由：登录、注册、改密（含安全加固）"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, validate_password_strength, is_password_in_history
from app.core.permissions import get_current_user, require_super_admin
from app.core.idcard import validate_id_card, parse_id_card
from app.models import User, UnitRoster, Person, OperationLog, Unit, AdminApplication
from app.models.security import LoginLog
from app.schemas.auth import (
    Token, LoginRequest, RegisterRequest, ChangePasswordRequest, UserOut,
    CreateUnitAdminRequest, AdminApplicationCreate, AdminApplicationReview, AdminApplicationOut,
    HrCreateAccountRequest, HrBatchCreateRequest, HrAccountOut, HrBatchResult,
    FirstLoginChangePasswordRequest,
)
from app import settings

router = APIRouter(prefix="/auth", tags=["认证"])

MAX_LOGIN_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 30
PASSWORD_EXPIRE_DAYS = 90


def log_operation(db: Session, user_id: int, username: str, action: str,
                  detail: str = None, target_type: str = None, target_id: int = None,
                  ip_address: str = None, old_value=None, new_value=None):
    """记录操作日志（含IP和变更前后值）"""
    log = OperationLog(
        operator_id=user_id, operator_name=username, action=action,
        detail=detail, target_type=target_type, target_id=target_id,
        ip_address=ip_address, old_value=old_value, new_value=new_value,
    )
    db.add(log)


def _get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _log_login_attempt(db: Session, username: str, user_id: int, ip: str, ua: str, success: bool, fail_reason: str = None):
    """记录登录日志"""
    log = LoginLog(
        user_id=user_id, username=username, ip_address=ip, user_agent=ua[:500] if ua else None,
        success=success, fail_reason=fail_reason,
    )
    db.add(log)


@router.post("/login", response_model=Token, summary="登录")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = _get_client_ip(request)
    ua = request.headers.get("User-Agent", "")

    user = db.query(User).filter(User.username == req.username, User.is_deleted == False).first()

    # 用户不存在
    if not user:
        _log_login_attempt(db, req.username, None, ip, ua, False, "用户不存在")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    # 账号停用
    if not user.is_active:
        _log_login_attempt(db, req.username, user.id, ip, ua, False, "账号已停用")
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被停用，请联系管理员")

    # 检查锁定
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        _log_login_attempt(db, req.username, user.id, ip, ua, False, f"账号锁定中(剩余{remaining}分钟)")
        db.commit()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=f"账号已锁定，请{remaining}分钟后重试")

    # 验证密码
    if not verify_password(req.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
            _log_login_attempt(db, req.username, user.id, ip, ua, False, f"连续失败{MAX_LOGIN_ATTEMPTS}次，锁定30分钟")
        else:
            remaining_attempts = MAX_LOGIN_ATTEMPTS - user.failed_login_count
            _log_login_attempt(db, req.username, user.id, ip, ua, False, f"密码错误(剩余{remaining_attempts}次)")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"用户名或密码错误，剩余尝试次数: {MAX_LOGIN_ATTEMPTS - user.failed_login_count}")

    # 登录成功：重置失败计数
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()

    # 检查密码是否过期（90天）
    password_expired = False
    if user.password_changed_at:
        if datetime.utcnow() - user.password_changed_at > timedelta(days=PASSWORD_EXPIRE_DAYS):
            password_expired = True
            user.first_login = True  # 强制改密

    token = create_access_token({"sub": str(user.id), "role": user.role})

    _log_login_attempt(db, req.username, user.id, ip, ua, True)
    log_operation(db, user.id, user.username, "login", f"用户 {user.username} 登录", ip_address=ip)

    db.commit()

    return Token(
        access_token=token,
        role=user.role,
        username=user.username,
        user_id=user.id,
        first_login=user.first_login,
    )


@router.post("/register", response_model=Token, summary="用户自助注册（凭名单匹配）")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 1. 用户名查重
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 2. 匹配单位名单
    roster = db.query(UnitRoster).filter(
        UnitRoster.name == req.name,
        UnitRoster.id_card == req.id_card,
        UnitRoster.is_registered == False,
    ).first()

    if not roster:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="姓名或身份证号不在单位名单内，或已被注册。请联系单位管理员。",
        )

    # 3. 创建账号
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role="person",
        unit_id=roster.unit_id,
    )
    db.add(user)
    db.flush()  # 拿到 user.id

    # 4. 关联/创建人员记录
    #    若人员表已存在同身份证的人（如管理员提前导入或简历导入创建过），直接关联，避免重复
    existing_person = db.query(Person).filter(Person.id_card == req.id_card).first()
    if existing_person:
        user.person_id = existing_person.id
    else:
        # 否则创建新人员记录（姓名+身份证，并联动回填出生日期/性别）
        birth_date, gender = parse_id_card(req.id_card)
        person = Person(
            name=req.name,
            id_card=req.id_card,
            unit_id=roster.unit_id,
            birth_date=birth_date,
            gender=gender,
            created_by=user.id,
        )
        db.add(person)
        db.flush()
        user.person_id = person.id

    # 5. 标记名单已注册
    roster.is_registered = True
    roster.registered_user_id = user.id

    log_operation(db, user.id, user.username, "register", f"注册成功，绑定单位ID={roster.unit_id}")
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token, role=user.role, username=user.username, user_id=user.id)


@router.get("/me", response_model=UserOut, summary="获取当前用户信息")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Unit
    unit_name = None
    if current_user.unit_id:
        unit = db.query(Unit).get(current_user.unit_id)
        unit_name = unit.name if unit else None
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        unit_id=current_user.unit_id,
        unit_name=unit_name,
        person_id=current_user.person_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/change-password", summary="修改密码")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    # 密码强度校验
    ok, msg = validate_password_strength(req.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # 不能与最近5次密码相同
    history = current_user.last_password_hashes or []
    if current_user.password_hash not in history:
        history.append(current_user.password_hash)
    if len(history) > 5:
        history = history[-5:]
    if is_password_in_history(req.new_password, history):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与最近5次使用过的密码相同")

    old_hash = current_user.password_hash
    current_user.password_hash = hash_password(req.new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.last_password_hashes = history
    current_user.first_login = False

    ip = _get_client_ip(request)
    log_operation(db, current_user.id, current_user.username, "change_password",
                  "修改密码", ip_address=ip, old_value={"hash": old_hash[:20]+"..."},
                  new_value={"hash": current_user.password_hash[:20]+"..."})
    db.commit()
    return {"msg": "密码修改成功"}


# ===== 单位管理员账号管理（仅超管）=====

@router.post("/unit-admins", response_model=UserOut, summary="创建单位管理员账号（仅超管）")
def create_unit_admin(
    req: CreateUnitAdminRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """超级管理员为单位创建管理员账号。一个单位可有多个管理员。"""
    # 用户名查重
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 校验单位存在且启用
    unit = db.query(Unit).filter(Unit.id == req.unit_id, Unit.is_active == True).first()
    if not unit:
        raise HTTPException(status_code=400, detail="单位不存在或已停用")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role="unit_admin",
        unit_id=req.unit_id,
    )
    db.add(user)
    db.flush()

    log_operation(db, current_user.id, current_user.username, "create_unit_admin",
                  f"为单位'{unit.name}'创建管理员 {req.username}", target_type="unit", target_id=req.unit_id)
    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id, username=user.username, role=user.role,
        unit_id=user.unit_id, unit_name=unit.name,
        person_id=user.person_id, is_active=user.is_active, created_at=user.created_at,
    )


@router.get("/unit-admins", summary="单位管理员账号列表（仅超管）")
def list_unit_admins(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """列出所有单位管理员账号"""
    users = db.query(User).filter(User.role == "unit_admin").order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        unit_name = None
        if u.unit_id:
            unit = db.query(Unit).get(u.unit_id)
            unit_name = unit.name if unit else None
        result.append({
            "id": u.id, "username": u.username, "role": u.role,
            "unit_id": u.unit_id, "unit_name": unit_name,
            "is_active": u.is_active, "created_at": u.created_at.isoformat(),
        })
    return result


@router.put("/unit-admins/{user_id}/toggle", summary="启用/停用账号（仅超管）")
def toggle_unit_admin(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """切换账号启用状态"""
    user = db.query(User).get(user_id)
    if not user or user.role != "unit_admin":
        raise HTTPException(status_code=404, detail="单位管理员账号不存在")
    user.is_active = not user.is_active
    status_text = "启用" if user.is_active else "停用"
    log_operation(db, current_user.id, current_user.username, "toggle_admin",
                  f"{status_text}管理员账号 {user.username}", target_type="user", target_id=user_id)
    db.commit()
    return {"msg": f"已{status_text}", "is_active": user.is_active}


@router.put("/unit-admins/{user_id}/reset-password", summary="重置管理员密码（仅超管）")
def reset_admin_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """重置单位管理员密码"""
    user = db.query(User).get(user_id)
    if not user or user.role != "unit_admin":
        raise HTTPException(status_code=404, detail="单位管理员账号不存在")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    user.password_hash = hash_password(new_password)
    log_operation(db, current_user.id, current_user.username, "reset_admin_pwd",
                  f"重置管理员 {user.username} 密码", target_type="user", target_id=user_id)
    db.commit()
    return {"msg": "密码已重置"}


# ===== 管理员申请与审批（账号升级）=====

@router.post("/applications", response_model=AdminApplicationOut, summary="提交管理员申请（个人账号）")
def create_application(
    req: AdminApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """普通用户申请成为本单位管理员，等待超管审批"""
    if current_user.role != "person":
        raise HTTPException(status_code=400, detail="当前账号角色无需申请（已是管理员或超管）")
    if not current_user.unit_id:
        raise HTTPException(status_code=400, detail="您未绑定单位，无法申请")

    # 幂等：同一用户已有 pending 申请则拒绝重复提交
    existing = db.query(AdminApplication).filter(
        AdminApplication.user_id == current_user.id,
        AdminApplication.status == "pending",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已有一个待审批的申请，请耐心等待")

    unit = db.query(Unit).get(current_user.unit_id)
    if not unit:
        raise HTTPException(status_code=400, detail="所属单位不存在")

    application = AdminApplication(
        user_id=current_user.id,
        username=current_user.username,
        target_unit_id=current_user.unit_id,
        target_unit_name=unit.name,
        status="pending",
        reason=req.reason,
    )
    db.add(application)
    log_operation(db, current_user.id, current_user.username, "apply_admin",
                  f"申请成为 {unit.name} 管理员", target_type="application", target_id=None)
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications/mine", response_model=list[AdminApplicationOut], summary="查看我的申请")
def my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(AdminApplication).filter(
        AdminApplication.user_id == current_user.id
    ).order_by(AdminApplication.created_at.desc()).all()


@router.get("/applications", response_model=list[AdminApplicationOut], summary="待审批申请列表（超管）")
def list_applications(
    status_filter: str = "pending",
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AdminApplication)
    if status_filter and status_filter != "all":
        q = q.filter(AdminApplication.status == status_filter)
    return q.order_by(AdminApplication.created_at.desc()).all()


@router.put("/applications/{application_id}/approve", summary="批准申请（超管）")
def approve_application(
    application_id: int,
    req: AdminApplicationReview,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """批准申请：把申请人升级为 unit_admin，保留 person_id（双重身份）"""
    from datetime import datetime
    application = db.query(AdminApplication).get(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"该申请状态为 {application.status}，无法审批")

    user = db.query(User).get(application.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="申请人账号不存在")
    if user.role != "person":
        raise HTTPException(status_code=400, detail=f"申请人当前角色为 {user.role}，无需升级")

    # 升级为单位管理员，保留 person_id（双重身份）
    user.role = "unit_admin"
    user.unit_id = application.target_unit_id

    application.status = "approved"
    application.reviewer_id = current_user.id
    application.review_note = req.review_note
    application.reviewed_at = datetime.utcnow()

    log_operation(db, current_user.id, current_user.username, "approve_admin",
                  f"批准 {user.username} 成为 {application.target_unit_name} 管理员",
                  target_type="user", target_id=user.id)
    db.commit()
    return {"msg": "已批准，该用户已升级为单位管理员"}


@router.put("/applications/{application_id}/reject", summary="驳回申请（超管）")
def reject_application(
    application_id: int,
    req: AdminApplicationReview,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """驳回申请"""
    from datetime import datetime
    application = db.query(AdminApplication).get(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"该申请状态为 {application.status}，无法审批")

    application.status = "rejected"
    application.reviewer_id = current_user.id
    application.review_note = req.review_note
    application.reviewed_at = datetime.utcnow()

    log_operation(db, current_user.id, current_user.username, "reject_admin",
                  f"驳回 {application.username} 的管理员申请",
                  target_type="user", target_id=application.user_id)
    db.commit()
    return {"msg": "已驳回"}


# ===== 首次登录改密 =====

@router.post("/first-login-change-password", summary="首次登录修改密码")
def first_login_change_password(
    req: FirstLoginChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """首次登录后强制修改密码（含密码强度校验）"""
    if not current_user.first_login:
        return {"msg": "无需修改", "first_login": False}

    # 密码强度校验
    ok, msg = validate_password_strength(req.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # 不能与当前密码相同
    if verify_password(req.new_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与初始密码相同")

    old_hash = current_user.password_hash
    current_user.password_hash = hash_password(req.new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.first_login = False
    current_user.last_password_hashes = [old_hash]

    ip = _get_client_ip(request)
    log_operation(db, current_user.id, current_user.username, "first_login_change_pwd",
                  "首次登录改密", ip_address=ip)
    db.commit()
    return {"msg": "密码修改成功", "first_login": False}


# ===== 人事批量注册（单位管理员/超管可用）=====

def _generate_username(db: Session, name: str, phone: str = None) -> str:
    """生成用户名：优先用手机号，否则用拼音首字母+序号"""
    if phone:
        # 手机号直接作用户名
        if not db.query(User).filter(User.username == phone).first():
            return phone
    # 用姓名拼音首字母 + 序号（简化版：直接用姓名+序号）
    import re
    base = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name)
    # 如果是中文，尝试用简拼；这里简化为姓名直接作用户名的一部分
    for i in range(1, 1000):
        candidate = f"{base}{i:03d}" if i > 1 else base
        if not db.query(User).filter(User.username == candidate).first():
            return candidate
    return base + str(int(datetime.utcnow().timestamp()))


def _create_account_for_employee(
    db: Session, name: str, id_card: str, phone: str, unit_id: int,
    department: str = None, position: str = None, password: str = None,
    operator: User = None,
) -> User:
    """核心：为员工创建账号（内部函数）"""
    # 1. 验证身份证
    if not validate_id_card(id_card):
        raise ValueError("身份证号格式或校验位错误")

    # 2. 生成用户名
    username = _generate_username(db, name, phone)

    # 3. 生成初始密码
    if not password:
        password = id_card[-6:]  # 身份证后6位

    # 4. 解析身份证获取出生日期和性别
    birth_date, gender = parse_id_card(id_card)

    # 5. 创建或关联人员档案
    person = db.query(Person).filter(Person.id_card == id_card).first()
    if not person:
        person = Person(
            name=name, id_card=id_card, gender=gender, birth_date=birth_date,
            phone=phone, unit_id=unit_id, department=department, position=position,
            created_by=operator.id if operator else None,
        )
        db.add(person)
        db.flush()
    else:
        # 更新缺失字段
        if phone and not person.phone:
            person.phone = phone
        if department and not person.department:
            person.department = department
        if position and not person.position:
            person.position = position

    # 6. 创建用户账号
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="person",
        unit_id=unit_id,
        person_id=person.id,
        first_login=True,  # 标记需要首次登录改密
    )
    db.add(user)
    db.flush()

    # 7. 标记名单已注册（如果名单存在）
    roster = db.query(UnitRoster).filter(
        UnitRoster.name == name,
        UnitRoster.id_card == id_card,
    ).first()
    if roster and not roster.is_registered:
        roster.is_registered = True
        roster.registered_user_id = user.id

    return user


@router.get("/hr/roster", summary="查看单位名单（含注册状态）")
def hr_view_roster(
    unit_id: int = None,
    keyword: str = None,
    registered: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人事查看本单位名单，支持按注册状态筛选"""
    query = db.query(UnitRoster)

    # 权限过滤
    if current_user.role == "super_admin":
        if unit_id:
            query = query.filter(UnitRoster.unit_id == unit_id)
    elif current_user.role == "unit_admin":
        accessible_ids = _get_accessible_unit_ids(db, current_user)
        if unit_id and unit_id in accessible_ids:
            query = query.filter(UnitRoster.unit_id == unit_id)
        else:
            query = query.filter(UnitRoster.unit_id.in_(accessible_ids))
    else:
        raise HTTPException(status_code=403, detail="无权查看名单")

    if keyword:
        query = query.filter(UnitRoster.name.contains(keyword))
    if registered is not None:
        query = query.filter(UnitRoster.is_registered == registered)

    rosters = query.order_by(UnitRoster.created_at.desc()).limit(500).all()
    result = []
    for r in rosters:
        unit = db.query(Unit).get(r.unit_id)
        user_info = None
        if r.registered_user_id:
            u = db.query(User).get(r.registered_user_id)
            if u:
                person = db.query(Person).filter(Person.id == u.person_id).first() if u.person_id else None
                user_info = {
                    "user_id": u.id, "username": u.username,
                    "is_active": u.is_active, "first_login": u.first_login,
                    "phone": person.phone if person else None,
                    "department": person.department if person else None,
                }
        result.append({
            "id": r.id, "name": r.name,
            "id_card": r.id_card[:6] + "********" + r.id_card[-4:],
            "id_card_full": r.id_card,
            "unit_id": r.unit_id, "unit_name": unit.name if unit else None,
            "is_registered": r.is_registered,
            "user_info": user_info,
        })
    return result


@router.post("/hr/create-account", response_model=HrAccountOut, summary="人事为单个员工创建账号")
def hr_create_account(
    req: HrCreateAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人事为员工创建账号，员工首次登录时需修改密码"""
    # 权限检查
    _check_hr_permission(db, current_user, req.unit_id)

    # 检查是否已有同身份证的账号
    existing = db.query(User).join(Person, User.person_id == Person.id).filter(
        Person.id_card == req.id_card
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"该员工已有账号: {existing.username}")

    try:
        user = _create_account_for_employee(
            db, req.name, req.id_card, req.phone, req.unit_id,
            req.department, req.position, req.password, current_user,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log_operation(db, current_user.id, current_user.username, "hr_create_account",
                  f"为员工 {req.name} 创建账号 {user.username}",
                  target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)

    unit = db.query(Unit).get(req.unit_id)
    person = db.query(Person).get(user.person_id) if user.person_id else None
    return HrAccountOut(
        id=user.id, username=user.username,
        name=person.name if person else req.name,
        id_card=req.id_card,
        phone=person.phone if person else req.phone,
        unit_id=user.unit_id, unit_name=unit.name if unit else None,
        department=person.department if person else req.department,
        position=person.position if person else req.position,
        is_active=user.is_active, first_login=user.first_login,
        created_at=user.created_at,
    )


@router.post("/hr/batch-create", response_model=HrBatchResult, summary="人事批量创建账号")
def hr_batch_create(
    req: HrBatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从名单中批量选择未注册员工，一次性创建账号"""
    _check_hr_permission(db, current_user, req.unit_id)

    rosters = db.query(UnitRoster).filter(
        UnitRoster.id.in_(req.roster_ids),
        UnitRoster.unit_id == req.unit_id,
        UnitRoster.is_registered == False,
    ).all()

    success_list = []
    failed_list = []

    for roster in rosters:
        try:
            # 检查是否已有账号
            existing = db.query(User).join(Person, User.person_id == Person.id).filter(
                Person.id_card == roster.id_card
            ).first()
            if existing:
                failed_list.append({
                    "name": roster.name, "id_card": roster.id_card[-4:],
                    "reason": "已有账号",
                })
                continue

            # 生成密码
            if req.password_mode == "idcard":
                pwd = roster.id_card[-6:]
            elif req.password_mode == "uniform" and req.uniform_password:
                pwd = req.uniform_password
            else:
                pwd = roster.id_card[-6:]

            user = _create_account_for_employee(
                db, roster.name, roster.id_card, None, req.unit_id,
                password=pwd, operator=current_user,
            )
            db.flush()

            unit = db.query(Unit).get(req.unit_id)
            person = db.query(Person).get(user.person_id) if user.person_id else None
            success_list.append(HrAccountOut(
                id=user.id, username=user.username,
                name=person.name if person else roster.name,
                id_card=roster.id_card,
                phone=None,
                unit_id=user.unit_id, unit_name=unit.name if unit else None,
                department=None, position=None,
                is_active=user.is_active, first_login=user.first_login,
                created_at=user.created_at,
            ))
        except Exception as e:
            failed_list.append({
                "name": roster.name, "id_card": roster.id_card[-4:],
                "reason": str(e),
            })

    log_operation(db, current_user.id, current_user.username, "hr_batch_create",
                  f"批量创建账号: 成功{len(success_list)}个, 失败{len(failed_list)}个",
                  target_type="unit", target_id=req.unit_id)
    db.commit()

    return HrBatchResult(success=success_list, failed=failed_list)


@router.get("/hr/accounts", summary="人事查看已创建的账号列表")
def hr_list_accounts(
    unit_id: int = None,
    keyword: str = None,
    is_active: bool = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人事查看本单位的账号列表"""
    query = db.query(User).filter(User.role == "person")

    if current_user.role == "super_admin":
        if unit_id:
            query = query.filter(User.unit_id == unit_id)
    elif current_user.role == "unit_admin":
        accessible_ids = _get_accessible_unit_ids(db, current_user)
        if unit_id and unit_id in accessible_ids:
            query = query.filter(User.unit_id == unit_id)
        else:
            query = query.filter(User.unit_id.in_(accessible_ids))
    else:
        raise HTTPException(status_code=403, detail="无权查看")

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if keyword:
        # 按用户名或人员姓名搜索
        query = query.join(Person, User.person_id == Person.id, isouter=True).filter(
            (User.username.contains(keyword)) | (Person.name.contains(keyword))
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for u in users:
        person = db.query(Person).get(u.person_id) if u.person_id else None
        unit = db.query(Unit).get(u.unit_id) if u.unit_id else None
        result.append({
            "id": u.id, "username": u.username,
            "name": person.name if person else "",
            "id_card": (person.id_card[:6] + "********" + person.id_card[-4:]) if person and person.id_card else None,
            "phone": person.phone if person else None,
            "department": person.department if person else None,
            "position": person.position if person else None,
            "unit_id": u.unit_id, "unit_name": unit.name if unit else None,
            "is_active": u.is_active, "first_login": u.first_login,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"items": result, "total": total}


@router.put("/hr/accounts/{user_id}/reset-password", summary="重置员工密码")
def hr_reset_password(
    user_id: int,
    new_password: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人事重置员工密码，重置后需首次登录改密"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    if user.role != "person":
        raise HTTPException(status_code=400, detail="只能重置普通员工账号")

    _check_hr_permission(db, current_user, user.unit_id)

    # 如果未提供密码，用身份证后6位
    if not new_password or len(new_password) < 6:
        person = db.query(Person).get(user.person_id) if user.person_id else None
        if person and person.id_card:
            new_password = person.id_card[-6:]
        else:
            raise HTTPException(status_code=400, detail="请提供新密码（至少6位）")

    user.password_hash = hash_password(new_password)
    user.first_login = True  # 重置后需要重新改密
    log_operation(db, current_user.id, current_user.username, "hr_reset_password",
                  f"重置员工 {user.username} 密码",
                  target_type="user", target_id=user.id)
    db.commit()
    return {"msg": "密码已重置", "new_password": new_password, "first_login": True}


@router.put("/hr/accounts/{user_id}/toggle", summary="启用/停用员工账号")
def hr_toggle_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启用或停用员工账号"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    if user.role != "person":
        raise HTTPException(status_code=400, detail="只能操作普通员工账号")

    _check_hr_permission(db, current_user, user.unit_id)

    user.is_active = not user.is_active
    status_text = "启用" if user.is_active else "停用"
    log_operation(db, current_user.id, current_user.username, "hr_toggle_account",
                  f"{status_text}员工账号 {user.username}",
                  target_type="user", target_id=user.id)
    db.commit()
    return {"msg": f"已{status_text}", "is_active": user.is_active}


@router.post("/hr/roster/import", summary="导入名单（手动添加）")
def hr_import_roster(
    items: list[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人事手动添加名单条目（姓名+身份证+单位）"""
    added = 0
    skipped = 0
    for item in items:
        name = item.get("name", "").strip()
        id_card = item.get("id_card", "").strip()
        unit_id = item.get("unit_id")

        if not name or len(id_card) != 18 or not unit_id:
            skipped += 1
            continue

        _check_hr_permission(db, current_user, unit_id)

        # 检查重复
        existing = db.query(UnitRoster).filter(
            UnitRoster.name == name,
            UnitRoster.id_card == id_card,
        ).first()
        if existing:
            skipped += 1
            continue

        roster = UnitRoster(unit_id=unit_id, name=name, id_card=id_card)
        db.add(roster)
        added += 1

    db.commit()
    return {"added": added, "skipped": skipped, "total": added + skipped}


# ===== 辅助函数 =====

def _get_accessible_unit_ids(db: Session, user: User) -> list:
    """获取用户可管理的单位ID列表"""
    from app.core.permissions import _get_descendant_unit_ids
    if user.role == "super_admin":
        return [u.id for u in db.query(Unit).all()]
    if user.role == "unit_admin" and user.unit_id:
        return list(_get_descendant_unit_ids(db, user.unit_id))
    return []


def _check_hr_permission(db: Session, user: User, unit_id: int):
    """检查人事是否有权操作指定单位"""
    if user.role == "super_admin":
        return
    if user.role == "unit_admin":
        accessible = _get_accessible_unit_ids(db, user)
        if unit_id not in accessible:
            raise HTTPException(status_code=403, detail="无权操作该单位")
        return
    raise HTTPException(status_code=403, detail="需要管理员权限")
