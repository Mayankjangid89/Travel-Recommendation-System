from fastapi import APIRouter
from pydantic import BaseModel
from db.sessions import SessionLocal
from db.crud import search_packages, get_all_agencies, bulk_create_packages
from agents.intent_parser import IntentParser
from agents.ranker import PackageRanker
from tools.scraper_engine import ScraperEngine
import asyncio

router = APIRouter(prefix="/recommend", tags=["Recommendation"])


class RecommendRequest(BaseModel):
    query: str
    max_results: int = 5


# ✅ small helper: auto scrape some agencies
async def auto_scrape_and_store(db, agencies, limit=2):
    stored_total = 0

    async with ScraperEngine() as scraper:
        for agency in agencies[:limit]:
            try:
                result = await scraper.scrape_agency(
                    url=agency.url,
                    agency_name=agency.name,
                    extract_packages=True
                )

                if not result or not result.get("success"):
                    continue

                packages = result.get("packages", [])
                if not packages:
                    continue

                # ✅ store packages into DB
                stored_count = bulk_create_packages(db, agency.id, packages)
                stored_total += stored_count

            except Exception as e:
                print(f"❌ Auto scrape failed for {agency.name}: {e}")

    return stored_total


@router.post("")
def recommend_packages(payload: RecommendRequest):
    query = payload.query
    max_results = payload.max_results

    parser = IntentParser()
    intent = parser.parse(query)

    db = SessionLocal()

    try:
        # ✅ Step 1: search in DB first
        packages = search_packages(
            db=db,
            destinations=intent.destinations if intent.destinations else None,
            max_price=intent.budget_per_person if intent.budget_per_person else None,
            min_days=intent.duration_days - intent.flexibility_days if intent.duration_days else None,
            max_days=intent.duration_days + intent.flexibility_days if intent.duration_days else None,
            limit=100
        )

        # ✅ Step 2: if nothing found, AUTO SCRAPE
        if len(packages) == 0:
            agencies = get_all_agencies(db)
            if agencies:
                # scrape max 2 agencies live (can increase later)
                stored = asyncio.run(auto_scrape_and_store(db, agencies, limit=2))

                # search again after scraping
                packages = search_packages(
                    db=db,
                    destinations=intent.destinations if intent.destinations else None,
                    max_price=intent.budget_per_person if intent.budget_per_person else None,
                    min_days=intent.duration_days - intent.flexibility_days if intent.duration_days else None,
                    max_days=intent.duration_days + intent.flexibility_days if intent.duration_days else None,
                    limit=100
                )

        # ✅ convert DB objects into dicts for ranking
        package_dicts = []
        for p in packages:
            package_dicts.append({
                "agency_name": p.agency.name if p.agency else "Unknown",
                "package_title": p.package_title,
                "price_in_inr": p.price_in_inr,
                "duration_days": p.duration_days,
                "destinations": p.destinations,
                "url": p.url,
                "rating": p.rating,
                "reviews_count": p.reviews_count,
                "scraped_at": p.scraped_at,
                "source_confidence_score": p.source_confidence_score,
                "agency_trust_score": p.agency.trust_score if p.agency else 0.5,
                "inclusions": p.inclusions or []
            })

        # ✅ still empty after scraping
        if not package_dicts:
            return {
                "query": query,
                "intent": intent.model_dump(),
                "total_found": 0,
                "ranked": [],
                "message": "⚠️ No packages found even after scraping. Add more agencies or check scraper."
            }

        # ✅ rank results
        ranker = PackageRanker()
        ranked = ranker.rank_packages(package_dicts, intent, max_results=max_results)

        return {
            "query": query,
            "intent": intent.model_dump(),
            "total_found": len(package_dicts),
            "ranked": [
                {
                    "rank": r.rank,
                    "score": r.total_score,
                    "title": r.package.package_title,
                    "price": r.package.price_in_inr,
                    "days": r.package.duration_days,
                    "destinations": r.package.destinations,
                    "agency": r.package.agency_name,
                    "url": r.booking_url,
                    "explanation": r.match_explanation,
                }
                for r in ranked
            ],
            "message": f"✅ Found {len(ranked)} best packages"
        }

    finally:
        db.close()
