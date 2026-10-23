from types import SimpleNamespace

from app import main
from app.services import gemini


def test_health_reports_effective_model_and_configuration_error(monkeypatch):
    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query):
            return None

    monkeypatch.setattr(main, "engine", SimpleNamespace(connect=Connection))
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(
        gemini.settings,
        "openrouter_model",
        "minimax/minimax-m3.1-flash:free",
    )
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")

    response = main.health()

    assert response["status"] == "degraded"
    assert response["database"] == "connected"
    assert response["ai_model"] == "minimax/minimax-m3.1-flash:free"
    assert response["ai_configured"] is False
    assert "environment proses" in response["ai_configuration_error"]
    assert "test-key" not in str(response)
