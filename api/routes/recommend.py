from fastapi import APIRouter
from pydantic import BaseModel
from db.sessions import SessionLocal
from db.crud import search_packages
from agents.intent_parser import IntentParser
from agents.ranker import PackageRanker

router = APIRouter(prefix="/recommend", tags=["Recommendation"])


class RecommendRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("")
def recommend_packages(payload: RecommendRequest):
    query = payload.query
    max_results = payload.max_results

    parser = IntentParser()
    intent = parser.parse(query)

    db = SessionLocal()

    # Search packages in DB based on user intent
    packages = search_packages(
        db=db,
        destinations=intent.destinations if intent.destinations else None,
        max_price=intent.budget_per_person if intent.budget_per_person else None,
        max_days=intent.duration_days + intent.flexibility_days if intent.duration_days else None,
        min_days=intent.duration_days - intent.flexibility_days if intent.duration_days else None,
        limit=50
    )

    # Convert SQLAlchemy objects to dict format for ranker
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

    db.close()

    if not package_dicts:
        return {
            "query": query,
            "intent": intent.model_dump(),
            "total_found": 0,
            "ranked": [],
            "message": "⚠️ No packages found in database for your query. Try running scraping again."
        }

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
        "message": f"✅ Found {len(ranked)} best packages for your query"
    }
