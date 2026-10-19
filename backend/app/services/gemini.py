from google import genai
from google.genai import errors, types
import httpx

from app.core.config import settings


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
        http_options=types.HttpOptions(timeout=30_000),
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
    except (errors.APIError, httpx.HTTPError, TimeoutError, OSError) as exc:
        raise GeminiRequestError(
            "Gemini tidak dapat memproses permintaan. Periksa model, koneksi, dan kuota API."
        ) from exc

    result = response.text
    if not result or not result.strip():
        raise GeminiRequestError("Gemini mengembalikan respons kosong. Coba ulangi instruksi.")
    return result.strip()[: settings.max_output_length]
