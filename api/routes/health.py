from fastapi import APIRouter
from db.sessions import SessionLocal
from db.crud import get_db_stats

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check():
    db = SessionLocal()
    stats = get_db_stats(db)
    db.close()

    return {
        "status": "ok",
        "database": "connected",
        "stats": stats
    }
