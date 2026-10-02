# -*- coding: utf-8 -*-
"""
测试数据初始化脚本 - 双击运行
运行后一次性创建：单位、名单、人员档案、用户账号、流程模板
所有账号密码统一为：test123
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.database import SessionLocal
from app.models.user import User, Unit, UnitRoster
from app.models.person import Person
from app.models.permission import Role, UserRole
from app.models.workflow import WorkflowTemplate
from app.core.security import hash_password
from datetime import date, datetime


def init():
    db = SessionLocal()
    try:
        # ---------- 1. 单位 ----------
        unit1 = db.query(Unit).filter(Unit.name.like("%测试单位%")).first()
        if not unit1:
            unit1 = Unit(name="测试单位-XX局", code="XXJ", is_active=True)
            db.add(unit1)
            db.flush()
            unit2 = Unit(name="测试单位-XX局办公室", code="XXJ-BGS", parent_id=unit1.id, is_active=True)
            unit3 = Unit(name="测试单位-XX局财务科", code="XXJ-CWK", parent_id=unit1.id, is_active=True)
            unit4 = Unit(name="测试单位-XX局人事科", code="XXJ-RSK", parent_id=unit1.id, is_active=True)
            db.add_all([unit2, unit3, unit4])
            db.flush()
            print(f"[OK] 创建测试单位（共4个），根单位ID={unit1.id}")
        else:
            for u in db.query(Unit).filter(Unit.parent_id == unit1.id).all():
                pass
            unit2 = db.query(Unit).filter(Unit.code == "XXJ-BGS").first()
            unit3 = db.query(Unit).filter(Unit.code == "XXJ-CWK").first()
            unit4 = db.query(Unit).filter(Unit.code == "XXJ-RSK").first()

        # ---------- 2. 系统角色（确保存在） ----------
        roles_map = {}
        for code, name, desc, lv in [
            ("super_admin", "系统管理员", "系统最高权限", 0),
            ("unit_admin", "单位管理员", "管理本单位人员", 10),
            ("dept_leader", "部门领导", "审批部门流程", 20),
            ("finance", "财务人员", "审批费用报销", 30),
            ("hr", "人事人员", "审批请假、入职等", 30),
            ("person", "普通用户", "只能操作自己", 100),
        ]:
            r = db.query(Role).filter(Role.code == code).first()
            if not r:
                r = Role(name=name, code=code, description=desc, is_system=(lv <= 10), level=lv, is_active=True)
                db.add(r)
                db.flush()
                print(f"[OK] 创建角色: {name}")
            roles_map[code] = r

        # ---------- 3. 测试人员 + 名单 + 用户 ----------
        test_users = [
            # username, name, id_card, phone, role_str, unit, unit_obj, department
            ("leader",     "张局长",   "110101197001011234", "13800000001", "super_admin", unit1, "领导层"),
            ("admin_01",   "李主任",   "110101197501011235", "13800000002", "unit_admin",  unit1, "办公室"),
            ("bgs_leader", "王科长",   "110101197801011236", "13800000003", "person",      unit2, "办公室"),  # 部门领导
            ("hr_01",      "赵人事",   "110101198501011237", "13800000004", "person",      unit4, "人事科"),  # 人事审批
            ("cw_01",      "孙会计",   "110101198601011238", "13800000005", "person",      unit3, "财务科"),  # 财务审批
            ("office_01",  "周文员",   "110101199001011239", "13800000006", "person",      unit2, "办公室"),  # 普通用户
            ("hr_02",      "吴干事",   "110101199201011240", "13800000007", "person",      unit4, "人事科"),  # 普通用户
            ("cw_02",      "郑出纳",   "110101199301011241", "13800000008", "person",      unit3, "财务科"),  # 普通用户
        ]

        created_users = {}

        for username, name, id_card, phone, role_str, unit_obj, dept in test_users:
            u = db.query(User).filter(User.username == username).first()
            if not u:
                # 身份证解析：出生日期
                birth_y = id_card[6:10]
                birth_m = id_card[10:12]
                birth_d = id_card[12:14]
                birth_date = date(int(birth_y), int(birth_m), int(birth_d))
                gender_str = "女" if int(id_card[-2]) % 2 == 0 else "男"

                # 创建人员档案
                person = Person(
                    name=name, gender=gender_str, birth_date=birth_date,
                    id_card=id_card, phone=phone,
                    department=dept, position="科长" if "主任" in name or "科长" in name else "科员",
                    rank="一级科员" if "长" in name else "二级科员",
                    ethnicity="汉族",
                    political_status="中共党员" if not name.startswith("周") else "群众",
                    work_start_date=date(2010, 7, 1) if "99" not in name else date(2020, 7, 1),
                    join_unit_date=date(2018, 1, 1) if "99" not in name else date(2022, 1, 1),
                    education_level="本科",
                    school="XX大学",
                    unit_id=unit_obj.id,
                )
                db.add(person)
                db.flush()

                # 创建名单记录（防止注册时找不到）
                roster = UnitRoster(
                    unit_id=unit_obj.id, name=name, id_card=id_card,
                    is_registered=True,
                )
                db.add(roster)
                db.flush()

                # 创建用户
                user = User(
                    username=username,
                    password_hash=hash_password("test123"),
                    role=role_str,
                    unit_id=unit_obj.id,
                    person_id=person.id,
                    is_active=True,
                    first_login=False,  # 测试账号不需要首次改密
                )
                db.add(user)
                db.flush()
                roster.registered_user_id = user.id

                created_users[username] = (user, name)
                print(f"[OK] 创建用户: {username:<12}  {name:<8}  role={role_str:<12} unit={unit_obj.name}")
            else:
                # 已存在则更新密码为 test123，跳过首次改密
                u.password_hash = hash_password("test123")
                u.first_login = False
                u.is_active = True
                created_users[username] = (u, u.username)

        db.commit()

        # ---------- 4. 分配角色（UserRole表） ----------
        # 王科长 -> 部门领导
        if "bgs_leader" in created_users:
            u, _ = created_users["bgs_leader"]
            if not db.query(UserRole).filter(UserRole.user_id == u.id, UserRole.role_id == roles_map["dept_leader"].id).first():
                db.add(UserRole(user_id=u.id, role_id=roles_map["dept_leader"].id, granted_by=created_users["leader"][0].id))
                print(f"[OK] 分配角色: 王科长 -> 部门领导")

        # 赵人事 -> 人事角色
        if "hr_01" in created_users:
            u, _ = created_users["hr_01"]
            if not db.query(UserRole).filter(UserRole.user_id == u.id, UserRole.role_id == roles_map["hr"].id).first():
                db.add(UserRole(user_id=u.id, role_id=roles_map["hr"].id, granted_by=created_users["leader"][0].id))
                print(f"[OK] 分配角色: 赵人事 -> 人事人员")

        # 孙会计 -> 财务角色
        if "cw_01" in created_users:
            u, _ = created_users["cw_01"]
            if not db.query(UserRole).filter(UserRole.user_id == u.id, UserRole.role_id == roles_map["finance"].id).first():
                db.add(UserRole(user_id=u.id, role_id=roles_map["finance"].id, granted_by=created_users["leader"][0].id))
                print(f"[OK] 分配角色: 孙会计 -> 财务人员")

        # ---------- 5. 重新生成流程模板 ----------
        print()
        print("[配置] 流程审批节点分配如下：")
        print("  部门负责人审批 -> 王科长 (bgs_leader)")
        print("  人事审批       -> 赵人事 (hr_01)")
        print("  财务审批       -> 孙会计 (cw_01)")
        print("  办公室主任审批 -> 李主任 (admin_01)")
        print("  分管领导审批   -> 张局长 (leader)")
        print()

        # 删除旧流程模板
        db.query(WorkflowTemplate).delete()

        def uid(name):
            return created_users[name][0].id

        templates = [
            {
                "name": "请假申请", "code": "leave", "category": "leave",
                "description": "年假/事假/病假/调休/婚假/产假等请假审批",
                "form_schema": [
                    {"key": "leave_type", "label": "请假类型", "type": "select", "options": ["年假", "事假", "病假", "调休", "婚假", "产假"], "required": True},
                    {"key": "start_date", "label": "开始日期", "type": "date", "required": True},
                    {"key": "end_date", "label": "结束日期", "type": "date", "required": True},
                    {"key": "days", "label": "请假天数", "type": "number", "required": True},
                    {"key": "reason", "label": "请假事由", "type": "textarea", "required": True},
                ],
                "flow_nodes": [
                    {"key": "dept_leader", "name": "部门负责人审批", "type": "approval", "handler_id": uid("bgs_leader")},
                    {"key": "hr", "name": "人事审批", "type": "approval", "handler_id": uid("hr_01")},
                ],
            },
            {
                "name": "费用报销", "code": "expense", "category": "expense",
                "description": "差旅费/招待费/办公采购等费用报销",
                "form_schema": [
                    {"key": "expense_type", "label": "费用类型", "type": "select", "options": ["差旅费", "招待费", "办公采购", "培训费", "其他"], "required": True},
                    {"key": "amount", "label": "报销金额", "type": "number", "required": True},
                    {"key": "expense_date", "label": "费用发生日期", "type": "date", "required": True},
                    {"key": "description", "label": "费用说明", "type": "textarea", "required": True},
                ],
                "flow_nodes": [
                    {"key": "dept_leader", "name": "部门负责人审批", "type": "approval", "handler_id": uid("bgs_leader")},
                    {"key": "finance", "name": "财务审批", "type": "approval", "handler_id": uid("cw_01")},
                ],
            },
            {
                "name": "用章申请", "code": "seal", "category": "seal",
                "description": "公章/合同章/财务章等用章申请",
                "form_schema": [
                    {"key": "seal_type", "label": "用章类型", "type": "select", "options": ["公章", "合同章", "财务章", "法人章"], "required": True},
                    {"key": "purpose", "label": "用章事由", "type": "textarea", "required": True},
                    {"key": "document_name", "label": "文件名称", "type": "text", "required": True},
                ],
                "flow_nodes": [
                    {"key": "dept_leader", "name": "部门负责人审批", "type": "approval", "handler_id": uid("bgs_leader")},
                    {"key": "office", "name": "办公室主任审批", "type": "approval", "handler_id": uid("admin_01")},
                ],
            },
            {
                "name": "出差申请", "code": "travel", "category": "travel",
                "description": "国内/国外出差审批",
                "form_schema": [
                    {"key": "destination", "label": "出差目的地", "type": "text", "required": True},
                    {"key": "start_date", "label": "出发日期", "type": "date", "required": True},
                    {"key": "end_date", "label": "返回日期", "type": "date", "required": True},
                    {"key": "purpose", "label": "出差事由", "type": "textarea", "required": True},
                    {"key": "budget", "label": "预计费用", "type": "number", "required": False},
                ],
                "flow_nodes": [
                    {"key": "dept_leader", "name": "部门负责人审批", "type": "approval", "handler_id": uid("bgs_leader")},
                    {"key": "leader", "name": "分管领导审批", "type": "approval", "handler_id": uid("leader")},
                ],
            },
        ]

        for tpl in templates:
            db.add(WorkflowTemplate(**tpl, is_active=True))

        db.commit()

        print()
        print("=" * 60)
        print("  测试账号全部创建完成！密码统一：test123")
        print("=" * 60)
        print()
        print("  username         | 姓名   | 角色/身份       | 测试用例")
        print("  -----------------|--------|-----------------|-----------------------------")
        print("  leader           | 张局长 | 超级管理员      | 最终审批、系统权限")
        print("  admin_01         | 李主任 | 单位管理员      | 办公室主任审批、管理数据")
        print("  bgs_leader       | 王科长 | 部门领导        | 部门审批第一关")
        print("  hr_01            | 赵人事 | 人事人员        | 请假第二关审批")
        print("  cw_01            | 孙会计 | 财务人员        | 报销第二关审批")
        print("  office_01        | 周文员 | 普通员工(办公)  | 发起流程测试")
        print("  hr_02            | 吴干事 | 普通员工(人事)  | 发起流程测试")
        print("  cw_02            | 郑出纳 | 普通员工(财务)  | 发起流程测试")
        print()
        print("  超级管理员(旧)：admin  /  admin123")
        print()
        print("  推荐测试流程：")
        print("  1) 用 office_01 登录 -> 发起请假申请")
        print("  2) 用 bgs_leader 登录 -> 同意（部门审批）")
        print("  3) 用 hr_01 登录     -> 同意（人事审批）")
        print("  4) 回到 office_01   -> 查看流程已通过")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    init()
    input("按回车关闭窗口...")
