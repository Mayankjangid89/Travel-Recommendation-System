"""Simple database check - run from project root"""
from db.sessions import SessionLocal
from db.models import Agency, TravelPackage

print("🔍 Checking database...\n")

db = SessionLocal()

# Check agencies
agencies = db.query(Agency).all()
print(f"✅ Total Agencies: {len(agencies)}")
for a in agencies[:3]:
    print(f"   - {a.name}")

# Check packages
packages = db.query(TravelPackage).all()
print(f"\n✅ Total Packages: {len(packages)}")
for p in packages[:5]:
    print(f"   - {p.package_title} | {p.destinations} | ₹{p.price_in_inr:,.0f}")

# Check Manali specifically
manali = [p for p in packages if any('manali' in d.lower() for d in p.destinations)]
print(f"\n✅ Manali Packages: {len(manali)}")
for p in manali:
    print(f"   - {p.package_title} | ₹{p.price_in_inr:,.0f}")

db.close()

if len(packages) == 0:
    print("\n⚠️  NO PACKAGES! Run: python scripts\\add_test_packages.py")