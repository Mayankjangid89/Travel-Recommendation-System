from fastapi import APIRouter
from db.sessions import SessionLocal
from db.crud import get_all_agencies

router = APIRouter(prefix="/agencies", tags=["Agencies"])


@router.get("")
def list_agencies(limit: int = 50):
    """Get all agencies"""
    db = SessionLocal()
    try:
        agencies = get_all_agencies(db, limit=limit)
        
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
    finally:
        db.close()