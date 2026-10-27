"""SQLAlchemy engine and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings


engine = (
    create_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)
SessionLocal = (
    sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    if engine is not None
    else None
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after the request completes."""

    if SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL is not configured; database access is unavailable."
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
