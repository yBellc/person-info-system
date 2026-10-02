"""FastAPI 应用入口"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app import settings
from app.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import User, Role
from app.models.workflow import WorkflowTemplate
from app.models.security import LeaveBalance
from app.routers import auth, units, persons, custom_fields, statistics, reports, resume_import
from app.routers.resume_smart import router as resume_smart_router
from app.routers.organization import router as dept_router, rank_router, position_router, person_position_router
from app.routers.permissions import router as permission_router
from app.routers.workspace import router as workspace_router
from app.routers.workflow import router as workflow_router
from app.routers.expense import router as expense_router
from app.routers.smart_form import router as smart_form_router
from app.routers.system import router as system_router
from app.routers.hr_mgmt import router as hr_mgmt_router
from app.routers.hr_exit_review import router as hr_exit_review_router
from app.routers.analytics_ops import router as analytics_ops_router
from app.routers.ai_router import router as ai_router


def init_default_data(db: SessionLocal):
    """初始化系统默认数据（角色、职级、岗位等）"""
    default_roles = [
        {"name": "系统管理员", "code": "super_admin", "description": "系统最高权限"},
        {"name": "单位管理员", "code": "unit_admin", "description": "管理本单位人员信息"},
        {"name": "部门管理员", "code": "dept_admin", "description": "管理本部门人员信息"},
        {"name": "普通用户", "code": "person", "description": "只能查看和修改自己的信息"},
        {"name": "人事人员", "code": "hr", "description": "人事审批权限"},
        {"name": "财务人员", "code": "finance", "description": "财务审批权限"},
        {"name": "部门领导", "code": "dept_leader", "description": "部门审批权限"},
        # ---- 三员分立角色（涉密单位强制要求）----
        {"name": "系统管理员(三员)", "code": "system_admin", "description": "三员分立：负责系统配置、用户账号管理、备份恢复，不能查看审计日志"},
        {"name": "安全保密管理员", "code": "security_officer", "description": "三员分立：负责密码策略、密级管理、权限配置、数据安全，不能修改业务数据"},
        {"name": "安全审计员", "code": "auditor", "description": "三员分立：只读审计日志与登录日志，独立审计监督，不能修改任何业务数据和系统配置"},
    ]
    for role_data in default_roles:
        existing = db.query(Role).filter(Role.code == role_data["code"]).first()
        if not existing:
            role = Role(
                name=role_data["name"],
                code=role_data["code"],
                description=role_data["description"],
                is_system=True,
                is_active=True,
            )
            db.add(role)
    db.commit()


def run_migrations(conn):
    """轻量级迁移：为已有表补充新字段"""
    migrations = [
        # User 安全字段
        ("users", "first_login", "BOOLEAN DEFAULT 1 NOT NULL"),
        ("users", "failed_login_count", "INTEGER DEFAULT 0 NOT NULL"),
        ("users", "locked_until", "DATETIME"),
        ("users", "password_changed_at", "DATETIME"),
        ("users", "last_login_at", "DATETIME"),
        ("users", "last_password_hashes", "JSON"),
        # User 软删除
        ("users", "is_deleted", "BOOLEAN DEFAULT 0 NOT NULL"),
        ("users", "deleted_at", "DATETIME"),
        ("users", "deleted_by", "INTEGER"),
        # Person 软删除
        ("persons", "is_deleted", "BOOLEAN DEFAULT 0 NOT NULL"),
        ("persons", "deleted_at", "DATETIME"),
        ("persons", "deleted_by", "INTEGER"),
        ("persons", "created_by", "INTEGER"),
        # Department 软删除
        ("departments", "is_deleted", "BOOLEAN DEFAULT 0 NOT NULL"),
        ("departments", "deleted_at", "DATETIME"),
        # OperationLog 审计加强
        ("operation_logs", "ip_address", "VARCHAR(50)"),
        ("operation_logs", "old_value", "JSON"),
        ("operation_logs", "new_value", "JSON"),
        ("operation_logs", "extra", "JSON"),
        # WorkflowInstance 补充
        ("workflow_instances", "current_handler_id", "INTEGER"),
        ("workflow_instances", "current_node_key", "VARCHAR(50)"),
        ("workflow_instances", "current_node_name", "VARCHAR(100)"),
        ("workflow_instances", "submitted_at", "DATETIME"),
        ("workflow_instances", "finished_at", "DATETIME"),
        # 涉密分级管控
        ("users", "clearance_level", "INTEGER DEFAULT 0 NOT NULL"),
        ("persons", "security_level", "INTEGER DEFAULT 1 NOT NULL"),
        ("custom_field_definitions", "security_level", "INTEGER DEFAULT 1 NOT NULL"),
    ]
    for table, column, col_type in migrations:
        try:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            print(f"[迁移] {table}.{column} 已添加")
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动：建表 + 迁移 + 初始化数据"""
    Base.metadata.create_all(bind=engine)

    # 轻量级迁移
    with engine.connect() as conn:
        run_migrations(conn)
        conn.commit()

    db = SessionLocal()
    try:
        # 初始化超管账号
        if not db.query(User).filter(User.role == "super_admin").first():
            admin = User(
                username=settings.SUPER_ADMIN_USERNAME,
                password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                role="super_admin",
            )
            db.add(admin)
            db.commit()
            print(f"[初始化] 超级管理员: {settings.SUPER_ADMIN_USERNAME} / {settings.SUPER_ADMIN_PASSWORD}")

        init_default_data(db)
        print("[初始化] 系统角色完成")

        # 初始化默认流程模板（动态审批人）
        if not db.query(WorkflowTemplate).first():
            default_templates = [
                {
                    "name": "请假申请",
                    "code": "leave",
                    "category": "leave",
                    "description": "年假/事假/病假/调休/婚假/产假等请假审批（动态审批人）",
                    "form_schema": [
                        {"key": "leave_type", "label": "请假类型", "type": "select", "options": ["年假", "事假", "病假", "调休", "婚假", "产假"], "required": True},
                        {"key": "start_date", "label": "开始日期", "type": "date", "required": True},
                        {"key": "end_date", "label": "结束日期", "type": "date", "required": True},
                        {"key": "days", "label": "请假天数", "type": "number", "required": True},
                        {"key": "reason", "label": "请假事由", "type": "textarea", "required": True},
                    ],
                    "flow_nodes": [
                        {"key": "dept_manager", "name": "部门负责人审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "dept_manager"},
                        {"key": "hr", "name": "人事审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "role:hr"},
                    ],
                },
                {
                    "name": "费用报销",
                    "code": "expense",
                    "category": "expense",
                    "description": "差旅费/招待费/办公采购等费用报销（动态审批人）",
                    "form_schema": [
                        {"key": "expense_type", "label": "费用类型", "type": "select", "options": ["差旅费", "招待费", "办公采购", "培训费", "其他"], "required": True},
                        {"key": "amount", "label": "报销金额", "type": "number", "required": True},
                        {"key": "expense_date", "label": "费用发生日期", "type": "date", "required": True},
                        {"key": "description", "label": "费用说明", "type": "textarea", "required": True},
                    ],
                    "flow_nodes": [
                        {"key": "dept_manager", "name": "部门负责人审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "dept_manager"},
                        {"key": "finance", "name": "财务审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "role:finance"},
                    ],
                },
                {
                    "name": "用章申请",
                    "code": "seal",
                    "category": "seal",
                    "description": "公章/合同章/财务章等用章申请（动态审批人）",
                    "form_schema": [
                        {"key": "seal_type", "label": "用章类型", "type": "select", "options": ["公章", "合同章", "财务章", "法人章"], "required": True},
                        {"key": "purpose", "label": "用章事由", "type": "textarea", "required": True},
                        {"key": "document_name", "label": "文件名称", "type": "text", "required": True},
                    ],
                    "flow_nodes": [
                        {"key": "dept_manager", "name": "部门负责人审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "dept_manager"},
                        {"key": "office", "name": "办公室主任审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "unit_admin"},
                    ],
                },
                {
                    "name": "出差申请",
                    "code": "travel",
                    "category": "travel",
                    "description": "国内/国外出差审批（动态审批人）",
                    "form_schema": [
                        {"key": "destination", "label": "出差目的地", "type": "text", "required": True},
                        {"key": "start_date", "label": "出发日期", "type": "date", "required": True},
                        {"key": "end_date", "label": "返回日期", "type": "date", "required": True},
                        {"key": "purpose", "label": "出差事由", "type": "textarea", "required": True},
                        {"key": "budget", "label": "预计费用", "type": "number", "required": False},
                    ],
                    "flow_nodes": [
                        {"key": "dept_manager", "name": "部门负责人审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "dept_manager"},
                        {"key": "leader", "name": "分管领导审批", "type": "approval",
                         "handler_type": "dynamic", "handler_rule": "super_admin"},
                    ],
                },
            ]
            for tpl_data in default_templates:
                tpl = WorkflowTemplate(**tpl_data, is_active=True)
                db.add(tpl)
            db.commit()
            print(f"[初始化] {len(default_templates)} 个流程模板已创建（动态审批人模式）")

        # 为所有已存在用户初始化本年度假期余额
        from app.models.security import LeaveBalance
        current_year = datetime.utcnow().year
        existing_users = db.query(User).filter(User.is_active == True, User.is_deleted == False).all()
        for u in existing_users:
            for leave_type, total in [("annual", 15), ("marriage", 3), ("maternity", 158), ("compassionate", 3)]:
                existing_balance = db.query(LeaveBalance).filter(
                    LeaveBalance.user_id == u.id,
                    LeaveBalance.year == current_year,
                    LeaveBalance.leave_type == leave_type,
                ).first()
                if not existing_balance:
                    balance = LeaveBalance(
                        user_id=u.id, year=current_year, leave_type=leave_type,
                        total_days=total, used_days=0, remaining_days=total,
                    )
                    db.add(balance)
        db.commit()
        print(f"[初始化] 假期余额已为 {len(existing_users)} 个用户初始化")

        # 修复测试账号：跳过首次改密
        test_usernames = ["leader", "admin_01", "bgs_leader", "hr_01", "cw_01", "office_01", "hr_02", "cw_02"]
        for uname in test_usernames:
            u = db.query(User).filter(User.username == uname).first()
            if u and u.first_login:
                u.first_login = False
                print(f"[修复] {uname} 已跳过首次改密")
        db.commit()

    finally:
        db.close()
    yield


# 生产环境安全检查
_is_production = not settings.DEBUG
if _is_production:
    if settings.SECRET_KEY == "dev-secret-key-change-in-production-please-use-strong-random-key":
        print("[安全警告] 检测到默认 SECRET_KEY！请通过环境变量 SECRET_KEY 设置强随机密钥")
    if settings.SUPER_ADMIN_PASSWORD == "admin123":
        print("[安全警告] 超管默认密码仍为 admin123，请部署后立即修改")

# 生产环境关闭 API 文档
_docs_url = None if _is_production else "/docs"
_redoc_url = None if _is_production else "/redoc"
_openapi_url = None if _is_production else "/openapi.json"

app = FastAPI(
    title=settings.APP_NAME,
    description="单位人员基本信息管理系统",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# 确保附件存储目录存在
ATTACHMENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "attachments")
os.makedirs(ATTACHMENT_DIR, exist_ok=True)

# CORS 配置：生产环境仅允许已配置的来源
_cors_env = os.environ.get("CORS_ORIGINS", "")
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173",
                     "http://localhost:8000", "http://127.0.0.1:8000",
                     "http://localhost:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# 注册路由
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(units.router, prefix=settings.API_V1_PREFIX)
app.include_router(persons.router, prefix=settings.API_V1_PREFIX)
app.include_router(custom_fields.router, prefix=settings.API_V1_PREFIX)
app.include_router(statistics.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(resume_import.router, prefix=settings.API_V1_PREFIX)
app.include_router(dept_router, prefix=settings.API_V1_PREFIX)
app.include_router(rank_router, prefix=settings.API_V1_PREFIX)
app.include_router(position_router, prefix=settings.API_V1_PREFIX)
app.include_router(person_position_router, prefix=settings.API_V1_PREFIX)
app.include_router(permission_router, prefix=settings.API_V1_PREFIX)
app.include_router(workspace_router, prefix=settings.API_V1_PREFIX)
app.include_router(workflow_router, prefix=settings.API_V1_PREFIX)
app.include_router(resume_smart_router, prefix=settings.API_V1_PREFIX)
app.include_router(expense_router, prefix=settings.API_V1_PREFIX)
app.include_router(smart_form_router, prefix=settings.API_V1_PREFIX)
app.include_router(system_router, prefix=settings.API_V1_PREFIX)
app.include_router(hr_mgmt_router, prefix=settings.API_V1_PREFIX)
app.include_router(hr_exit_review_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_ops_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["默认"])
def health():
    return {"status": "ok"}


# 前端静态文件托管
FRONTEND_DIST = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "frontend", "dist"
))


@app.get("/", tags=["默认"])
async def serve_index():
    """根路径返回前端首页"""
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


@app.get("/assets/{path:path}", include_in_schema=False)
async def serve_assets(path: str):
    """托管前端静态资源"""
    return FileResponse(os.path.join(FRONTEND_DIST, "assets", path))


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """SPA 回退：所有非API路由返回 index.html，确保 Vue Router history 模式正常"""
    # 排除 API 和 FastAPI 内置路径
    skip_prefixes = ("api/", "docs", "redoc", "openapi.json", "health")
    for prefix in skip_prefixes:
        if full_path.startswith(prefix) or full_path == prefix.rstrip("/"):
            return {"error": "not found"}
    file_path = os.path.join(FRONTEND_DIST, full_path)
    if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
