"""
Add manual test packages for Manali and other destinations
Quick way to populate database for testing
"""
from db.sessions import SessionLocal
from db.crud import get_agency_by_domain, create_package
from datetime import datetime


def add_test_packages():
    """Add test packages for common destinations"""
    db = SessionLocal()
    
    # Get Himachal Tourism agency (or any agency)
    agency = get_agency_by_domain(db, "himachaltourism.gov.in")
    
    if not agency:
        # Try Rajasthan Tourism
        agency = get_agency_by_domain(db, "tourism.rajasthan.gov.in")
    
    if not agency:
        print("❌ No agency found! Run: python scripts\\seed_agencies.py")
        db.close()
        return
    
    print(f"✅ Using agency: {agency.name}\n")
    
    # Test packages for popular destinations
    test_packages = [
        # MANALI PACKAGES
        {
            "package_title": "Manali Honeymoon Special",
            "url": "https://example.com/manali-honeymoon",
            "price_in_inr": 18000,
            "duration_days": 5,
            "duration_nights": 4,
            "destinations": ["Manali", "Solang Valley", "Rohtang Pass"],
            "countries": ["India"],
            "inclusions": ["Hotel", "Breakfast", "Dinner", "Transport", "Sightseeing"],
            "exclusions": ["Flights", "Lunch", "Personal Expenses"],
            "highlights": ["Romantic stay", "Snow activities", "Valley views"],
            "scraped_at": datetime.utcnow(),
            "is_active": True,
            "source_confidence_score": 0.8
        },
        {
            "package_title": "Manali Adventure Package",
            "url": "https://example.com/manali-adventure",
            "price_in_inr": 12500,
            "duration_days": 4,
            "duration_nights": 3,
            "destinations": ["Manali", "Solang Valley"],
            "countries": ["India"],
            "inclusions": ["Hotel", "Meals", "Transport", "Paragliding", "River Rafting"],
            "exclusions": ["Flights"],
            "highlights": ["Adventure activities", "Budget friendly"],
            "scraped_at": datetime.utcnow(),
            "is_active": True,
            "source_confidence_score": 0.8
        },
        {
            "package_title": "Manali Kullu Valley Tour",
            "url": "https://example.com/manali-kullu",
            "price_in_inr": 15000,
            "duration_days": 6,
            "duration_nights": 5,
            "destinations": ["Manali", "Kullu", "Manikaran"],
            "countries": ["India"],
            "inclusions": ["Hotel", "All Meals", "Transport", "Guide"],
            "exclusions": ["Flights", "Entry Fees"],
            "highlights": ["Complete valley tour", "Hot springs visit"],
            "scraped_at": datetime.utcnow(),
            "is_active": True,
            "source_confidence_score": 0.8
        },
        
        # GOA PACKAGES
        {
            "package_title": "Goa Beach Holiday",
            "url": "https://example.com/goa",
            "price_in_inr": 12000,
            "duration_days": 5,
            "duration_nights": 4,
            "destinations": ["Goa", "Calangute", "Baga"],
            "countries": ["India"],
            "inclusions": ["Beach Resort", "Breakfast", "Water Sports"],
            "exclusions": ["Flights", "Other Meals"],
            "highlights": ["Beach parties", "Water sports", "Nightlife"],
            "scraped_at": datetime.utcnow(),
            "is_active": True,
            "source_confidence_score": 0.8
        },
    ]
    
    print("📦 Adding test packages...\n")
    
    for pkg_data in test_packages:
        try:
            pkg = create_package(db, agency.id, pkg_data)
            print(f"✅ Added: {pkg.package_title} - ₹{pkg.price_in_inr:,.0f} ({pkg.duration_days} days)")
        except Exception as e:
            print(f"❌ Failed to add {pkg_data['package_title']}: {e}")
    
    db.close()
    
    print("\n✅ Test packages added successfully!")
    print("\nNow try your query: 'I want to go Manali'")


if __name__ == "__main__":
    add_test_packages()