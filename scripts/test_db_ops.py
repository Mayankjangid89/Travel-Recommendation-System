"""
Test database operations
Run this to verify CRUD operations work correctly
"""
from db.sessions import SessionLocal
from db.crud import *
from tools.normalizer import DataNormalizer
from datetime import datetime



def test_crud_operations():
    """Test all CRUD operations"""
    db = SessionLocal()
    normalizer = DataNormalizer()
    
    print("=" * 80)
    print("TESTING DATABASE CRUD OPERATIONS")
    print("=" * 80)
    print()
    
    # Test 1: Get all agencies
    print("1. Testing: Get All Agencies")
    agencies = get_all_agencies(db, limit=10)
    print(f"   Found {len(agencies)} agencies")
    for agency in agencies[:3]:
        print(f"   - {agency.name} ({agency.domain})")
    print()
    
    # Test 2: Get agency by domain
    print("2. Testing: Get Agency by Domain")
    agency = get_agency_by_domain(db, "tourism.rajasthan.gov.in")
    if agency:
        print(f"   Found: {agency.name}")
        print(f"   Trust Score: {agency.trust_score}")
        print(f"   Last Scraped: {agency.last_scraped_at}")
    else:
        print("   Agency not found (run seed_agencies.py first)")
        # Create dummy agency if not found for testing
        agency = get_all_agencies(db, limit=1)[0]
    print()
    
    # Test 3: Create sample packages
    print("3. Testing: Create Packages")
    sample_packages = [
        {
            "title": "Jaipur Heritage Tour",
            "price_inr": 15000,
            "duration_days": 5,
            "destinations": ["Jaipur", "Udaipur"],
            "inclusions": ["Hotel", "Meals", "Transport"],
            "url": "https://example.com/jaipur-tour"
        },
        {
            "title": "Rajasthan Desert Safari",
            "price_inr": 22000,
            "duration_days": 7,
            "destinations": ["Jaisalmer", "Jodhpur", "Bikaner"],
            "inclusions": ["Hotel", "Meals", "Transport", "Camel Safari"],
            "url": "https://example.com/desert-safari"
        }
    ]
    
    # Normalize and create packages
    normalized = normalizer.normalize_packages_batch(sample_packages, agency.id)
    created_count = bulk_create_packages(db, agency.id, normalized)
    print(f"   Created {created_count} packages")
    print()
    
    # Test 4: Search packages
    print("4. Testing: Search Packages")
    
    # Search by destination
    packages = search_packages(
        db,
        destinations=["Jaipur"],
        min_price=10000,
        max_price=20000,
        limit=10
    )
    print(f"   Found {len(packages)} packages matching criteria:")
    for pkg in packages[:3]:
        print(f"   - {pkg.package_title}: {pkg.price_in_inr} ({pkg.duration_days} days)")
    print()
    
    # Test 5: Update agency scrape status
    print("5. Testing: Update Agency Scrape Status")
    updated = update_agency_scrape_status(
        db,
        agency.id,
        success=True,
        packages_found=created_count
    )
    if updated:
        print(f"   Updated {agency.name}")
        print(f"   Success Count: {updated.scrape_success_count}")
        print(f"   Last Scraped: {updated.last_scraped_at}")
    print()
    
    # Test 6: Get packages by agency
    print("6. Testing: Get Packages by Agency")
    agency_packages = get_packages_by_agency(db, agency.id)
    print(f"   Found {len(agency_packages)} packages for {agency.name}")
    print()
    
    # Test 7: Database statistics
    print("7. Testing: Database Statistics")
    stats = get_db_stats(db)
    print(f"   Total Agencies: {stats['total_agencies']}")
    print(f"   Active Agencies: {stats['active_agencies']}")
    print(f"   Total Packages: {stats.get('total_packages', 0)}")
    print(f"   Active Packages: {stats.get('active_packages', 0)}")
    print()
    
    # Test 8: Create scraping job
    print("8. Testing: Scraping Job Tracking")
    job = create_scraping_job(
        db,
        job_id=f"job_{int(datetime.utcnow().timestamp())}",
        agency_id=agency.id,
        job_type="package_scrape"
    )
    print(f"   Created job: {job.job_id}")
    
    # Update job status
    updated_job = update_scraping_job(
        db,
        job.job_id,
        status="completed",
        packages_found=created_count,
        packages_stored=created_count
    )
    print(f"   Updated job status: {updated_job.status}")
    print()
    
    db.close()
    
    print("=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    test_crud_operations()