import sys, os
sys.path.insert(0, 'e:/工作工作/text/person-info-system/backend')
os.chdir('e:/工作工作/text/person-info-system/backend')

from app.database import SessionLocal
from app.models.smart_form import SmartFormTask, SmartFormDistribution

db = SessionLocal()

# Fix all distributions' submitted_count
dists = db.query(SmartFormDistribution).all()
fixed = 0
for d in dists:
    actual = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == d.id,
        SmartFormTask.status == "submitted",
    ).count()
    if d.submitted_count != actual:
        print(f"Dist {d.id}: submitted_count was {d.submitted_count}, fixing to {actual}")
        d.submitted_count = actual
        fixed += 1

db.commit()
print(f"\nFixed {fixed} distributions")

# Verify
print("\nVerification:")
for d in dists:
    actual = db.query(SmartFormTask).filter(
        SmartFormTask.distribution_id == d.id,
        SmartFormTask.status == "submitted",
    ).count()
    if actual > 0:
        print(f"  Dist {d.id}: submitted_count={d.submitted_count}, actual={actual} ✓")

db.close()
