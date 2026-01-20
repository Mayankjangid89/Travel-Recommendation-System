import asyncio
from tools.scraper_engine import ScraperEngine

URL = "https://www.youthcamping.in/tours/"

async def main():
    async with ScraperEngine() as scraper:
        result = await scraper.scrape_agency(
            url=URL,
            agency_name="Youth Camping",
            extract_packages=True
        )

        print("\n✅ RAW RESULT SUCCESS:", result.get("success"))
        print("✅ TOTAL PACKAGES FOUND:", len(result.get("packages", [])))

        # show first 2 packages
        pkgs = result.get("packages", [])
        for i, p in enumerate(pkgs[:2], 1):
            print(f"\n--- Package {i} ---")
            for k, v in p.items():
                print(k, "=>", v)

asyncio.run(main())
