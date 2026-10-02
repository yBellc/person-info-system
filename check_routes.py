import sys
sys.path.insert(0, r"e:\工作工作\text\person-info-system\backend")
import os
os.chdir(r"e:\工作工作\text\person-info-system\backend")

# Check expense router
from app.routers.expense import router as expense_router
print("=== Expense Router Routes ===")
for route in expense_router.routes:
    methods = getattr(route, "methods", set()) or set()
    path = getattr(route, "path", "?")
    print(f"  {methods} {path}")

print()

# Check main app routes
from app.main import app
print("=== Main App Routes (expense-related) ===")
for route in app.routes:
    methods = getattr(route, "methods", set()) or set()
    path = getattr(route, "path", "?")
    if "attachment" in path or "invoice" in path or "voucher" in path:
        print(f"  {methods} {path}")

print()
print("=== Check if POST attachment exists ===")
has_post = False
for route in expense_router.routes:
    methods = getattr(route, "methods", set()) or set()
    path = getattr(route, "path", "?")
    if "attachments" in path and "POST" in methods:
        has_post = True
        print(f"✅ POST route found: {methods} {path}")
if not has_post:
    print("❌ POST attachments route NOT found in expense_router!")
    # Print all routes with their details
    for route in expense_router.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "?")
        print(f"  Route: {methods} {path}")
        print(f"    name: {getattr(route, 'name', '?')}")
        print(f"    endpoint: {getattr(route, 'endpoint', '?')}")
