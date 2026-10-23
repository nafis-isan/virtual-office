import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.core.config import settings
from app.db.session import engine
from app.services.gemini import generation_configuration_error

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Visual Office AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
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
    ai_error = generation_configuration_error()
    ai_model = (
        settings.openrouter_model
        if settings.ai_provider == "openrouter"
        else settings.gemini_model
        if settings.ai_provider == "gemini"
        else ""
    )
    return {
        "status": "ok" if database == "connected" and ai_error is None else "degraded",
        "database": database,
        "ai_provider": settings.ai_provider,
        "ai_model": ai_model,
        "ai_configured": ai_error is None,
        "ai_configuration_error": ai_error,
        "gemini_configured": bool(settings.gemini_api_key and settings.gemini_model),
        "gemini_embedding_configured": bool(settings.gemini_api_key),
        "rag_mode": (
            "keyword_local"
            if settings.ai_provider == "openrouter"
            else "gemini_embeddings"
            if settings.ai_provider == "gemini"
            else "unavailable"
        ),
    }
