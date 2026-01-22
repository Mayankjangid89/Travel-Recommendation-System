"""Check database contents"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.sessions import SessionLocal
from db.models import Agency, TravelPackage

db = SessionLocal()

print("=" * 80)
print("📊 DATABASE STATUS")
print("=" * 80)

# Count agencies
agency_count = db.query(Agency).count()
print(f"\n✅ Agencies: {agency_count}")

if agency_count > 0:
    agencies = db.query(Agency).limit(5).all()
    for agency in agencies:
        print(f"   - {agency.name}")
else:
    print("   ⚠️  NO AGENCIES FOUND!")
    print("   Run: python scripts\\seed_agencies.py")

# Count packages
package_count = db.query(TravelPackage).count()
print(f"\n✅ Packages: {package_count}")

if package_count > 0:
    packages = db.query(TravelPackage).limit(10).all()
    for pkg in packages:
        print(f"   - {pkg.package_title}: {pkg.destinations} (₹{pkg.price_in_inr:,.0f})")
else:
    print("   ⚠️  NO PACKAGES FOUND!")
    print("   Run: python scripts\\add_test_packages.py")

# Check Manali packages specifically
manali_packages = db.query(TravelPackage).filter(
    TravelPackage.destinations.contains(["Manali"])
).all()

print(f"\n✅ Manali packages: {len(manali_packages)}")
if manali_packages:
    for pkg in manali_packages:
        print(f"   - {pkg.package_title} (₹{pkg.price_in_inr:,.0f})")

db.close()

print("\n" + "=" * 80)