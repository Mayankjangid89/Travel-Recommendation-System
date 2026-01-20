"""
Scrape + Store Packages into Database
- Scrapes agencies from DB
- Extracts packages using Playwright + Gemini (fallback supported)
- Stores packages into DB
- Updates agency scrape status
- LIMIT: scrape max 3 agencies per run
"""


import asyncio
from sqlalchemy.orm import Session

from db.sessions import SessionLocal
from db.crud import (
    get_all_agencies,
    bulk_create_packages,
    update_agency_scrape_status,
)
from tools.scraper_engine import ScraperEngine
from tools.normalizer import DataNormalizer  # Added import


MAX_AGENCIES_PER_RUN = 3  # scrape only 3 agencies per run


def should_scrape_now(agency) -> bool:
    """
    Decide whether to scrape an agency again.
    For now: Always scrape.
    Later you can add: last_scraped_at + cooldown logic
    """
    return True


async def scrape_and_store():
    print("=" * 80)
    print("SCRAPE + STORE PACKAGES INTO DATABASE")
    print("=" * 80)

    db: Session = SessionLocal()
    normalizer = DataNormalizer()  # Initialize normalizer

    try:
        agencies = get_all_agencies(db)

        if not agencies:
            print("No agencies found in DB. Run seed_agencies first.")
            return

        # Always scrape Youth Camping first if present
        agencies.sort(key=lambda a: 0 if "youthcamping" in a.domain else 1)

        print(f"Found {len(agencies)} agencies in DB")
        print(f"Scrape limit enabled: {MAX_AGENCIES_PER_RUN} agencies per run")

        # Apply limit
        agencies_to_scrape = []
        for a in agencies:
            if should_scrape_now(a):
                agencies_to_scrape.append(a)
            if len(agencies_to_scrape) >= MAX_AGENCIES_PER_RUN:
                break

        print(f"Will scrape {len(agencies_to_scrape)} agencies this run")
        print()

        async with ScraperEngine() as scraper:
            for agency in agencies_to_scrape:
                print("-" * 80)
                print(f"Scraping Agency: {agency.name} ({agency.url})")

                try:
                    result = await scraper.scrape_agency(
                        url=agency.url,
                        agency_name=agency.name,
                        extract_packages=True
                    )

                    if not result or not result.get("success"):
                        print("Scraping failed or empty response")
                        update_agency_scrape_status(db, agency.id, False, 0)
                        continue

                    packages = result.get("packages", [])
                    print(f"Scraped {len(packages)} packages")

                    if not packages:
                        print("No valid packages extracted to store")
                        update_agency_scrape_status(db, agency.id, False, 0)
                        continue

                    # NORMALIZE packages
                    normalized_packages = normalizer.normalize_packages_batch(packages, agency.id)
                    print(f"Normalized {len(normalized_packages)} packages (valid only)")

                    if not normalized_packages:
                        print("No valid packages after normalization (check price/duration)")
                        update_agency_scrape_status(db, agency.id, False, 0)
                        continue

                    # Store into DB
                    stored_count = bulk_create_packages(db, agency.id, normalized_packages)
                    print(f"Stored {stored_count} packages into DB")

                    # Update scrape status
                    update_agency_scrape_status(db, agency.id, True, stored_count)

                except Exception as e:
                    print(f"Error while scraping {agency.name}: {e}")
                    try:
                        update_agency_scrape_status(db, agency.id, False, 0)
                    except Exception as inner:
                        print(f"Failed updating agency status too: {inner}")

        print()
        print("=" * 80)
        print("SCRAPING + STORAGE COMPLETE")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(scrape_and_store())
