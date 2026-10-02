"""后端接口流程测试脚本"""
import json
import requests

BASE = "http://127.0.0.1:8000/api/v1"


def main():
    # 1. 超管登录
    r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    admin_token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {admin_token}"}
    print("✓ 超管登录成功")

    # 2. 创建单位
    r = requests.post(f"{BASE}/units", headers=H, json={"name": "一年级一班", "code": "G1C1"})
    assert r.status_code == 200, r.text
    unit = r.json()
    unit_id = unit["id"]
    print(f"✓ 创建单位: {unit['name']} (id={unit_id})")

    # 3. 导入名单（用合法校验位的身份证号）
    roster = {
        "items": [
            {"name": "张三", "id_card": "110101199003078398"},
            {"name": "李四", "id_card": "110101199205151280"},
        ]
    }
    r = requests.post(f"{BASE}/units/{unit_id}/roster", headers=H, json=roster)
    assert r.status_code == 200, r.text
    print(f"✓ 导入名单: {r.json()}")

    # 4. 查看名单
    r = requests.get(f"{BASE}/units/{unit_id}/roster", headers=H)
    assert r.status_code == 200, r.text
    print(f"✓ 名单列表: {json.dumps(r.json(), ensure_ascii=False)}")

    # 5. 用户注册（凭名单匹配）
    r = requests.post(f"{BASE}/auth/register", json={
        "username": "zhangsan", "password": "123456",
        "name": "张三", "id_card": "110101199003078398",
    })
    assert r.status_code == 200, r.text
    user_token = r.json()["access_token"]
    UH = {"Authorization": f"Bearer {user_token}"}
    print(f"✓ 用户注册成功: {r.json()['username']}")

    # 6. 重复注册应失败
    r = requests.post(f"{BASE}/auth/register", json={
        "username": "zhangsan2", "password": "123456",
        "name": "张三", "id_card": "110101199003078398",
    })
    assert r.status_code == 400, f"应拒绝重复注册: {r.text}"
    print(f"✓ 重复注册被正确拒绝")

    # 7. 查看个人信息（应已联动回填出生日期和性别）
    me = requests.get(f"{BASE}/auth/me", headers=UH).json()
    person_id = me["person_id"]
    r = requests.get(f"{BASE}/persons/{person_id}", headers=UH)
    assert r.status_code == 200, r.text
    person = r.json()
    print(f"✓ 个人信息: 姓名={person['name']}, 性别={person['gender']}, 出生日期={person['birth_date']}, 年龄={person['age']}")

    # 8. 本人补充信息
    r = requests.put(f"{BASE}/persons/{person_id}", headers=UH, json={
        "phone": "13800138000",
        "education_level": "本科",
        "native_place": "北京市海淀区",
        "reason": "本人补充联系方式",
    })
    assert r.status_code == 200, r.text
    print(f"✓ 本人补充信息成功, 手机={r.json()['phone']}")

    # 9. 本人尝试改职务（应被拒）
    r = requests.put(f"{BASE}/persons/{person_id}", headers=UH, json={"position": "科长"})
    assert r.status_code == 403, f"个人账号不应改职务: {r.text}"
    print(f"✓ 个人账号改职务被正确拒绝")

    # 10. 查看变更历史
    r = requests.get(f"{BASE}/persons/{person_id}/changes", headers=UH)
    assert r.status_code == 200, r.text
    print(f"✓ 变更历史记录数: {len(r.json())}")

    # 11. 统计接口
    r = requests.get(f"{BASE}/statistics/overview", headers=UH)
    assert r.status_code == 200, r.text
    print(f"✓ 统计总览: {r.json()}")

    print("\n===== 全部测试通过 =====")


if __name__ == "__main__":
    main()
