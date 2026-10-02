# -*- coding: utf-8 -*-
"""
创建完整测试数据：
- 3个大领导（局长+2个副局长）
- 5个部门：财务处、人事处、技术部、办公室、后勤部
- 每个部门 1个主任 + 3个成员
- 设置角色权限（hr/finance）和部门负责人关联
- 确保工作流动态审批人能正确解析
"""
import sys
import os
from datetime import date

# 确保能导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, Unit
from app.models.person import Person
from app.models.organization import Department, Position, Rank, PersonPosition
from app.models.permission import Role, UserRole
from app.models.workflow import WorkflowTemplate

PASSWORD = "Test@1234"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data_log.txt")

# 重定向 stdout 到日志文件
import io
log_buf = io.StringIO()
_orig_stdout = sys.stdout
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, text):
        for f in self.files:
            f.write(text)
    def flush(self):
        for f in self.files:
            f.flush()
sys.stdout = Tee(_orig_stdout, log_buf)

def main():
    db = SessionLocal()
    try:
        # ============================================================
        # 1. 创建单位
        # ============================================================
        print("\n[1] 创建单位...")
        unit = db.query(Unit).filter(Unit.name == "测试单位").first()
        if not unit:
            unit = Unit(name="测试单位", code="test_unit", is_active=True)
            db.add(unit)
            db.commit()
            db.refresh(unit)
            print(f"  ✅ 单位创建: {unit.name} (id={unit.id})")
        else:
            print(f"  ℹ️ 单位已存在: {unit.name} (id={unit.id})")

        # ============================================================
        # 2. 创建职级
        # ============================================================
        print("\n[2] 创建职级...")
        ranks_data = [
            ("局级正职", "rank_director", "管理岗", 1),
            ("局级副职", "rank_deputy", "管理岗", 2),
            ("处级正职", "rank_dept_head", "管理岗", 3),
            ("处级副职", "rank_dept_deputy", "管理岗", 4),
            ("科级正职", "rank_section_head", "管理岗", 5),
            ("科员", "rank_staff", "管理岗", 6),
            ("初级技术", "rank_tech_junior", "技术岗", 6),
            ("中级技术", "rank_tech_mid", "技术岗", 5),
            ("高级技术", "rank_tech_senior", "技术岗", 4),
        ]
        rank_map = {}
        for name, code, cat, lvl in ranks_data:
            r = db.query(Rank).filter(Rank.code == code).first()
            if not r:
                r = Rank(name=name, code=code, category=cat, level=lvl, is_active=True)
                db.add(r)
                db.commit()
                db.refresh(r)
            rank_map[code] = r
            print(f"  ✅ 职级: {r.name} ({r.code})")

        # ============================================================
        # 3. 创建岗位
        # ============================================================
        print("\n[3] 创建岗位...")
        positions_data = [
            ("局长", "pos_director", "管理岗", True),
            ("副局长", "pos_deputy_director", "管理岗", True),
            ("部门主任", "pos_dept_manager", "管理岗", True),
            ("部门副主任", "pos_dept_deputy", "管理岗", True),
            ("财务专员", "pos_finance_staff", "专业技术岗", False),
            ("人事专员", "pos_hr_staff", "专业技术岗", False),
            ("技术工程师", "pos_tech_staff", "专业技术岗", False),
            ("行政专员", "pos_admin_staff", "管理岗", False),
            ("后勤专员", "pos_logistics_staff", "管理岗", False),
        ]
        pos_map = {}
        for name, code, cat, is_lead in positions_data:
            p = db.query(Position).filter(Position.code == code).first()
            if not p:
                p = Position(name=name, code=code, category=cat, is_leadership=is_lead, is_active=True)
                db.add(p)
                db.commit()
                db.refresh(p)
            pos_map[code] = p
            print(f"  ✅ 岗位: {p.name} ({p.code})")

        # ============================================================
        # 4. 创建部门
        # ============================================================
        print("\n[4] 创建部门...")
        depts_data = [
            ("财务处", "dept_finance", "财务管理、预算、报销审批"),
            ("人事处", "dept_hr", "人事管理、人员档案、考勤"),
            ("技术部", "dept_tech", "系统开发、技术支持"),
            ("办公室", "dept_office", "行政办公、印章管理"),
            ("后勤部", "dept_logistics", "后勤保障、资产管理"),
        ]
        dept_map = {}
        for name, code, desc in depts_data:
            d = db.query(Department).filter(Department.code == code, Department.is_deleted == False).first()
            if not d:
                d = Department(
                    unit_id=unit.id, name=name, code=code,
                    description=desc, level=1, sort=0, is_active=True
                )
                db.add(d)
                db.commit()
                db.refresh(d)
            dept_map[code] = d
            print(f"  ✅ 部门: {d.name} (id={d.id})")

        # ============================================================
        # 5. 创建角色（hr, finance）
        # ============================================================
        print("\n[5] 创建角色...")
        roles_data = [
            ("人事角色", "hr", "人事审批权限", 3),
            ("财务角色", "finance", "财务审批权限", 3),
        ]
        role_map = {}
        for name, code, desc, lvl in roles_data:
            r = db.query(Role).filter(Role.code == code).first()
            if not r:
                r = Role(name=name, code=code, description=desc, level=lvl, is_system=True, is_active=True)
                db.add(r)
                db.commit()
                db.refresh(r)
            role_map[code] = r
            print(f"  ✅ 角色: {r.name} ({r.code})")

        # ============================================================
        # 6. 创建人员 + 用户 + 岗位关联
        # ============================================================
        print("\n[6] 创建人员、账号、岗位关联...")

        # 格式: (username, name, gender, dept_code, pos_code, rank_code, role_codes, is_manager)
        all_accounts = [
            # === 3个大领导（不属于具体部门，属于单位顶层） ===
            ("leader_01", "张局长", "男", None, "pos_director", "rank_director", [], False),
            ("leader_02", "李副局长", "男", None, "pos_deputy_director", "rank_deputy", [], False),
            ("leader_03", "王副局长", "女", None, "pos_deputy_director", "rank_deputy", [], False),

            # === 财务处（1主任 + 3成员） ===
            ("finance_01", "赵财务主任", "男", "dept_finance", "pos_dept_manager", "rank_dept_head", ["finance"], True),
            ("finance_02", "钱财务A", "女", "dept_finance", "pos_finance_staff", "rank_staff", ["finance"], False),
            ("finance_03", "孙财务B", "男", "dept_finance", "pos_finance_staff", "rank_staff", ["finance"], False),
            ("finance_04", "周财务C", "女", "dept_finance", "pos_finance_staff", "rank_tech_junior", [], False),

            # === 人事处（1主任 + 3成员） ===
            ("hr_01", "吴人事主任", "男", "dept_hr", "pos_dept_manager", "rank_dept_head", ["hr"], True),
            ("hr_02", "郑人事A", "女", "dept_hr", "pos_hr_staff", "rank_staff", ["hr"], False),
            ("hr_03", "王人事B", "男", "dept_hr", "pos_hr_staff", "rank_staff", ["hr"], False),
            ("hr_04", "李人事C", "女", "dept_hr", "pos_hr_staff", "rank_tech_junior", [], False),

            # === 技术部（1主任 + 3成员） ===
            ("tech_01", "陈技术主任", "男", "dept_tech", "pos_dept_manager", "rank_dept_head", [], True),
            ("tech_02", "褚技术A", "男", "dept_tech", "pos_tech_staff", "rank_tech_mid", [], False),
            ("tech_03", "卫技术B", "女", "dept_tech", "pos_tech_staff", "rank_tech_junior", [], False),
            ("tech_04", "蒋技术C", "男", "dept_tech", "pos_tech_staff", "rank_tech_junior", [], False),

            # === 办公室（1主任 + 3成员） ===
            ("office_02", "沈办公主任", "男", "dept_office", "pos_dept_manager", "rank_dept_head", [], True),
            ("office_03", "韩办公A", "女", "dept_office", "pos_admin_staff", "rank_staff", [], False),
            ("office_04", "杨办公B", "男", "dept_office", "pos_admin_staff", "rank_staff", [], False),
            ("office_05", "朱办公C", "女", "dept_office", "pos_admin_staff", "rank_tech_junior", [], False),

            # === 后勤部（1主任 + 3成员） ===
            ("logi_01", "秦后勤主任", "男", "dept_logistics", "pos_dept_manager", "rank_dept_head", [], True),
            ("logi_02", "尤后勤A", "女", "dept_logistics", "pos_logistics_staff", "rank_staff", [], False),
            ("logi_03", "许后勤B", "男", "dept_logistics", "pos_logistics_staff", "rank_staff", [], False),
            ("logi_04", "何后勤C", "女", "dept_logistics", "pos_logistics_staff", "rank_tech_junior", [], False),
        ]

        created_users = {}
        for username, name, gender, dept_code, pos_code, rank_code, role_codes, is_manager in all_accounts:
            # 检查用户是否已存在
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                # 解锁已有用户
                existing_user.failed_login_count = 0
                existing_user.locked_until = None
                existing_user.is_active = True
                existing_user.password_hash = hash_password(PASSWORD)
                existing_user.first_login = False
                db.commit()
                created_users[username] = existing_user
                print(f"  ℹ️ 账号已存在(已重置密码): {username} ({name})")
                continue

            # 创建 Person
            person = Person(
                unit_id=unit.id,
                name=name,
                gender=gender,
                id_card=f"110101199001{hash(username) % 10000:04d}XXXX",  # 生成唯一身份证号
                phone=f"138{hash(username) % 100000000:08d}",
                department=dept_map[dept_code].name if dept_code else "领导层",
                position=pos_map[pos_code].name,
                rank=rank_map[rank_code].name,
                work_start_date=date(2015, 1, 1),
                join_unit_date=date(2018, 6, 1),
                data_status="confirmed",
            )
            db.add(person)
            db.commit()
            db.refresh(person)

            # 创建 User
            user = User(
                username=username,
                password_hash=hash_password(PASSWORD),
                role="person",
                person_id=person.id,
                unit_id=unit.id,
                is_active=True,
                first_login=False,
                failed_login_count=0,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users[username] = user

            # 创建 PersonPosition
            dept_id = dept_map[dept_code].id if dept_code else None
            pp = PersonPosition(
                person_id=person.id,
                department_id=dept_id,
                position_id=pos_map[pos_code].id,
                rank_id=rank_map[rank_code].id,
                is_primary=True,
                is_current=True,
                start_date=date(2018, 6, 1),
            )
            db.add(pp)
            db.commit()

            # 设置部门负责人
            if is_manager and dept_code:
                dept_map[dept_code].manager_id = person.id
                db.commit()

            # 分配角色
            for rc in role_codes:
                ur = UserRole(
                    user_id=user.id,
                    role_id=role_map[rc].id,
                    unit_id=unit.id,
                )
                db.add(ur)
            db.commit()

            print(f"  ✅ 创建: {username} ({name}) - 部门: {dept_map[dept_code].name if dept_code else '领导层'} - 岗位: {pos_map[pos_code].name}")

        # ============================================================
        # 7. 给大领导设置 unit_admin 角色（可以审批用章申请）
        # ============================================================
        print("\n[7] 设置大领导为单位管理员...")
        for uname in ["leader_01", "leader_02", "leader_03"]:
            u = created_users.get(uname)
            if u:
                u.role = "unit_admin"
                u.unit_id = unit.id
                db.commit()
                print(f"  ✅ {uname} -> unit_admin")

        # 确保 admin 账号也解锁
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            admin.failed_login_count = 0
            admin.locked_until = None
            admin.is_active = True
            admin.password_hash = hash_password("admin123")
            admin.first_login = False
            db.commit()
            print(f"  ✅ admin 账号已解锁")

        # ============================================================
        # 8. 汇总
        # ============================================================
        print("\n" + "=" * 60)
        print("测试数据创建完成！")
        print("=" * 60)
        print(f"\n单位: {unit.name}")
        print(f"部门数: {len(dept_map)}")
        print(f"总账号数: {len(created_users)} + admin")
        print(f"\n所有账号密码: {PASSWORD} (admin密码: admin123)")
        print("\n账号清单:")
        print("-" * 60)
        for username, name, gender, dept_code, pos_code, rank_code, role_codes, is_manager in all_accounts:
            dept_name = dept_map[dept_code].name if dept_code else "领导层"
            pos_name = pos_map[pos_code].name
            roles_str = f" [{','.join(role_codes)}]" if role_codes else ""
            mgr_str = " (主任)" if is_manager else ""
            print(f"  {username:15s} | {name:8s} | {dept_name:6s} | {pos_name:10s}{mgr_str}{roles_str}")
        print("-" * 60)
        print(f"\n大领导(3): leader_01, leader_02, leader_03")
        print(f"财务处(4): finance_01(主任,finance角色), finance_02-04")
        print(f"人事处(4): hr_01(主任,hr角色), hr_02-04")
        print(f"技术部(4): tech_01(主任), tech_02-04")
        print(f"办公室(4): office_02(主任), office_03-05")
        print(f"后勤部(4): logi_01(主任), logi_02-04")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
        # 写入日志文件
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(log_buf.getvalue())


if __name__ == "__main__":
    main()
