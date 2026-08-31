"""
Database engine, session factory, and declarative base.

Uses PostgreSQL in production (set DATABASE_URL), SQLite for local/demo
(PRD Section 6). No frontend code or route ever touches this module
directly - only services/models do, keeping the DB an implementation
detail behind the documented REST API (PRD Section 5).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config.settings import settings

connect_args = {}
engine_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    # Needed for SQLite when used with FastAPI's threaded request handling.
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL (and other real DB servers) in production: verify a
    # connection is still alive before handing it to a request (avoids
    # "server closed the connection unexpectedly" after idle periods) and
    # recycle connections periodically so a restarted/rebalanced DB server
    # doesn't leave the pool holding stale sockets.
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,  # 30 min
    }

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
