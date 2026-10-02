# -*- coding: utf-8 -*-
"""
P0-1 全流程端到端测试：报销流程 → 附件上传 → 发票OCR → 验真 → 查重 → 审批 → 凭证生成
"""
import requests
import json
import os
import sys
import tempfile
import time

BASE = "http://127.0.0.1:8000/api/v1"
TEST_RESULTS = []

def log(test_name, success, detail=""):
    status = "PASS" if success else "FAIL"
    TEST_RESULTS.append({"test": test_name, "status": status, "detail": detail})
    mark = "✅" if success else "❌"
    print(f"{mark} [{status}] {test_name}")
    if detail and not success:
        print(f"    详情: {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================
# Step 0: 健康检查
# ============================
section("Step 0: 健康检查")
try:
    r = requests.get("http://127.0.0.1:8000/health", timeout=5)
    if r.status_code == 200:
        log("后端服务在线", True)
    else:
        log("后端服务在线", False, f"HTTP {r.status_code}")
        sys.exit(1)
except Exception as e:
    log("后端服务在线", False, str(e))
    print("\n请先启动后端服务（双击 START.bat）")
    sys.exit(1)

# ============================
# Step 1: 登录 - 普通员工
# ============================
section("Step 1: 登录普通员工账号")
employee_token = None
try:
    r = requests.post(f"{BASE}/auth/login", json={
        "username": "office_01",
        "password": "Admin@123"
    }, timeout=10)
    if r.status_code == 200:
        data = r.json()
        employee_token = data.get("access_token")
        log("员工登录成功", True, f"token={employee_token[:20]}...")
    else:
        # 尝试多种密码
        for pwd in ["Test@1234", "Admin@123", "admin123", "123456"]:
            r = requests.post(f"{BASE}/auth/login", json={
                "username": "office_01",
                "password": pwd
            }, timeout=10)
            if r.status_code == 200:
                employee_token = r.json().get("access_token")
                log("员工登录成功", True, f"密码={pwd}")
                break
            elif r.status_code == 423:
                log("员工登录", False, "账号被锁定，请先运行 FIX_ACCOUNTS.bat 解锁")
                break
        if not employee_token:
            log("员工登录成功", False, f"HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    log("员工登录成功", False, str(e))

if not employee_token:
    # 尝试用admin登录
    print("\n  尝试用 admin 账号登录...")
    for pwd in ["Test@1234", "admin123", "Admin@123", "Admin123!"]:
        r = requests.post(f"{BASE}/auth/login", json={
            "username": "admin",
            "password": pwd
        }, timeout=10)
        if r.status_code == 200:
            employee_token = r.json().get("access_token")
            log("admin登录成功", True, f"密码={pwd}")
            break
        elif r.status_code == 423:
            print(f"  admin账号被锁定，请先运行 FIX_ACCOUNTS.bat")
    if not employee_token:
        log("admin登录成功", False, "所有密码尝试均失败")
        sys.exit(1)

headers = {"Authorization": f"Bearer {employee_token}"}

# 获取当前用户信息
r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=10)
if r.status_code == 200:
    user_info = r.json()
    print(f"  当前用户: {user_info.get('username')} (角色: {user_info.get('role')})")
    current_user_id = user_info.get("id")
else:
    log("获取用户信息", False, f"HTTP {r.status_code}")
    sys.exit(1)

# ============================
# Step 2: 获取费用报销模板
# ============================
section("Step 2: 获取费用报销流程模板")
template_id = None
try:
    r = requests.get(f"{BASE}/workflow-templates", headers=headers, timeout=10)
    if r.status_code == 200:
        templates = r.json()
        print(f"  共 {len(templates)} 个模板")
        for t in templates:
            print(f"    - {t['id']}: {t['name']} (类别: {t.get('category', '?')})")
            if "报销" in t["name"] or "expense" in t.get("category", "").lower():
                template_id = t["id"]
        if template_id:
            log("找到报销模板", True, f"模板ID={template_id}")
        else:
            # 用第一个模板
            if templates:
                template_id = templates[0]["id"]
                log("使用第一个模板", True, f"模板ID={template_id} ({templates[0]['name']})")
    else:
        log("获取流程模板", False, f"HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    log("获取流程模板", False, str(e))

if not template_id:
    print("\n无法继续测试，退出")
    sys.exit(1)

# ============================
# Step 3: 发起报销流程
# ============================
section("Step 3: 发起费用报销流程")
instance_id = None
try:
    r = requests.post(f"{BASE}/workflow-instances", headers=headers, json={
        "template_id": template_id,
        "title": "P0测试-差旅费报销-北京出差",
        "form_data": {
            "expense_type": "差旅费",
            "amount": 3580.50,
            "expense_date": "2026-08-10",
            "description": "北京出差3天，含住宿+交通+餐饮",
            "bank_account": "6228480401234567890"
        }
    }, timeout=10)
    if r.status_code == 200 or r.status_code == 201:
        inst = r.json()
        instance_id = inst.get("id")
        log("发起报销流程成功", True, f"实例ID={instance_id}, 状态={inst.get('status')}")
    else:
        log("发起报销流程成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    log("发起报销流程成功", False, str(e))

if not instance_id:
    print("\n无法继续测试，退出")
    sys.exit(1)

# ============================
# Step 4: 上传附件（发票图片+行程单PDF）
# ============================
section("Step 4: 上传附件")

# 4.1 创建模拟发票文本文件（模拟PDF发票）
temp_dir = tempfile.mkdtemp()
invoice_file_path = os.path.join(temp_dir, "test_invoice.pdf")
with open(invoice_file_path, "wb") as f:
    # 写入模拟的发票文本内容（PDF格式头+文本）
    f.write(b"%PDF-1.4\n")
    f.write("增值税普通发票\n".encode("utf-8"))
    f.write("发票号码: 25000000001234567890\n".encode("utf-8"))
    f.write("开票日期: 2026年08月10日\n".encode("utf-8"))
    f.write("购买方: 测试单位\n".encode("utf-8"))
    f.write("销售方: 北京某酒店管理有限公司\n".encode("utf-8"))
    f.write("价税合计(大写): 叁仟伍佰捌拾元整 ￥3580.50\n".encode("utf-8"))

ticket_file_path = os.path.join(temp_dir, "train_ticket.xlsx")
with open(ticket_file_path, "wb") as f:
    f.write(b"PK\x03\x04")  # xlsx magic bytes
    f.write("train ticket content".encode("utf-8"))

attachment_id = None
try:
    with open(invoice_file_path, "rb") as inv_file, open(ticket_file_path, "rb") as ticket_file:
        r = requests.post(
            f"{BASE}/workflow-instances/{instance_id}/attachments",
            headers=headers,
            files=[
                ("files", ("test_invoice.pdf", inv_file, "application/pdf")),
                ("files", ("train_ticket.xlsx", ticket_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ],
            timeout=30
        )
    if r.status_code == 200:
        atts = r.json()
        log("上传附件成功", True, f"上传了 {len(atts)} 个附件")
        for a in atts:
            print(f"    附件ID={a['id']}, 文件名={a['filename']}, 类型={a.get('attachment_type')}, 是发票={a.get('is_invoice')}")
            if a.get("is_invoice"):
                attachment_id = a["id"]
    else:
        log("上传附件成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    log("上传附件成功", False, str(e))

# 4.2 验证附件列表
try:
    r = requests.get(f"{BASE}/workflow-instances/{instance_id}/attachments", headers=headers, timeout=10)
    if r.status_code == 200:
        atts = r.json()
        log("查询附件列表成功", True, f"共 {len(atts)} 个附件")
    else:
        log("查询附件列表成功", False, f"HTTP {r.status_code}")
except Exception as e:
    log("查询附件列表成功", False, str(e))

if not attachment_id:
    print("\n附件上传失败，无法继续发票测试")
    # 仍然继续后续测试
else:
    # ============================
    # Step 5: 发票OCR识别
    # ============================
    section("Step 5: 发票OCR智能识别")
    try:
        r = requests.post(f"{BASE}/attachments/{attachment_id}/ocr", headers=headers, timeout=15)
        if r.status_code == 200:
            ocr_result = r.json()
            log("发票OCR识别成功", True,
                f"发票号={ocr_result.get('invoice_number')}, 金额={ocr_result.get('total_amount')}, 类型={ocr_result.get('invoice_type')}, 置信度={ocr_result.get('confidence')}")
        else:
            log("发票OCR识别成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log("发票OCR识别成功", False, str(e))

    # ============================
    # Step 6: 发票验真
    # ============================
    section("Step 6: 发票验真")
    try:
        r = requests.post(f"{BASE}/invoice/verify", headers=headers, json={
            "invoice_number": "25000000001234567890",
            "invoice_code": None,
            "invoice_date": "2026-08-10",
            "total_amount": 3580.50
        }, timeout=10)
        if r.status_code == 200:
            verify_result = r.json()
            log("发票验真成功", True,
                f"验真结果={verify_result.get('verify_result')}, 详情={json.dumps(verify_result.get('verify_detail', {}), ensure_ascii=False)[:200]}")
        else:
            log("发票验真成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log("发票验真成功", False, str(e))

    # ============================
    # Step 7: 发票查重
    # ============================
    section("Step 7: 发票查重")
    try:
        r = requests.post(f"{BASE}/invoice/check-duplicate", headers=headers, json={
            "invoice_number": "25000000001234567890",
            "invoice_date": "2026-08-10",
            "total_amount": 3580.50
        }, timeout=10)
        if r.status_code == 200:
            dup_result = r.json()
            log("发票查重成功", True,
                f"是否重复={dup_result.get('is_duplicate')}, 消息={dup_result.get('message')}")
        else:
            log("发票查重成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log("发票查重成功", False, str(e))

    # ============================
    # Step 8: 查询流程关联的发票列表
    # ============================
    section("Step 8: 查询流程关联的发票记录")
    try:
        r = requests.get(f"{BASE}/workflow-instances/{instance_id}/invoices", headers=headers, timeout=10)
        if r.status_code == 200:
            invoices = r.json()
            log("查询发票列表成功", True, f"共 {len(invoices)} 条发票记录")
            for inv in invoices:
                print(f"    发票号={inv.get('invoice_number')}, 金额={inv.get('total_amount')}, 已验真={inv.get('is_verified')}, 结果={inv.get('verify_result')}")
        else:
            log("查询发票列表成功", False, f"HTTP {r.status_code}")
    except Exception as e:
        log("查询发票列表成功", False, str(e))

# ============================
# Step 9: 审批流程（需要用审批人账号登录）
# ============================
section("Step 9: 审批流程")

# 获取流程详情，找到审批人
approver_token = None
try:
    r = requests.get(f"{BASE}/workflow-instances/{instance_id}", headers=headers, timeout=10)
    if r.status_code == 200:
        inst_detail = r.json()
        current_handler_id = inst_detail.get("current_handler_id")
        current_node_name = inst_detail.get("current_node_name")
        print(f"  当前审批节点: {current_node_name}, 审批人ID: {current_handler_id}")
        print(f"  流程状态: {inst_detail.get('status')}")
        log("获取流程详情成功", True)
    else:
        log("获取流程详情成功", False, f"HTTP {r.status_code}")
except Exception as e:
    log("获取流程详情成功", False, str(e))

# 尝试用 admin 账号审批（超管可以审批任何流程）
try:
    # admin 可能已经登录了
    if employee_token:
        # 检查当前用户是否是审批人
        r = requests.get(f"{BASE}/auth/me", headers=headers, timeout=10)
        if r.status_code == 200:
            user_info = r.json()
            if user_info.get("role") == "super_admin" or user_info.get("id") == current_handler_id:
                approver_token = employee_token
                print("  当前用户即为审批人（或超管）")

    if not approver_token:
        # 尝试用其他账号登录（使用修复后的密码）
        for username in ["admin", "manager_01", "dept_manager", "bgs_leader"]:
            for pwd in ["Test@1234", "admin123", "Admin@123", "Admin123!"]:
                r = requests.post(f"{BASE}/auth/login", json={
                    "username": username,
                    "password": pwd
                }, timeout=10)
                if r.status_code == 200:
                    approver_token = r.json().get("access_token")
                    print(f"  审批人账号登录成功: {username}")
                    break
                elif r.status_code == 423:
                    print(f"  账号 {username} 被锁定")
                    continue
            if approver_token:
                break

    if approver_token:
        approver_headers = {"Authorization": f"Bearer {approver_token}"}
        
        # 先查看流程当前状态
        r = requests.get(f"{BASE}/workflow-instances/{instance_id}", headers=approver_headers, timeout=10)
        if r.status_code == 200:
            inst_before = r.json()
            print(f"  审批前流程状态: {inst_before.get('status')}")
            print(f"  当前节点: {inst_before.get('current_node_name')}")
            print(f"  模板节点数: {len(inst_before.get('nodes', []))}")
            for node in inst_before.get("nodes", []):
                print(f"    - {node.get('node_name')}: status={node.get('status')}, seq={node.get('seq')}, handler_id={node.get('handler_id')}")
        
        r = requests.post(
            f"{BASE}/workflow-instances/{instance_id}/approve",
            headers=approver_headers,
            json={"action": "approve", "opinion": "P0测试-同意报销"},
            timeout=10
        )
        if r.status_code == 200:
            approved_inst = r.json()
            log("审批通过成功", True, f"流程状态={approved_inst.get('status')}")
            print(f"  审批后状态: {approved_inst.get('status')}")
            
            # 如果还是 pending，继续审批下一个节点
            inst_status = approved_inst.get('status')
            while inst_status == 'pending':
                print(f"  状态仍为 pending，尝试继续审批...")
                r = requests.post(
                    f"{BASE}/workflow-instances/{instance_id}/approve",
                    headers=approver_headers,
                    json={"action": "approve", "opinion": "P0测试-同意报销"},
                    timeout=10
                )
                if r.status_code == 200:
                    approved_inst = r.json()
                    inst_status = approved_inst.get('status')
                    print(f"  继续审批后状态: {inst_status}")
                else:
                    print(f"  继续审批失败: HTTP {r.status_code}")
                    break
        elif r.status_code == 403:
            log("审批通过成功", False, f"权限不足(403)，需要检查审批人权限")
        else:
            log("审批通过成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
    else:
        log("审批人登录", False, "无法找到可用的审批人账号")
except Exception as e:
    log("审批通过成功", False, str(e))

# ============================
# Step 10: 生成会计凭证
# ============================
section("Step 10: 一键生成会计凭证")
try:
    r = requests.post(f"{BASE}/vouchers/generate", headers=headers, json={
        "instance_id": instance_id,
        "voucher_type": "转账凭证",
        "summary": "P0测试-差旅费报销凭证"
    }, timeout=10)
    if r.status_code == 200:
        voucher = r.json()
        log("生成凭证成功", True,
            f"凭证号={voucher.get('voucher_number')}, 金额={voucher.get('total_amount')}, 类型={voucher.get('voucher_type')}")
        print(f"    借方: {json.dumps(voucher.get('debit_items', []), ensure_ascii=False)}")
        print(f"    贷方: {json.dumps(voucher.get('credit_items', []), ensure_ascii=False)}")
    else:
        log("生成凭证成功", False, f"HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    log("生成凭证成功", False, str(e))

# ============================
# Step 11: 查询凭证列表
# ============================
section("Step 11: 查询凭证列表")
try:
    r = requests.get(f"{BASE}/vouchers", headers=headers, timeout=10)
    if r.status_code == 200:
        vouchers = r.json()
        log("查询凭证列表成功", True, f"共 {len(vouchers)} 条凭证")
    else:
        log("查询凭证列表成功", False, f"HTTP {r.status_code}")
except Exception as e:
    log("查询凭证列表成功", False, str(e))

# ============================
# Step 12: 查询流程实例详情（验证表单数据 + 附件信息）
# ============================
section("Step 12: 验证流程详情完整性")
try:
    r = requests.get(f"{BASE}/workflow-instances/{instance_id}", headers=headers, timeout=10)
    if r.status_code == 200:
        inst = r.json()
        has_form = bool(inst.get("form_data"))
        has_schema = bool(inst.get("form_schema"))
        has_attachments = bool(inst.get("attachments"))
        log("流程详情完整性", True,
            f"表单数据={has_form}, 表单Schema={has_schema}, 附件信息={has_attachments}")
        print(f"    标题: {inst.get('title')}")
        print(f"    状态: {inst.get('status')}")
        print(f"    表单: {json.dumps(inst.get('form_data', {}), ensure_ascii=False)[:200]}")
        if inst.get("form_schema"):
            print(f"    Schema字段: {[f.get('field') for f in inst.get('form_schema', [])][:10]}")
        if inst.get("attachments"):
            print(f"    附件数: {len(inst.get('attachments', []))}")
    else:
        log("流程详情完整性", False, f"HTTP {r.status_code}")
except Exception as e:
    log("流程详情完整性", False, str(e))

# ============================
# 测试报告汇总
# ============================
section("测试报告汇总")
total = len(TEST_RESULTS)
passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAIL")

print(f"\n  总测试项: {total}")
print(f"  通过: {passed}")
print(f"  失败: {failed}")
print(f"  通过率: {passed/total*100:.1f}%")

if failed > 0:
    print(f"\n  失败项明细:")
    for r in TEST_RESULTS:
        if r["status"] == "FAIL":
            print(f"    ❌ {r['test']}: {r['detail'][:150]}")

# 保存报告
report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({"total": total, "passed": passed, "failed": failed, "results": TEST_RESULTS}, f, ensure_ascii=False, indent=2)
print(f"\n  报告已保存: {report_path}")

# 清理临时文件
import shutil
shutil.rmtree(temp_dir, ignore_errors=True)

print(f"\n{'='*60}")
if failed == 0:
    print("  🎉 全部测试通过！报销全流程链路通畅。")
else:
    print(f"  ⚠️ 有 {failed} 个测试项失败，需要修复。")
print(f"{'='*60}")
