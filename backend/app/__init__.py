"""应用配置"""
import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """系统配置 - 通过环境变量覆盖"""

    # 应用
    APP_NAME: str = "人员基本信息系统"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # 数据库 - 开发用 SQLite，部署用 PostgreSQL
    # 部署时设置 DATABASE_URL=postgresql://user:pass@host:5432/dbname
    # SQLite 使用规范绝对路径，Windows 路径反斜杠转为正斜杠避免 URL 解析问题
    _DB_PATH: str = str((Path(__file__).resolve().parent.parent / "person_info.db")).replace("\\", "/")
    DATABASE_URL: str = f"sqlite:///{_DB_PATH}"

    # 认证 - 生产环境必须通过环境变量设置 SECRET_KEY
    SECRET_KEY: str = "dev-secret-key-change-in-production-please-use-strong-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # 文件上传
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent / "uploads")

    # 初始超管（首次启动自动创建）
    SUPER_ADMIN_USERNAME: str = "admin"
    SUPER_ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# 引入所有模型，确保被 SQLAlchemy metadata 识别，create_all/migrate 才能正常建表
from app.models.user import *  # noqa: F401, E402
from app.models.person import *  # noqa: F401, E402
from app.models.organization import *  # noqa: F401, E402
from app.models.workflow import *  # noqa: F401, E402
from app.models.report import *  # noqa: F401, E402
from app.models.smart_form import *  # noqa: F401, E402
from app.models.hr_management import *  # noqa: F401, E402

# 开发环境安全检查：如果使用默认 SECRET_KEY 且未设置 DEBUG，自动开启开发模式
if settings.SECRET_KEY == "dev-secret-key-change-in-production-please-use-strong-random-key":
    if not os.environ.get("SECRET_KEY"):
        # 未通过环境变量设置，自动生成临时密钥（开发模式）
        settings.SECRET_KEY = secrets.token_urlsafe(32)

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
