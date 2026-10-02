"""快速测试：登录超管 -> 测试新 KB API -> 入库所有新文档"""
import requests, sys, json

BASE = "http://127.0.0.1:8000/api/v1"

# 1) 登录
r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "Test@1234"})
if r.status_code != 200:
    print("登录失败：", r.status_code, r.text)
    sys.exit(1)
token = r.json().get("access_token")
print(f"[1] 登录 OK，token={token[:20]}...")
H = {"Authorization": f"Bearer {token}"}

# 2) kb/stats
r = requests.get(f"{BASE}/ai/kb/stats", headers=H)
print(f"[2] kb/stats: {r.status_code}", json.dumps(r.json(), ensure_ascii=False, indent=2)[:600])

# 3) kb/docs
r = requests.get(f"{BASE}/ai/kb/docs", headers=H)
j = r.json()
print(f"\n[3] kb/docs: {r.status_code} 共 {j.get('total')} 份文档")
for d in j.get("items", []):
    print(f"   - {d['filename']}  [{d['category']}]  {d['size_human']}  入库={d['indexed']} chunks={d['chunks']}")

# 4) build KB 增量入库
print("\n[4] 开始 增量入库 ...")
r = requests.post(f"{BASE}/ai/kb/build", headers=H, json={})
j = r.json()
print(f"   状态={r.status_code} ok={j.get('ok')} 总分块={j.get('total_chunks')}")
print(f"   ok={j.get('ok_count')}  fail={j.get('fail_count')}  skip={j.get('skip_count')}")
for d in j.get("details", []):
    if not d.get("skipped"):
        print(f"   -> {d.get('filename')}: chunks={d.get('chunks')} ok={d.get('ok')}  err={d.get('error','')}")

# 5) 再次 stats
r = requests.get(f"{BASE}/ai/kb/stats", headers=H)
print(f"\n[5] 入库后 stats: ", json.dumps(r.json(), ensure_ascii=False, indent=2))

# 6) 快速 RAG 检索测试
q = "请假多少天以上需要分管领导审批？"
r = requests.post(f"{BASE}/ai/chat", headers=H, json={"message": q}, timeout=300)
print(f"\n[6] RAG 测试问题: {q}")
rj = r.json()
print(f"   source={rj.get('source')}  kb_hits={rj.get('kb_hits')}  model={rj.get('model')}")
ans = rj.get("answer", "")
print(f"   回答: {ans[:400]}" + ("..." if len(ans) > 400 else ""))

print("\n全部完成 ✓")
