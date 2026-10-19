import logging
import math
from collections.abc import Sequence

from google import genai
from google.genai import errors, types
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiUnavailableError(RuntimeError):
    pass


class GeminiRequestError(RuntimeError):
    pass


def generate_text(prompt: str, *, json_response: bool = False) -> str:
    if not settings.gemini_api_key or not settings.gemini_model:
        raise GeminiUnavailableError(
            "Gemini belum dikonfigurasi. Isi GEMINI_API_KEY dan GEMINI_MODEL di backend/.env."
        )

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=120_000),
    )
    generation_options: dict[str, object] = {"max_output_tokens": 2048}
    if json_response:
        generation_options["response_mime_type"] = "application/json"
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(**generation_options),
        )
    except errors.APIError as exc:
        status = getattr(exc, "code", None)
        logger.warning("Gemini request failed: model=%s status=%s", settings.gemini_model, status)
        if status == 404:
            message = (
                f"Model Gemini '{settings.gemini_model}' tidak ditemukan atau tidak tersedia "
                "untuk akun ini. Periksa GEMINI_MODEL di backend/.env."
            )
        elif status in (401, 403):
            message = "Gemini menolak akses. Periksa API key dan izin Gemini API pada akun."
        elif status == 429:
            message = "Kuota atau batas permintaan Gemini tercapai. Periksa kuota API lalu coba lagi."
        else:
            message = f"Gemini API gagal merespons (HTTP {status or 'tidak diketahui'}). Coba lagi nanti."
        raise GeminiRequestError(message) from exc
    except (httpx.HTTPError, TimeoutError, OSError) as exc:
        logger.warning(
            "Gemini connection failed: model=%s error=%s",
            settings.gemini_model,
            type(exc).__name__,
        )
        raise GeminiRequestError(
            "Koneksi ke Gemini gagal atau melewati batas waktu 120 detik. "
            "Periksa koneksi internet dan coba lagi."
        ) from exc

    result = response.text
    if not result or not result.strip():
        raise GeminiRequestError("Gemini mengembalikan respons kosong. Coba ulangi instruksi.")
    return result.strip()[: settings.max_output_length]


def embed_texts(texts: Sequence[str], *, task_type: str) -> list[list[float]]:
    if not settings.gemini_api_key:
        raise GeminiUnavailableError(
            "Gemini belum dikonfigurasi. Isi GEMINI_API_KEY di backend/.env."
        )
    if not texts:
        return []

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=120_000),
    )
    try:
        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=list(texts),
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=768,
            ),
        )
    except errors.APIError as exc:
        status = getattr(exc, "code", None)
        logger.warning(
            "Gemini embedding failed: model=%s status=%s",
            settings.gemini_embedding_model,
            status,
        )
        if status == 404:
            message = (
                f"Model embedding Gemini '{settings.gemini_embedding_model}' tidak ditemukan. "
                "Periksa GEMINI_EMBEDDING_MODEL di backend/.env."
            )
        elif status in (401, 403):
            message = "Gemini menolak akses embedding. Periksa API key dan izin Gemini API."
        elif status == 429:
            message = "Kuota embedding Gemini tercapai. Periksa kuota API lalu coba lagi."
        else:
            message = f"Gemini embedding gagal (HTTP {status or 'tidak diketahui'})."
        raise GeminiRequestError(message) from exc
    except (httpx.HTTPError, TimeoutError, OSError) as exc:
        logger.warning(
            "Gemini embedding connection failed: model=%s error=%s",
            settings.gemini_embedding_model,
            type(exc).__name__,
        )
        raise GeminiRequestError(
            "Koneksi embedding Gemini gagal atau melewati batas waktu 120 detik."
        ) from exc

    embeddings = response.embeddings or []
    vectors = [
        list(embedding.values or [])
        for embedding in embeddings
        if embedding is not None
    ]
    if len(vectors) != len(texts) or any(
        not vector or any(not math.isfinite(value) for value in vector)
        for vector in vectors
    ):
        raise GeminiRequestError("Gemini mengembalikan embedding yang tidak valid.")
    return vectors
