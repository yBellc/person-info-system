"""系统管理路由：审计日志查看、数据库备份
三员分立权限控制：
  - 审计日志（只读）：require_auditor → auditor / super_admin
  - 备份恢复（系统操作）：require_system_admin → system_admin / super_admin
  - 日志清理（高敏感）：require_super_admin → 仅超管
"""
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.core.permissions import require_super_admin, require_auditor, require_system_admin, require_security_officer
from app.models import User, OperationLog
from app.models.security import LoginLog
from app import settings

router = APIRouter(prefix="/system", tags=["系统管理"])

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


# ==================== 审计日志 ====================

@router.get("/operation-logs", summary="操作日志列表（三员：仅审计员与超管可见）")
def list_operation_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    operator_name: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db),
):
    q = db.query(OperationLog)
    if operator_name:
        q = q.filter(OperationLog.operator_name.contains(operator_name))
    if action:
        q = q.filter(OperationLog.action == action)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            q = q.filter(OperationLog.created_at >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(OperationLog.created_at < ed)
        except ValueError:
            pass

    total = q.count()
    logs = q.order_by(desc(OperationLog.created_at)).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": log.id,
                "operator_id": log.operator_id,
                "operator_name": log.operator_name,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "detail": log.detail,
                "ip_address": log.ip_address,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/login-logs", summary="登录日志列表（三员：仅审计员与超管可见）")
def list_login_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    username: Optional[str] = None,
    success: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db),
):
    q = db.query(LoginLog)
    if username:
        q = q.filter(LoginLog.username.contains(username))
    if success is not None:
        q = q.filter(LoginLog.success == success)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            q = q.filter(LoginLog.login_time >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(LoginLog.login_time < ed)
        except ValueError:
            pass

    total = q.count()
    logs = q.order_by(desc(LoginLog.login_time)).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "ip_address": log.ip_address,
                "success": log.success,
                "fail_reason": log.fail_reason,
                "login_time": log.login_time.strftime("%Y-%m-%d %H:%M:%S") if log.login_time else None,
                "logout_time": log.logout_time.strftime("%Y-%m-%d %H:%M:%S") if log.logout_time else None,
            }
            for log in logs
        ],
    }


@router.get("/logs/stats", summary="日志统计概览（三员：仅审计员与超管可见）")
def logs_stats(
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    return {
        "operation_logs_total": db.query(OperationLog).count(),
        "operation_logs_today": db.query(OperationLog).filter(OperationLog.created_at >= today_start).count(),
        "login_logs_total": db.query(LoginLog).count(),
        "login_logs_today": db.query(LoginLog).filter(LoginLog.login_time >= today_start).count(),
        "login_success_today": db.query(LoginLog).filter(
            LoginLog.login_time >= today_start, LoginLog.success == True
        ).count(),
        "login_failed_today": db.query(LoginLog).filter(
            LoginLog.login_time >= today_start, LoginLog.success == False
        ).count(),
        "login_failed_week": db.query(LoginLog).filter(
            LoginLog.login_time >= week_ago, LoginLog.success == False
        ).count(),
    }


# ==================== 数据库备份 ====================

@router.get("/backups", summary="备份文件列表（三员：仅系统管理员与超管）")
def list_backups(
    current_user: User = Depends(require_system_admin),
):
    backups = []
    if os.path.exists(BACKUP_DIR):
        for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
            fpath = os.path.join(BACKUP_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                backups.append({
                    "filename": fname,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
    return {"items": backups, "total": len(backups)}


@router.post("/backups/create", summary="手动创建数据库备份（三员：仅系统管理员与超管）")
def create_backup(
    current_user: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    backup_name = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    try:
        db.close()
        shutil.copy2(db_path, backup_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {str(e)}")

    stat = os.stat(backup_path)
    log = OperationLog(
        operator_id=current_user.id,
        operator_name=current_user.username,
        action="backup_database",
        detail=f"手动备份数据库: {backup_name}",
    )
    db.add(log)
    db.commit()

    return {
        "message": "备份成功",
        "filename": backup_name,
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/backups/{filename}/download", summary="下载备份文件（三员：仅系统管理员与超管）")
def download_backup(
    filename: str,
    current_user: User = Depends(require_system_admin),
):
    safe_name = os.path.basename(filename)
    if not safe_name.startswith("backup_") or not safe_name.endswith(".db"):
        raise HTTPException(status_code=400, detail="无效的备份文件名")
    backup_path = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")
    return FileResponse(backup_path, filename=safe_name)


@router.delete("/backups/{filename}", summary="删除备份文件（三员：仅系统管理员与超管）")
def delete_backup(
    filename: str,
    current_user: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    safe_name = os.path.basename(filename)
    if not safe_name.startswith("backup_") or not safe_name.endswith(".db"):
        raise HTTPException(status_code=400, detail="无效的备份文件名")
    backup_path = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    os.remove(backup_path)
    log = OperationLog(
        operator_id=current_user.id,
        operator_name=current_user.username,
        action="delete_backup",
        detail=f"删除备份: {safe_name}",
    )
    db.add(log)
    db.commit()
    return {"message": "已删除"}


@router.delete("/logs/clean", summary="清理过期日志（保留指定天数）")
def clean_old_logs(
    days: int = Query(180, ge=30, le=3650),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    old_ops = db.query(OperationLog).filter(OperationLog.created_at < cutoff).count()
    old_logins = db.query(LoginLog).filter(LoginLog.login_time < cutoff).count()

    db.query(OperationLog).filter(OperationLog.created_at < cutoff).delete()
    db.query(LoginLog).filter(LoginLog.login_time < cutoff).delete()

    log = OperationLog(
        operator_id=current_user.id,
        operator_name=current_user.username,
        action="clean_logs",
        detail=f"清理{days}天前日志: 操作日志{old_ops}条, 登录日志{old_logins}条",
    )
    db.add(log)
    db.commit()

    return {
        "message": "清理完成",
        "deleted_operation_logs": old_ops,
        "deleted_login_logs": old_logins,
    }


# ==================== 涉密分级管控 ====================

SECURITY_LEVEL_NAMES = {0: "公开", 1: "内部", 2: "秘密", 3: "机密"}


@router.get("/clearance/users", summary="用户涉密等级列表（三员：仅保密管理员与超管）")
def list_user_clearance(
    current_user: User = Depends(require_security_officer),
    db: Session = Depends(get_db),
):
    """获取所有用户的涉密等级配置"""
    users = db.query(User).filter(User.is_deleted == False).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "clearance_level": getattr(u, "clearance_level", 0) or 0,
            "clearance_name": SECURITY_LEVEL_NAMES.get(getattr(u, "clearance_level", 0) or 0, "未知"),
            "is_active": u.is_active,
        })
    return {"items": result, "total": len(result)}


@router.put("/clearance/users/{user_id}", summary="设置用户涉密等级（三员：仅保密管理员与超管）")
def set_user_clearance(
    user_id: int,
    level: int = Query(..., ge=0, le=3, description="涉密等级: 0=公开 1=内部 2=秘密 3=机密"),
    current_user: User = Depends(require_security_officer),
    db: Session = Depends(get_db),
):
    """设置用户的涉密等级（clearance_level）"""
    target = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_level = getattr(target, "clearance_level", 0) or 0
    target.clearance_level = level
    db.add(OperationLog(
        operator_id=current_user.id,
        operator_name=current_user.username,
        action="set_clearance",
        detail=f"设置用户 {target.username} 涉密等级: {SECURITY_LEVEL_NAMES.get(old_level, '?')} → {SECURITY_LEVEL_NAMES.get(level, '?')}",
        target_type="user",
        target_id=user_id,
        old_value={"clearance_level": old_level},
        new_value={"clearance_level": level},
    ))
    db.commit()
    return {
        "message": "涉密等级已更新",
        "user_id": user_id,
        "username": target.username,
        "clearance_level": level,
        "clearance_name": SECURITY_LEVEL_NAMES.get(level, "未知"),
    }


@router.get("/clearance/levels", summary="涉密等级字典")
def get_clearance_levels(
    current_user: User = Depends(require_security_officer),
):
    """返回涉密等级选项列表"""
    return [
        {"level": 0, "name": "公开", "desc": "可查看公开级数据"},
        {"level": 1, "name": "内部", "desc": "可查看公开+内部级数据"},
        {"level": 2, "name": "秘密", "desc": "可查看公开+内部+秘密级数据（敏感字段部分打码）"},
        {"level": 3, "name": "机密", "desc": "可查看所有数据，不脱敏"},
    ]
