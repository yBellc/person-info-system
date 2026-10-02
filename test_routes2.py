import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8000"

# Test 1: Direct POST without auth to see raw behavior
print("=== Test 1: POST without auth ===")
boundary = "----TestBoundary12345"
body = f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"test.txt\"\r\nContent-Type: text/plain\r\n\r\nhello world\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"{BASE}/api/v1/workflow-instances/3/attachments",
    data=body,
    method="POST",
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f"Status: {resp.status}")
    print(f"Response: {resp.read().decode()[:500]}")
except urllib.error.HTTPError as e:
    body_text = e.read().decode()[:800]
    print(f"Status: {e.code}")
    print(f"Allow header: {e.headers.get('Allow', '?')}")
    print(f"Response: {body_text}")

# Test 2: Check the OpenAPI spec for attachment routes
print("\n=== Test 2: Check OpenAPI for attachment routes ===")
try:
    req = urllib.request.Request(f"{BASE}/openapi.json")
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    paths = data.get("paths", {})
    
    attachment_paths = []
    for path, methods in paths.items():
        if "attachment" in path or "attachments" in path:
            attachment_paths.append((path, list(methods.keys())))
    
    if attachment_paths:
        for p, m in attachment_paths:
            print(f"  {m} {p}")
    else:
        print("  No attachment routes found in OpenAPI!")
        # Search for workflow-instances paths
        wi_paths = []
        for path, methods in paths.items():
            if "workflow-instances" in path:
                wi_paths.append((path, list(methods.keys())))
        print(f"\n  Workflow-instances paths:")
        for p, m in wi_paths:
            print(f"    {m} {p}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: List all registered routes
print("\n=== Test 3: Check /docs page ===")
try:
    req = urllib.request.Request(f"{BASE}/docs")
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode()
    # Check if attachment routes are in the docs
    if "attachments" in html.lower():
        print("  'attachments' found in /docs page")
    else:
        print("  'attachments' NOT found in /docs page")
except Exception as e:
    print(f"  Error: {e}")
