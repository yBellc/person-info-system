import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"

# First, login and get a token
login_data = json.dumps({"username": "office_01", "password": "123456"}).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    login_result = json.loads(resp.read())
    token = login_result.get("access_token", "")
    print(f"[OK] Login successful, token: {token[:20]}...")
except Exception as e:
    print(f"[FAIL] Login failed: {e}")
    sys.exit(1)

# Now test the attachment upload with proper multipart form-data
import uuid
boundary = uuid.uuid4().hex
filename = "test_invoice.txt"
content = b"Hello, this is a test invoice file"

body = (
    f"--{boundary}\r\n"
    f"Content-Disposition: form-data; name=\"files\"; filename=\"{filename}\"\r\n"
    f"Content-Type: text/plain\r\n"
    f"\r\n"
    f"Hello, this is a test invoice file\r\n"
    f"--{boundary}--\r\n"
).encode()

req = urllib.request.Request(
    f"{BASE}/api/v1/workflow-instances/3/attachments",
    data=body,
    method="POST",
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
        "Content-Length": str(len(body))
    }
)

try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f"[OK] Upload successful! Status: {resp.status}")
    print(f"Response: {resp.read().decode()[:500]}")
except urllib.error.HTTPError as e:
    body_text = e.read().decode()[:500]
    print(f"[FAIL] Upload failed! Status: {e.code}")
    print(f"Response: {body_text}")
    
    # Check the Allow header
    allowed = e.headers.get("Allow", "?")
    print(f"Allow header: {allowed}")
except Exception as e:
    print(f"[FAIL] Upload error: {e}")

# Also test with a simple OPTIONS request to see allowed methods
print("\n=== Testing OPTIONS to see allowed methods ===")
req2 = urllib.request.Request(
    f"{BASE}/api/v1/workflow-instances/3/attachments",
    method="OPTIONS"
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    allow = resp2.headers.get("Allow", "?")
    print(f"Allow: {allow}")
except urllib.error.HTTPError as e:
    allow = e.headers.get("Allow", "?")
    print(f"Status: {e.code}, Allow: {allow}")
