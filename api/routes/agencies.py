from fastapi import APIRouter
from db.sessions import SessionLocal
from db.crud import get_agencies

router = APIRouter(prefix="/agencies", tags=["Agencies"])


@router.get("")
def list_agencies(limit: int = 50):
    db = SessionLocal()
    agencies = get_agencies(db, limit=limit)
    db.close()

    return [
        {
            "id": a.id,
            "name": a.name,
            "domain": a.domain,
            "url": a.url,
            "city": a.city,
            "country": a.country,
            "trust_score": a.trust_score,
            "scraping_enabled": a.scraping_enabled,
        }
        for a in agencies
    ]
