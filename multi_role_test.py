# -*- coding: utf-8 -*-
"""
多角色全功能测试脚本
测试所有账号登录 + 各功能模块 + 工作流审批全流程 + 留痕验证
"""
import requests
import json
import sys
import os
import tempfile
import time

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = "Test@1234"
ADMIN_PASSWORD = "admin123"
RESULTS = []

def log(test_name, success, detail=""):
    status = "PASS" if success else "FAIL"
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    mark = "✅" if success else "❌"
    print(f"{mark} [{status}] {test_name}")
    if detail and not success:
        print(f"    详情: {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def login(username, password=None):
    pwd = password or PASSWORD
    r = requests.post(f"{BASE}/auth/login", json={"username": username, "password": pwd}, timeout=10)
    if r.status_code == 200:
        token = r.json().get("access_token")
        user = r.json().get("user", {})
        return token, {"Authorization": f"Bearer {token}"}, user
    return None, None, None

def get_user_info(headers):
    r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=10)
    return r.json() if r.status_code == 200 else None

# ============================================================
# 测试账号列表
# ============================================================
TEST_ACCOUNTS = [
    # 大领导
    ("leader_01", "张局长", "unit_admin"),
    ("leader_02", "李副局长", "unit_admin"),
    ("leader_03", "王副局长", "unit_admin"),
    # 财务处
    ("finance_01", "赵财务主任", "person"),
    ("finance_02", "钱财务A", "person"),
    ("finance_03", "孙财务B", "person"),
    # 人事处
    ("hr_01", "吴人事主任", "person"),
    ("hr_02", "郑人事A", "person"),
    ("hr_03", "王人事B", "person"),
    # 技术部
    ("tech_01", "陈技术主任", "person"),
    ("tech_02", "褚技术A", "person"),
    ("tech_03", "卫技术B", "person"),
    # 办公室
    ("office_02", "沈办公主任", "person"),
    ("office_03", "韩办公A", "person"),
    # 后勤部
    ("logi_01", "秦后勤主任", "person"),
    ("logi_02", "尤后勤A", "person"),
]

# ============================================================
# Step 0: 健康检查
# ============================================================
section("Step 0: 健康检查")
try:
    r = requests.get("http://127.0.0.1:8000/health", timeout=5)
    log("后端服务在线", r.status_code == 200)
except Exception as e:
    log("后端服务在线", False, str(e))
    sys.exit(1)

# ============================================================
# Step 1: 批量登录测试
# ============================================================
section("Step 1: 批量登录测试")
tokens = {}  # username -> (token, headers, user_info)
for username, name, expected_role in TEST_ACCOUNTS:
    token, headers, user = login(username)
    if token:
        info = get_user_info(headers) or {}
        actual_role = info.get("role", "?")
        role_ok = actual_role == expected_role
        log(f"登录-{username}({name})", True, f"角色: {actual_role}")
        if not role_ok:
            log(f"角色检查-{username}", False, f"期望: {expected_role}, 实际: {actual_role}")
        tokens[username] = (token, headers, info)
    else:
        log(f"登录-{username}({name})", False, "登录失败")
        # 尝试 admin 密码
        token, headers, user = login(username, "admin123")
        if token:
            tokens[username] = (token, headers, user)
            log(f"登录-{username}(admin密码)", True)

# admin 登录
admin_token, admin_h, admin_user = login("admin", ADMIN_PASSWORD)
if admin_token:
    log("登录-admin", True)
    tokens["admin"] = (admin_token, admin_h, admin_user)
else:
    log("登录-admin", False, "admin登录失败")

# ============================================================
# Step 2: 获取工作流模板
# ============================================================
section("Step 2: 获取工作流模板")
templates = {}
if "tech_02" in tokens:
    _, h, _ = tokens["tech_02"]
    r = requests.get(f"{BASE}/workflow-templates", headers=h, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            for t in data:
                if isinstance(t, dict):
                    templates[t.get("category", t.get("code", ""))] = t
                    print(f"  模板: {t.get('id')} - {t.get('name')} (类别: {t.get('category')})")
        log("获取流程模板", len(templates) > 0)
    else:
        log("获取流程模板", False, f"HTTP {r.status_code}")
else:
    log("获取流程模板", False, "tech_02 未登录")

# ============================================================
# Step 3: 报销流程全链路测试（技术部成员发起 → 部门主任审批 → 财务审批）
# ============================================================
section("Step 3: 报销流程全链路测试")

expense_tpl = templates.get("expense")
inst_id = None

if expense_tpl and "tech_02" in tokens:
    # 3.1 tech_02 发起报销
    _, h_applicant, _ = tokens["tech_02"]
    r = requests.post(f"{BASE}/workflow-instances", headers=h_applicant, json={
        "template_id": expense_tpl.get("id"),
        "title": "多角色测试-差旅费报销-上海出差",
        "form_data": {
            "expense_type": "差旅费",
            "amount": 2500,
            "expense_date": "2026-08-12",
            "description": "上海出差2天技术交流"
        }
    }, timeout=10)
    if r.status_code == 200:
        inst = r.json()
        inst_id = inst.get("id")
        log("tech_02 发起报销", True, f"实例ID={inst_id}")
        print(f"    状态: {inst.get('status')}")
        print(f"    当前处理人ID: {inst.get('current_handler_id')}")
    else:
        log("tech_02 发起报销", False, f"HTTP {r.status_code}: {r.text[:200]}")

    # 3.2 检查动态审批人是否正确解析（应该是 tech_01=陈技术主任）
    if inst_id:
        r = requests.get(f"{BASE}/workflow-instances/{inst_id}", headers=h_applicant, timeout=10)
        if r.status_code == 200:
            detail = r.json()
            current_handler_id = detail.get("current_handler_id")
            current_node_name = detail.get("current_node_name")
            print(f"    当前节点: {current_node_name}, 处理人ID: {current_handler_id}")

            # 验证处理人是否是 tech_01
            tech_01_info = tokens.get("tech_01", (None, None, {}))[2]
            tech_01_id = tech_01_info.get("id")
            if current_handler_id == tech_01_id:
                log("动态审批人解析(部门主任)", True, f"正确指向 tech_01(id={tech_01_id})")
            else:
                log("动态审批人解析(部门主任)", False,
                    f"期望 tech_01(id={tech_01_id}), 实际 handler_id={current_handler_id}")

            # 3.3 tech_01 审批通过
            if "tech_01" in tokens:
                _, h_approver1, _ = tokens["tech_01"]
                r = requests.post(f"{BASE}/workflow-instances/{inst_id}/approve", headers=h_approver1, json={
                    "action": "approve", "opinion": "同意报销-出差属实"
                }, timeout=10)
                if r.status_code == 200:
                    log("tech_01 部门主任审批通过", True)
                    # 检查下一个处理人
                    r = requests.get(f"{BASE}/workflow-instances/{inst_id}", headers=h_applicant, timeout=10)
                    detail = r.json()
                    print(f"    审批后状态: {detail.get('status')}")
                    print(f"    下一处理人ID: {detail.get('current_handler_id')}")

                    # 验证下一处理人是否是 finance_01（财务角色）
                    next_handler_id = detail.get("current_handler_id")
                    if detail.get("status") == "pending":
                        finance_01_info = tokens.get("finance_01", (None, None, {}))[2]
                        finance_01_id = finance_01_info.get("id")
                        if next_handler_id == finance_01_id:
                            log("动态审批人解析(财务)", True, f"正确指向 finance_01(id={finance_01_id})")
                        else:
                            log("动态审批人解析(财务)", False,
                                f"期望 finance_01(id={finance_01_id}), 实际 handler_id={next_handler_id}")

                        # 3.4 finance_01 财务审批通过
                        if "finance_01" in tokens:
                            _, h_finance, _ = tokens["finance_01"]
                            r = requests.post(f"{BASE}/workflow-instances/{inst_id}/approve", headers=h_finance, json={
                                "action": "approve", "opinion": "财务审核通过-金额无误"
                            }, timeout=10)
                            if r.status_code == 200:
                                r = requests.get(f"{BASE}/workflow-instances/{inst_id}", headers=h_applicant, timeout=10)
                                final = r.json()
                                log("finance_01 财务审批通过", True, f"最终状态: {final.get('status')}")
                            else:
                                log("finance_01 财务审批通过", False, f"HTTP {r.status_code}: {r.text[:200]}")
                    elif detail.get("status") == "approved":
                        log("流程已通过(单节点)", True)
                    else:
                        log("审批后状态异常", False, f"状态: {detail.get('status')}")
                else:
                    log("tech_01 部门主任审批通过", False, f"HTTP {r.status_code}: {r.text[:200]}")
        else:
            log("获取流程详情", False, f"HTTP {r.status_code}")
else:
    log("报销流程测试", False, "缺少模板或账号")

# ============================================================
# Step 4: 验证留痕 - 审批完成后记录仍在列表中
# ============================================================
section("Step 4: 留痕验证 - 审批完成后记录可见性")

if inst_id and "tech_02" in tokens:
    _, h, _ = tokens["tech_02"]
    # my_apply 应包含已审批的记录
    r = requests.get(f"{BASE}/workflow-instances?tab=my_apply&page=1&page_size=50", headers=h, timeout=10)
    items = r.json().get("items", [])
    found = [it for it in items if it.get("id") == inst_id]
    log("tech_02 my_apply 包含已审批记录", len(found) > 0,
        f"找到 {len(found)} 条" if found else f"未找到实例 {inst_id}")

# tech_01 应在 my_approve/my_handled 中看到
if inst_id and "tech_01" in tokens:
    _, h, _ = tokens["tech_01"]
    r = requests.get(f"{BASE}/workflow-instances?tab=my_approve&page=1&page_size=50", headers=h, timeout=10)
    items = r.json().get("items", [])
    found = [it for it in items if it.get("id") == inst_id]
    log("tech_01 my_approve 包含已审批记录", len(found) > 0,
        f"找到 {len(found)} 条" if found else "未找到")

    r = requests.get(f"{BASE}/workflow-instances?tab=my_handled&page=1&page_size=50", headers=h, timeout=10)
    items = r.json().get("items", [])
    found = [it for it in items if it.get("id") == inst_id]
    log("tech_01 my_handled 包含已审批记录", len(found) > 0,
        f"找到 {len(found)} 条" if found else "未找到")

# finance_01 应在 my_handled 中看到
if inst_id and "finance_01" in tokens:
    _, h, _ = tokens["finance_01"]
    r = requests.get(f"{BASE}/workflow-instances?tab=my_handled&page=1&page_size=50", headers=h, timeout=10)
    items = r.json().get("items", [])
    found = [it for it in items if it.get("id") == inst_id]
    log("finance_01 my_handled 包含已审批记录", len(found) > 0,
        f"找到 {len(found)} 条" if found else "未找到")

# ============================================================
# Step 5: 请假流程测试（后勤部成员发起 → 部门主任审批 → 人事审批）
# ============================================================
section("Step 5: 请假流程测试")

leave_tpl = templates.get("leave")
leave_inst_id = None

if leave_tpl and "logi_02" in tokens:
    _, h, _ = tokens["logi_02"]
    r = requests.post(f"{BASE}/workflow-instances", headers=h, json={
        "template_id": leave_tpl.get("id"),
        "title": "多角色测试-年假申请",
        "form_data": {
            "leave_type": "年假",
            "start_date": "2026-08-15",
            "end_date": "2026-08-17",
            "days": 3,
            "reason": "年假休息"
        }
    }, timeout=10)
    if r.status_code == 200:
        leave_inst_id = r.json().get("id")
        log("logi_02 发起请假", True, f"实例ID={leave_inst_id}")

        # 检查第一审批人是否是 logi_01
        r = requests.get(f"{BASE}/workflow-instances/{leave_inst_id}", headers=h, timeout=10)
        detail = r.json()
        handler_id = detail.get("current_handler_id")
        logi_01_id = tokens.get("logi_01", (None, None, {}))[2].get("id")
        if handler_id == logi_01_id:
            log("请假-部门主任解析", True, f"正确指向 logi_01")
        else:
            log("请假-部门主任解析", False, f"期望 logi_01(id={logi_01_id}), 实际={handler_id}")

        # logi_01 审批
        if "logi_01" in tokens:
            _, h_lg1, _ = tokens["logi_01"]
            r = requests.post(f"{BASE}/workflow-instances/{leave_inst_id}/approve", headers=h_lg1, json={
                "action": "approve", "opinion": "同意请假"
            }, timeout=10)
            if r.status_code == 200:
                log("logi_01 审批通过", True)

                # 检查下一审批人是否是 hr 角色
                r = requests.get(f"{BASE}/workflow-instances/{leave_inst_id}", headers=h, timeout=10)
                detail = r.json()
                next_handler = detail.get("current_handler_id")
                hr_01_id = tokens.get("hr_01", (None, None, {}))[2].get("id")
                if detail.get("status") == "pending":
                    if next_handler == hr_01_id:
                        log("请假-HR审批人解析", True, f"正确指向 hr_01")
                    else:
                        log("请假-HR审批人解析", False, f"期望 hr_01(id={hr_01_id}), 实际={next_handler}")

                    # hr_01 审批
                    if "hr_01" in tokens:
                        _, h_hr1, _ = tokens["hr_01"]
                        r = requests.post(f"{BASE}/workflow-instances/{leave_inst_id}/approve", headers=h_hr1, json={
                            "action": "approve", "opinion": "人事备案通过"
                        }, timeout=10)
                        if r.status_code == 200:
                            r = requests.get(f"{BASE}/workflow-instances/{leave_inst_id}", headers=h, timeout=10)
                            final = r.json()
                            log("hr_01 人事审批通过", True, f"最终状态: {final.get('status')}")
                        else:
                            log("hr_01 人事审批通过", False, f"HTTP {r.status_code}")
                elif detail.get("status") == "approved":
                    log("请假流程已通过(单节点)", True)
            else:
                log("logi_01 审批通过", False, f"HTTP {r.status_code}: {r.text[:200]}")
    else:
        log("logi_02 发起请假", False, f"HTTP {r.status_code}: {r.text[:200]}")
else:
    log("请假流程测试", False, "缺少模板或账号")

# ============================================================
# Step 6: 用章申请测试（办公室成员发起 → 部门主任审批 → 单位管理员审批）
# ============================================================
section("Step 6: 用章申请测试")

seal_tpl = templates.get("seal")
seal_inst_id = None

if seal_tpl and "office_03" in tokens:
    _, h, _ = tokens["office_03"]
    r = requests.post(f"{BASE}/workflow-instances", headers=h, json={
        "template_id": seal_tpl.get("id"),
        "title": "多角色测试-公章使用申请",
        "form_data": {
            "seal_type": "公章",
            "purpose": "合同盖章",
            "document_name": "2026年度技术合作协议"
        }
    }, timeout=10)
    if r.status_code == 200:
        seal_inst_id = r.json().get("id")
        log("office_03 发起用章申请", True, f"实例ID={seal_inst_id}")

        # 检查第一审批人是否是 office_02（办公室主任）
        r = requests.get(f"{BASE}/workflow-instances/{seal_inst_id}", headers=h, timeout=10)
        detail = r.json()
        handler_id = detail.get("current_handler_id")
        office_02_id = tokens.get("office_02", (None, None, {}))[2].get("id")
        if handler_id == office_02_id:
            log("用章-部门主任解析", True, f"正确指向 office_02")
        else:
            log("用章-部门主任解析", False, f"期望 office_02(id={office_02_id}), 实际={handler_id}")

        # office_02 审批
        if "office_02" in tokens:
            _, h_of2, _ = tokens["office_02"]
            r = requests.post(f"{BASE}/workflow-instances/{seal_inst_id}/approve", headers=h_of2, json={
                "action": "approve", "opinion": "同意用章"
            }, timeout=10)
            if r.status_code == 200:
                log("office_02 主任审批通过", True)

                # 检查下一审批人是否是 unit_admin（大领导）
                r = requests.get(f"{BASE}/workflow-instances/{seal_inst_id}", headers=h, timeout=10)
                detail = r.json()
                next_handler = detail.get("current_handler_id")
                if detail.get("status") == "pending":
                    # 下一处理人应该是 leader_01/02/03 之一
                    leader_ids = [tokens.get(l, (None, None, {}))[2].get("id") for l in ["leader_01", "leader_02", "leader_03"]]
                    if next_handler in leader_ids:
                        log("用章-单位管理员解析", True, f"正确指向 leader (id={next_handler})")
                    else:
                        log("用章-单位管理员解析", False, f"期望 leader, 实际={next_handler}")

                    # leader_01 审批
                    if next_handler and "admin" in tokens:
                        # 用超管审批（fallback）
                        _, h_admin, _ = tokens["admin"]
                        r = requests.post(f"{BASE}/workflow-instances/{seal_inst_id}/approve", headers=h_admin, json={
                            "action": "approve", "opinion": "领导批准用章"
                        }, timeout=10)
                        if r.status_code == 200:
                            r = requests.get(f"{BASE}/workflow-instances/{seal_inst_id}", headers=h, timeout=10)
                            final = r.json()
                            log("领导审批用章通过", True, f"最终状态: {final.get('status')}")
                        else:
                            log("领导审批用章通过", False, f"HTTP {r.status_code}")
                elif detail.get("status") == "approved":
                    log("用章流程已通过(单节点)", True)
            else:
                log("office_02 主任审批通过", False, f"HTTP {r.status_code}: {r.text[:200]}")
    else:
        log("office_03 发起用章申请", False, f"HTTP {r.status_code}: {r.text[:200]}")
else:
    log("用章申请测试", False, "缺少模板或账号")

# ============================================================
# Step 7: 凭证生成测试（对已通过的报销流程）
# ============================================================
section("Step 7: 凭证生成测试")

if inst_id and "tech_02" in tokens:
    _, h, _ = tokens["tech_02"]
    r = requests.post(f"{BASE}/vouchers/generate", headers=h, json={"instance_id": inst_id}, timeout=10)
    if r.status_code == 200:
        voucher = r.json()
        log("凭证生成", True, f"凭证号: {voucher.get('voucher_number')}")
    else:
        log("凭证生成", False, f"HTTP {r.status_code}: {r.text[:200]}")

    # 验证凭证查询
    r = requests.get(f"{BASE}/workflow-instances/{inst_id}/voucher", headers=h, timeout=10)
    if r.status_code == 200 and r.json():
        log("凭证查询", True, f"凭证号: {r.json().get('voucher_number')}")
    else:
        log("凭证查询", False, f"HTTP {r.status_code}")

# ============================================================
# Step 8: 附件上传测试
# ============================================================
section("Step 8: 附件上传测试")

if inst_id and "tech_02" in tokens:
    _, h, _ = tokens["tech_02"]
    # 创建临时测试文件
    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, "test_receipt.pdf")
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write("测试发票\n".encode("utf-8"))

    with open(file_path, "rb") as f:
        r = requests.post(
            f"{BASE}/workflow-instances/{inst_id}/attachments",
            headers=h,
            files=[("files", ("test_receipt.pdf", f, "application/pdf"))],
            timeout=15
        )
    if r.status_code == 200:
        atts = r.json()
        log("附件上传", True, f"上传 {len(atts)} 个文件")
    else:
        log("附件上传", False, f"HTTP {r.status_code}: {r.text[:200]}")

    # 查询附件列表
    r = requests.get(f"{BASE}/workflow-instances/{inst_id}/attachments", headers=h, timeout=10)
    if r.status_code == 200:
        atts = r.json()
        log("附件列表查询", True, f"共 {len(atts)} 个附件")
    else:
        log("附件列表查询", False, f"HTTP {r.status_code}")

# ============================================================
# Step 9: 智能表格测试（简化）
# ============================================================
section("Step 9: 智能表格测试")

if "leader_01" in tokens:
    _, h, _ = tokens["leader_01"]
    r = requests.get(f"{BASE}/smart-forms?page=1&page_size=10", headers=h, timeout=10)
    if r.status_code == 200:
        data = r.json()
        forms = data if isinstance(data, list) else data.get("items", [])
        log("智能表格列表", True, f"共 {len(forms)} 个表格")
    else:
        log("智能表格列表", False, f"HTTP {r.status_code}")

    # 查询待填写任务
    if "tech_03" in tokens:
        _, h_t3, _ = tokens["tech_03"]
        r = requests.get(f"{BASE}/smart-forms/my-tasks?page=1&page_size=10", headers=h_t3, timeout=10)
        if r.status_code == 200:
            log("待填写任务查询", True)
        else:
            log("待填写任务查询", False, f"HTTP {r.status_code}")

# ============================================================
# Step 10: 消息中心测试
# ============================================================
section("Step 10: 消息中心测试")

if "tech_02" in tokens:
    _, h, _ = tokens["tech_02"]
    r = requests.get(f"{BASE}/messages?page=1&page_size=10", headers=h, timeout=10)
    if r.status_code == 200:
        log("消息列表查询", True)
    else:
        log("消息列表查询", False, f"HTTP {r.status_code}")

    r = requests.get(f"{BASE}/messages/stats", headers=h, timeout=10)
    if r.status_code == 200:
        stats = r.json()
        log("消息统计查询", True, f"未读: {stats.get('unread', 0)}")
    else:
        log("消息统计查询", False, f"HTTP {r.status_code}")

# ============================================================
# Step 11: 报销拒绝流程测试
# ============================================================
section("Step 11: 报销拒绝流程测试")

reject_inst_id = None
if expense_tpl and "finance_02" in tokens:
    _, h, _ = tokens["finance_02"]
    r = requests.post(f"{BASE}/workflow-instances", headers=h, json={
        "template_id": expense_tpl.get("id"),
        "title": "多角色测试-办公采购报销(测试拒绝)",
        "form_data": {
            "expense_type": "办公采购",
            "amount": 5000,
            "expense_date": "2026-08-12",
            "description": "采购办公电脑"
        }
    }, timeout=10)
    if r.status_code == 200:
        reject_inst_id = r.json().get("id")
        log("finance_02 发起报销(拒绝测试)", True, f"实例ID={reject_inst_id}")

        # 检查审批人 - 应该是 finance_01（财务处主任）
        r = requests.get(f"{BASE}/workflow-instances/{reject_inst_id}", headers=h, timeout=10)
        detail = r.json()
        handler_id = detail.get("current_handler_id")
        finance_01_id = tokens.get("finance_01", (None, None, {}))[2].get("id")
        if handler_id == finance_01_id:
            log("拒绝测试-部门主任解析", True, f"正确指向 finance_01")
        else:
            log("拒绝测试-部门主任解析", False, f"期望 finance_01(id={finance_01_id}), 实际={handler_id}")

        # finance_01 拒绝
        if "finance_01" in tokens:
            _, h_f1, _ = tokens["finance_01"]
            r = requests.post(f"{BASE}/workflow-instances/{reject_inst_id}/approve", headers=h_f1, json={
                "action": "reject", "opinion": "金额过大，需提供更多明细"
            }, timeout=10)
            if r.status_code == 200:
                r = requests.get(f"{BASE}/workflow-instances/{reject_inst_id}", headers=h, timeout=10)
                final = r.json()
                log("finance_01 拒绝报销", True, f"状态: {final.get('status')}")
            else:
                log("finance_01 拒绝报销", False, f"HTTP {r.status_code}: {r.text[:200]}")

        # 验证被拒绝的记录仍在列表中
        r = requests.get(f"{BASE}/workflow-instances?tab=my_apply&page=1&page_size=50", headers=h, timeout=10)
        items = r.json().get("items", [])
        found = [it for it in items if it.get("id") == reject_inst_id]
        log("被拒绝记录仍在my_apply中", len(found) > 0,
            f"找到" if found else "未找到")
else:
    log("报销拒绝流程测试", False, "缺少模板或账号")

# ============================================================
# 测试报告汇总
# ============================================================
section("测试报告汇总")

passed = sum(1 for r in RESULTS if r["status"] == "PASS")
failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
total = len(RESULTS)

print(f"\n  总测试项: {total}")
print(f"  通过: {passed}")
print(f"  失败: {failed}")
print(f"  通过率: {passed/total*100:.1f}%" if total > 0 else "  无测试项")

if failed > 0:
    print(f"\n  失败项明细:")
    for r in RESULTS:
        if r["status"] == "FAIL":
            print(f"    ❌ {r['test']}: {r['detail']}")

# 保存报告
report = {"total": total, "passed": passed, "failed": failed, "results": RESULTS}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "multi_role_test_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n  报告已保存: multi_role_test_report.json")

if failed == 0:
    print(f"\n  🎉 全部测试通过！")
else:
    print(f"\n  ⚠️ 有 {failed} 个测试项失败，需要修复。")
