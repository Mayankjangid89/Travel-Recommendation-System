from fastapi import APIRouter
from db.sessions import SessionLocal  # ✅ Fixed: "session" not "sessions"
from db.crud import get_database_stats  # ✅ Fixed: function name

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check():
    """Health check endpoint"""
    db = SessionLocal()
    try:
        stats = get_database_stats(db)
        return {
            "status": "ok",
            "database": "connected",
            "stats": stats
        }
    finally:
        db.close()