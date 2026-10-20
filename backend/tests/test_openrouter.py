from copy import deepcopy

import httpx
import pytest

from app.services import gemini


def test_generate_text_uses_openrouter_and_json_response(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "minimax/minimax-m3.1-flash:free"
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
    assert captured["json"]["max_tokens"] == 8192
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["reasoning"] == {"enabled": True}


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


def test_openrouter_requires_api_key(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "")
    monkeypatch.setattr(gemini.settings, "openrouter_model", "model-id")

    with pytest.raises(gemini.GeminiUnavailableError, match="OPENROUTER_API_KEY"):
        gemini.generate_text("prompt")
