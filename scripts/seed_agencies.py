"""
Seed database with LOCAL + easy-to-scrape agencies (10)

Run:
python -m scripts.seed_agencies
"""
from db.sessions import SessionLocal
from db.crud import create_agency, get_agency_by_domain
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_agencies():
    db = SessionLocal()

    sample_agencies = [
        {
            "name": "Youth Camping",
            "domain": "youthcamping.in",
            "url": "https://www.youthcamping.in/tours/",
            "country": "India",
            "city": "Delhi",
            "agency_type": "private",
            "trust_score": 0.85,
            "is_verified": True,
            "scraping_enabled": True
        },
        {
             "name": "Thrillblazers",
             "domain": "thrillblazers.in",
             "url": "https://thrillblazers.in/",
             "country": "India",
             "city": "Delhi",
             "agency_type": "private",
             "trust_score": 0.78,
             "is_verified": False
        },

        {
            "name": "Himalayan Dream Treks",
            "domain": "himalayandreamtreks.in",
            "url": "https://himalayandreamtreks.in/tours/",
            "country": "India",
            "city": "Dehradun",
            "agency_type": "private",
            "trust_score": 0.75,
            "is_verified": False,
            "scraping_enabled": True
        },
        {
            "name": "India Travel Store",
            "domain": "indiatravelstore.com",
            "url": "https://www.indiatravelstore.com/tour-packages/",
            "country": "India",
            "city": "Delhi",
            "agency_type": "private",
            "trust_score": 0.70,
            "is_verified": False,
            "scraping_enabled": True
        },
        {
            "name": "Travel Triangle",
            "domain": "traveltriangle.com",
            "url": "https://traveltriangle.com/tour-packages",
            "country": "India",
            "city": "Gurugram",
            "agency_type": "private",
            "trust_score": 0.80,
            "is_verified": True,
            "scraping_enabled": True
        },
        {
            "name": "Tour My India",
            "domain": "tourmyindia.com",
            "url": "https://www.tourmyindia.com/packages/",
            "country": "India",
            "city": "Delhi",
            "agency_type": "private",
            "trust_score": 0.85,
            "is_verified": True,
            "scraping_enabled": True
        },
        {
            "name": "Holidify Packages",
            "domain": "holidify.com",
            "url": "https://www.holidify.com/packages",
            "country": "India",
            "city": "Bangalore",
            "agency_type": "private",
            "trust_score": 0.75,
            "is_verified": True,
            "scraping_enabled": True
        },
        {
            "name": "Trawell.in",
            "domain": "trawell.in",
            "url": "https://www.trawell.in/tour-packages",
            "country": "India",
            "city": "Bangalore",
            "agency_type": "private",
            "trust_score": 0.65,
            "is_verified": False,
            "scraping_enabled": True
        },
        {
            "name": "Himachal Tour Packages (Local)",
            "domain": "himachaltourpackages.com",
            "url": "https://www.himachaltourpackages.com/tour-packages/",
            "country": "India",
            "city": "Manali",
            "agency_type": "private",
            "trust_score": 0.65,
            "is_verified": False,
            "scraping_enabled": True
        },
        {
            "name": "Jaipur Travels (Local)",
            "domain": "jaipurtaxiservice.com",
            "url": "https://www.jaipurtaxiservice.com/rajasthan-tour-packages.html",
            "country": "India",
            "city": "Jaipur",
        
            "agency_type": "private",
            "trust_score": 0.60,
            "is_verified": False,
            "scraping_enabled": True
        },
        {
            "name": "Ahmedabad Travel Agency (Local)",
            "domain": "ahmedabadtravels.com",
            "url": "https://www.ahmedabadtravels.com/tour-packages/",
            "country": "India",
            "city": "Ahmedabad",
            "agency_type": "private",
            "trust_score": 0.60,
            "is_verified": False,
            "scraping_enabled": True
        }
    ]

    print("🌱 Seeding agencies...")
    print("=" * 80)

    for agency_data in sample_agencies:
        try:
            existing = get_agency_by_domain(db, agency_data["domain"])
            if existing:
                print(f"⏭️  Skipping {agency_data['name']} (already exists)")
                continue

            agency = create_agency(db, **agency_data)
            print(f"✅ Added: {agency.name} ({agency.domain})")

        except Exception as e:
            print(f"❌ Error adding {agency_data['name']}: {e}")

    db.close()
    print("=" * 80)
    print("✅ Seeding complete!")


if __name__ == "__main__":
    seed_agencies()
