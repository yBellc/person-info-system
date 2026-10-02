"""安全模块：密码哈希、JWT、密码强度校验"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from app import settings


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）"""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """密码强度校验：至少8位，包含大小写字母、数字、特殊字符中的3种"""
    if len(password) < 8:
        return False, "密码长度至少8位"
    if len(password) > 100:
        return False, "密码长度不能超过100位"

    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password))

    type_count = sum([has_upper, has_lower, has_digit, has_special])
    if type_count < 3:
        return False, "密码需包含大写字母、小写字母、数字、特殊字符中的至少3种"

    # 常见弱密码检查
    weak_patterns = ['123456', 'password', 'abc123', '111111', '000000', 'qwerty', 'admin']
    for pattern in weak_patterns:
        if pattern in password.lower():
            return False, f"密码不能包含常见弱密码片段: {pattern}"

    return True, "密码强度合格"


def is_password_in_history(password: str, history: list) -> bool:
    """检查密码是否在最近使用过的密码历史中"""
    for old_hash in (history or []):
        if verify_password(password, old_hash):
            return True
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌

    Args:
        data: 要编码的数据，至少包含 sub(用户ID)
        expires_delta: 过期时间增量，默认用配置
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解码 JWT 令牌，失败返回 None"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
