# -*- coding: utf-8 -*-
"""
修复测试账号：解锁 office_01 + 重置密码为已知值
"""
import sys
sys.path.insert(0, r"e:\工作工作\text\person-info-system\backend")
import os
os.chdir(r"e:\工作工作\text\person-info-system\backend")

from datetime import datetime
from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

# 修复1: 解锁 office_01
print("=" * 50)
print("修复测试账号")
print("=" * 50)

for username in ["office_01", "admin"]:
    user = db.query(User).filter(User.username == username).first()
    if user:
        print(f"\n用户: {user.username} (ID={user.id})")
        print(f"  角色: {user.role}")
        print(f"  状态: {'启用' if user.is_active else '停用'}")
        print(f"  失败次数: {user.failed_login_count}")
        print(f"  锁定至: {user.locked_until}")
        print(f"  是否首登: {user.first_login}")
        
        # 解锁 + 重置密码
        user.locked_until = None
        user.failed_login_count = 0
        user.first_login = False  # 关闭首次登录强制改密
        
        # 新密码: Test@1234 (符合复杂度要求: 大写+小写+数字+符号)
        new_password = "Test@1234"
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        
        print(f"  ✅ 已解锁，密码已重置为: {new_password}")
    else:
        print(f"\n用户 {username} 不存在")

db.commit()

# 验证
print("\n" + "=" * 50)
print("验证修复结果")
print("=" * 50)

for username in ["office_01", "admin"]:
    user = db.query(User).filter(User.username == username).first()
    if user:
        print(f"\n{user.username}:")
        print(f"  locked_until: {user.locked_until}")
        print(f"  failed_login_count: {user.failed_login_count}")
        print(f"  first_login: {user.first_login}")
        print(f"  可以用密码 Test@1234 登录")

db.close()
print("\n✅ 修复完成！现在可以用 Test@1234 作为密码登录 office_01 和 admin 账号")
