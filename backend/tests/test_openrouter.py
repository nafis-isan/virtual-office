from copy import deepcopy

import httpx
import pytest

from app.core.config import Settings
from app.services import gemini


def test_generate_text_uses_openrouter_and_json_response(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "supported/model-id"
    )
    monkeypatch.setattr(gemini.settings, "openrouter_reasoning_enabled", True)
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    assert gemini.generate_text("prompt", json_response=True) == '{"ok":true}'
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "supported/model-id"
    assert captured["json"]["max_tokens"] == 8192
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["reasoning"] == {"enabled": True}


def test_openrouter_defaults_to_the_nvidia_nemotron_model(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        ai_provider="openrouter",
        openrouter_api_key="test-key",
    )

    assert settings.openrouter_model == "nvidia/nemotron-3.5-super-vl:free"
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"


def test_openrouter_rejects_a_legacy_minimax_process_override(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings,
        "openrouter_model",
        "minimax/minimax-m3.1-flash:free",
    )

    with pytest.raises(gemini.GeminiUnavailableError, match="environment proses"):
        gemini.validate_generation_configuration()


def test_openrouter_rejects_non_openrouter_base_url(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "nvidia/nemotron-3.5-super-vl:free"
    )
    monkeypatch.setattr(
        gemini.settings, "openrouter_base_url", "https://attacker.example/api/v1"
    )

    with pytest.raises(gemini.GeminiUnavailableError, match="OPENROUTER_BASE_URL"):
        gemini.validate_generation_configuration()


def test_generate_text_uses_the_configured_model_for_every_agent(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "nvidia/nemotron-3.5-super-vl:free"
    )
    captured = {}

    def fake_post(_url, **kwargs):
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Desain UI/UX."}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    result = gemini.generate_text("prompt")

    assert result == "Desain UI/UX."
    assert captured["json"]["model"] == "nvidia/nemotron-3.5-super-vl:free"
    assert captured["json"]["reasoning"] == {"enabled": True}


def test_generate_text_uses_json_mode_for_nvidia_nemotron_free_model(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "nvidia/nemotron-3.5-super-vl:free"
    )
    captured = {}

    def fake_post(_url, **kwargs):
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    assert gemini.generate_text("prompt", json_response=True) == '{"ok":true}'
    assert captured["json"]["model"] == "nvidia/nemotron-3.5-super-vl:free"
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_generate_text_continues_reasoning_when_first_response_has_no_answer(
    monkeypatch,
):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    reasoning_details = [{"type": "reasoning.test", "data": "opaque"}]
    requests = []

    def fake_post(_url, **kwargs):
        requests.append(deepcopy(kwargs["json"]))
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "reasoning_details": reasoning_details,
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Jawaban akhir."}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    assert gemini.generate_text("prompt") == "Jawaban akhir."
    assert len(requests) == 2
    assert requests[1]["messages"][1]["reasoning_details"] == reasoning_details
    assert "reasoning" not in requests[1]["messages"][1]
    assert "Jangan tampilkan proses reasoning" in requests[1]["messages"][2]["content"]


def test_generate_text_continues_legacy_reasoning_field(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    requests = []

    def fake_post(_url, **kwargs):
        requests.append(deepcopy(kwargs["json"]))
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "reasoning": "opaque reasoning",
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Jawaban akhir."}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    assert gemini.generate_text("prompt") == "Jawaban akhir."
    assert requests[1]["messages"][1]["reasoning"] == "opaque reasoning"


def test_generate_text_retries_empty_response_without_reasoning(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    requests = []

    def fake_post(_url, **kwargs):
        requests.append(deepcopy(kwargs["json"]))
        content = None if len(requests) == 1 else '{"ok":true}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(gemini.httpx, "post", fake_post)

    assert gemini.generate_text("prompt", json_response=True) == '{"ok":true}'
    assert len(requests) == 2
    assert requests[1]["reasoning"] == {"enabled": False}
    assert requests[1]["response_format"] == {"type": "json_object"}


def test_generate_text_reports_when_retry_is_still_empty(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    monkeypatch.setattr(
        gemini.httpx,
        "post",
        lambda *_args, **_kwargs: httpx.Response(
            200,
            json={"choices": [{"message": {"content": None}, "finish_reason": "length"}]},
        ),
    )

    with pytest.raises(gemini.GeminiRequestError, match="dicoba ulang tanpa reasoning"):
        gemini.generate_text("prompt")


def test_generate_text_reads_text_blocks_from_openrouter_content(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    monkeypatch.setattr(
        gemini.httpx,
        "post",
        lambda *_args, **_kwargs: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "Bagian satu."},
                                {"type": "image", "data": "ignored"},
                                {"type": "text", "text": " Bagian dua."},
                            ]
                        }
                    }
                ]
            },
        ),
    )

    assert gemini.generate_text("prompt") == "Bagian satu. Bagian dua."


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "OpenRouter menolak akses"),
        (402, "Saldo atau kredit OpenRouter"),
        (404, "Model OpenRouter"),
        (429, "Batas permintaan OpenRouter"),
    ],
)
def test_generate_text_reports_openrouter_http_errors(monkeypatch, status, message):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    monkeypatch.setattr(
        gemini.httpx,
        "post",
        lambda *_args, **_kwargs: httpx.Response(status, json={"error": "details"}),
    )

    with pytest.raises(gemini.GeminiRequestError, match=message):
        gemini.generate_text("prompt")


def test_generate_text_sanitizes_openrouter_bad_request_detail(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")
    monkeypatch.setattr(
        gemini.httpx,
        "post",
        lambda *_args, **_kwargs: httpx.Response(
            400,
            json={"error": {"message": "reasoning parameter is not supported"}},
        ),
    )

    with pytest.raises(
        gemini.GeminiRequestError,
        match="dukungan parameter",
    ) as error:
        gemini.generate_text("prompt")
    assert "reasoning parameter is not supported" not in str(error.value)


@pytest.mark.parametrize(
    "unsupported_parameter",
    ["reasoning", "response_format", "max_tokens"],
)
def test_generate_text_retries_http_400_without_optional_parameter(
    monkeypatch,
    unsupported_parameter,
):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "supported/model-id")
    requests = []

    def fake_post(_url, **kwargs):
        payload = kwargs["json"]
        requests.append(payload.copy())
        if unsupported_parameter == "reasoning" and "reasoning" in payload:
            return httpx.Response(400, json={"error": "unsupported parameter"})
        if unsupported_parameter == "response_format" and "response_format" in payload:
            return httpx.Response(400, json={"error": "unsupported parameter"})
        if unsupported_parameter == "max_tokens" and payload["max_tokens"] > 4096:
            return httpx.Response(400, json={"error": "limit too high"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    monkeypatch.setattr(gemini.httpx, "post", fake_post)
    monkeypatch.setattr(gemini.settings, "openrouter_reasoning_enabled", True)

    result = gemini.generate_text("prompt", json_response=True)

    assert result == '{"ok":true}'
    assert len(requests) > 1
    if unsupported_parameter == "reasoning":
        assert "reasoning" not in requests[-1]
    elif unsupported_parameter == "response_format":
        assert "response_format" not in requests[-1]
    else:
        assert requests[-1]["max_tokens"] == 4096


def test_openrouter_requires_api_key(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")

    with pytest.raises(gemini.GeminiUnavailableError, match="OPENROUTER_API_KEY"):
        gemini.generate_text("prompt")
