# =============================================================
# AeroDesk — Database Connection
# backend/database.py
# =============================================================
# Manages the SQLAlchemy engine, session factory,
# and the Base class all models inherit from.
# =============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Check your .env file.")

# Create the SQLAlchemy engine
# pool_pre_ping=True checks connections before using them
# Prevents errors from stale/dropped database connections
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=True  # Set to False in production — logs all SQL queries
)

# Session factory
# autocommit=False — transactions must be committed explicitly
# autoflush=False  — changes are not flushed until commit or explicit flush
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency that yields a database session.
    Automatically closes the session after the request completes.

    Usage in routers:
        from backend.database import get_db
        from sqlalchemy.orm import Session
        from fastapi import Depends

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
