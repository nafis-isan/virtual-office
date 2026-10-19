import logging
from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        db.close()
        logger.warning("MySQL is unavailable (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Database belum tersedia. Periksa konfigurasi dan jalankan MySQL.",
        ) from None

    try:
        yield db
    finally:
        db.close()
