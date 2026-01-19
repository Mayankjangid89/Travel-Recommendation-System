"""
Database session management for Travel AI Agent
Provides SQLAlchemy engine, SessionLocal, init_db, and dependency get_db
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_ai_agent.db")

# SQLite needs check_same_thread=False
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create tables in DB"""
    from db.models import Base
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency -> yields db session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
