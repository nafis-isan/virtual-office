import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.core.config import settings
from app.db.session import engine

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Visual Office AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/api/health")
def health() -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "connected"
    except SQLAlchemyError:
        database = "disconnected"
    return {
        "status": "ok" if database == "connected" else "degraded",
        "database": database,
        "gemini_configured": bool(settings.gemini_api_key and settings.gemini_model),
    }
