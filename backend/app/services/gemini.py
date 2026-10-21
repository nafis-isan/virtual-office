import json
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


def generate_text(
    prompt: str,
    *,
    json_response: bool = False,
    model_override: str | None = None,
) -> str:
    if settings.ai_provider == "openrouter":
        return _generate_text_openrouter(
            prompt,
            json_response=json_response,
            model_override=model_override,
        )
    if model_override is not None:
        raise GeminiUnavailableError("Pemilihan model khusus hanya tersedia untuk OpenRouter.")
    if settings.ai_provider != "gemini":
        raise GeminiUnavailableError(
            "AI_PROVIDER tidak dikenal. Gunakan 'gemini' atau 'openrouter' di backend/.env."
        )
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


def _generate_text_openrouter(
    prompt: str,
    *,
    json_response: bool,
    model_override: str | None = None,
) -> str:
    model = model_override or settings.openrouter_model
    if not settings.openrouter_api_key or not model:
        raise GeminiUnavailableError(
            "OpenRouter belum dikonfigurasi. Isi OPENROUTER_API_KEY dan "
            "OPENROUTER_MODEL di backend/.env."
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "X-Title": "NF Office",
        "HTTP-Referer": "http://localhost:3000",
    }
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "reasoning": {"enabled": settings.openrouter_reasoning_enabled},
    }
    if json_response:
        payload["response_format"] = {"type": "json_object"}
    initial_payload = payload.copy()

    def request_completion(request_payload: dict[str, object]) -> dict:
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=request_payload,
                timeout=120.0,
            )
        except (httpx.HTTPError, TimeoutError, OSError) as exc:
            logger.warning(
                "OpenRouter connection failed: model=%s error=%s",
                model,
                type(exc).__name__,
            )
            raise GeminiRequestError(
                "Koneksi ke OpenRouter gagal atau melewati batas waktu 120 detik. "
                "Periksa koneksi internet dan coba lagi."
            ) from exc

        if response.is_error:
            status = response.status_code
            logger.warning(
                "OpenRouter request failed: model=%s status=%s",
                model,
                status,
            )
            if status in (401, 403):
                message = "OpenRouter menolak akses. Periksa OPENROUTER_API_KEY."
            elif status == 402:
                message = "Saldo atau kredit OpenRouter tidak mencukupi."
            elif status == 404:
                message = (
                    f"Model OpenRouter '{model}' tidak ditemukan. "
                    "Periksa konfigurasi model OpenRouter di backend/.env."
                )
            elif status == 400:
                try:
                    error_data = response.json()
                except json.JSONDecodeError:
                    error_data = {}
                error = error_data.get("error") if isinstance(error_data, dict) else None
                provider_message = error.get("message") if isinstance(error, dict) else None
                if isinstance(provider_message, str) and provider_message.strip():
                    detail = " ".join(provider_message.split())[:300]
                    message = (
                        f"OpenRouter menolak format permintaan (HTTP 400): {detail}"
                    )
                else:
                    message = (
                        "OpenRouter menolak format permintaan (HTTP 400). "
                        "Periksa model dan parameter permintaan."
                    )
            elif status == 429:
                message = "Batas permintaan OpenRouter tercapai. Periksa limit akun lalu coba lagi."
            else:
                message = f"OpenRouter gagal merespons (HTTP {status}). Coba lagi nanti."
            raise GeminiRequestError(message)

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise GeminiRequestError("OpenRouter mengembalikan respons yang tidak valid.") from exc

    def get_assistant_message(data: dict) -> dict:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiRequestError("OpenRouter mengembalikan respons yang tidak valid.") from exc
        if not isinstance(message, dict):
            raise GeminiRequestError("OpenRouter mengembalikan respons yang tidak valid.")
        return message

    def get_finish_reason(data: dict) -> str | None:
        try:
            choice = data["choices"][0]
        except (KeyError, IndexError, TypeError):
            return None
        if not isinstance(choice, dict):
            return None
        finish_reason = choice.get("finish_reason")
        return finish_reason if isinstance(finish_reason, str) else None

    def get_text_content(content: object) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "".join(
                part["text"]
                for part in content
                if isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ).strip()
        return ""

    completion = request_completion(payload)
    message = get_assistant_message(completion)
    result = get_text_content(message.get("content"))
    reasoning_details = message.get("reasoning_details")
    reasoning = message.get("reasoning")
    if not result and (reasoning_details or reasoning):
        assistant_message = {"role": "assistant", "content": message.get("content")}
        if reasoning_details:
            assistant_message["reasoning_details"] = reasoning_details
        if reasoning:
            assistant_message["reasoning"] = reasoning
        continuation_payload = {
            **payload,
            "messages": [
                {"role": "user", "content": prompt},
                assistant_message,
                {
                    "role": "user",
                    "content": (
                        "Lanjutkan dari respons sebelumnya dan berikan jawaban akhir. "
                        "Jangan tampilkan proses reasoning. Ikuti format output yang diminta."
                    ),
                },
            ],
        }
        completion = request_completion(continuation_payload)
        message = get_assistant_message(completion)
        result = get_text_content(message.get("content"))

    if not result:
        retry_payload = {
            **initial_payload,
            "reasoning": {"enabled": False},
        }
        completion = request_completion(retry_payload)
        message = get_assistant_message(completion)
        result = get_text_content(message.get("content"))

    if not result:
        finish_reason = get_finish_reason(completion)
        logger.warning(
            "OpenRouter returned empty completion after retry: model=%s finish_reason=%s",
            model,
            finish_reason,
        )
        raise GeminiRequestError(
            "OpenRouter tetap mengembalikan respons kosong setelah dicoba ulang tanpa "
            "reasoning. Periksa ketersediaan model OpenRouter atau coba ulangi instruksi."
        )
    return result[: settings.max_output_length]


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
