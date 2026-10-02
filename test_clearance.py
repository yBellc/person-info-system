import requests

BASE = "http://127.0.0.1:8000/api/v1"

# 1. 登录
r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print(f"登录: {r.status_code}")

# 2. 获取涉密等级字典
r = requests.get(f"{BASE}/system/clearance/levels", headers=headers)
print(f"\n=== 涉密等级字典 ===")
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    for item in r.json():
        print(f"  {item['level']}: {item['name']} - {item['desc']}")
else:
    print(r.text[:200])

# 3. 获取用户涉密等级列表
r = requests.get(f"{BASE}/system/clearance/users", headers=headers)
print(f"\n=== 用户涉密等级列表 ===")
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"总用户数: {data['total']}")
    for u in data['items'][:5]:
        print(f"  {u['username']} ({u['role']}): {u['clearance_level']}={u['clearance_name']}")
else:
    print(r.text[:200])

# 4. 设置admin用户为机密级
r = requests.put(f"{BASE}/system/clearance/users/1", headers=headers, params={"level": 3})
print(f"\n=== 设置admin为机密级 ===")
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    print(r.json())
else:
    print(r.text[:200])

# 5. 查看人员列表（验证security_level字段是否返回）
r = requests.get(f"{BASE}/persons", headers=headers, params={"page": 1, "page_size": 3})
print(f"\n=== 人员列表（验证security_level字段）===")
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    for p in r.json()[:3]:
        print(f"  {p.get('name')}: security_level={p.get('security_level', 'N/A')}, phone={p.get('phone', 'N/A')}")
else:
    print(r.text[:200])
