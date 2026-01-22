from fastapi import APIRouter
from db.sessions import SessionLocal  # ✅ Fixed
from db.crud import search_packages

router = APIRouter(prefix="/packages", tags=["Packages"])


@router.get("")
def list_packages(limit: int = 50):
    """List all packages"""
    db = SessionLocal()
    try:
        packages = search_packages(db, limit=limit)
        
        return [
            {
                "id": p.id,
                "agency_id": p.agency_id,
                "package_title": p.package_title,
                "price_in_inr": p.price_in_inr,
                "duration_days": p.duration_days,
                "destinations": p.destinations,
                "url": p.url,
                "scraped_at": str(p.scraped_at),
            }
            for p in packages
        ]
    finally:
        db.close()