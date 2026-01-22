"""
Scrape agencies and store packages in database
This populates your database with real data
"""
import asyncio
import sys
from datetime import datetime

from db.sessions import SessionLocal
from db.crud import (
    get_agency_by_domain,
    create_package,
    update_agency_scrape_status,
    get_all_agencies
)
from tools.scraper_engine import ScraperEngine
from tools.normalizer import DataNormalizer


async def scrape_and_store_packages():
    """Scrape all agencies and store packages"""
    db = SessionLocal()
    normalizer = DataNormalizer()
    
    print("=" * 80)
    print("🚀 SCRAPING AGENCIES AND STORING PACKAGES")
    print("=" * 80)
    print()
    
    # Get all active agencies
    agencies = get_all_agencies(db, limit=100, active_only=True)
    TARGET_DOMAINS = ["youthcamping.in", "thrillblazers.in"]
    agencies = [a for a in agencies if a.domain in TARGET_DOMAINS]

    if not agencies:
        print("❌ No agencies found in database!")
        print("   Run: python scripts\\seed_agencies.py")
        return
    
    print(f"📋 Found {len(agencies)} agencies to scrape\n")
    
    total_packages = 0
    
    # Scrape each agency
    async with ScraperEngine() as scraper:
        for i, agency in enumerate(agencies, 1):
            print(f"\n[{i}/{len(agencies)}] Scraping: {agency.name}")
            print(f"   URL: {agency.url}")
            
            try:
                # Scrape the agency
                result = await scraper.scrape_agency(
                    url=agency.url,
                    agency_name=agency.name,
                    extract_packages=True
                )
                
                if not result['success']:
                    print(f"   ❌ Scraping failed: {result.get('error', 'Unknown error')}")
                    update_agency_scrape_status(db, agency.id, success=False)
                    continue
                
                raw_packages = result['packages']
                print(f"   ✅ Found {len(raw_packages)} raw packages")
                
                # Normalize packages
                normalized_packages = normalizer.normalize_packages_batch(
                    raw_packages,
                    agency.id
                )
                
                if not normalized_packages:
                    print(f"   ⚠️  No valid packages after normalization")
                    update_agency_scrape_status(db, agency.id, success=True, packages_found=0)
                    continue
                
                print(f"   ✅ Normalized {len(normalized_packages)} packages")
                
                # Store in database
                stored_count = 0
                for pkg_data in normalized_packages:
                    try:
                        create_package(db, agency.id, pkg_data)
                        stored_count += 1
                    except Exception as e:
                        print(f"   ⚠️  Failed to store package: {e}")
                
                print(f"   ✅ Stored {stored_count} packages in database")
                total_packages += stored_count
                
                # Update agency scrape status
                update_agency_scrape_status(
                    db,
                    agency.id,
                    success=True,
                    packages_found=stored_count
                )
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                update_agency_scrape_status(db, agency.id, success=False)
    
    db.close()
    
    print("\n" + "=" * 80)
    print(f"✅ SCRAPING COMPLETE!")
    print(f"   Total packages stored: {total_packages}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(scrape_and_store_packages())