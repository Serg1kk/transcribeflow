"""Settings persistence and key redaction for direct LLM providers."""
import pytest
from fastapi.testclient import TestClient

from config import clear_settings_cache, get_settings
from main import app


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_provider_key_saved_but_never_returned(tmp_path, monkeypatch, provider):
    cleanup_model = "gpt-6-luna" if provider == "openai" else "claude-haiku-5-5"
    insights_model = "gpt-6.1-sol" if provider == "openai" else "claude-sonnet-5-5"
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("api.settings.CONFIG_PATH", config_path)
    monkeypatch.setattr("config.CONFIG_PATH", config_path)
    clear_settings_cache()
    try:
        with TestClient(app) as client:
            initial = client.get("/api/settings").json()
            assert initial[f"has_{provider}_key"] is False
            assert initial["features"][f"{provider}_llm"]["status"] == "implemented"

            response = client.put("/api/settings", json={
                f"{provider}_api_key": "test-secret-never-return",
                "postprocessing_provider": provider,
                "postprocessing_model": cleanup_model,
                "insights_provider": provider,
                "insights_model": insights_model,
                "postprocessing_reasoning_effort": "low",
                "insights_reasoning_effort": "high",
            })
            assert response.status_code == 200
            assert response.json()[f"has_{provider}_key"] is True
            assert "test-secret-never-return" not in response.text
            assert f"{provider}_api_key" not in response.json()
            assert getattr(get_settings(), f"{provider}_api_key") == "test-secret-never-return"
            assert get_settings().postprocessing_model == cleanup_model
            assert get_settings().insights_model == insights_model
            assert response.json()["postprocessing_reasoning_effort"] == "low"
            assert response.json()["insights_reasoning_effort"] == "high"
            assert client.get("/api/settings").json()[f"has_{provider}_key"] is True

            # Saving again with the empty key input must preserve the key.
            response = client.put("/api/settings", json={f"{provider}_api_key": ""})
            assert response.json()[f"has_{provider}_key"] is True
            assert getattr(get_settings(), f"{provider}_api_key") == "test-secret-never-return"
            response = client.put("/api/settings", json={"insights_reasoning_effort": "default"})
            assert response.json()["insights_reasoning_effort"] == "default"
            assert client.put("/api/settings", json={"insights_reasoning_effort": "invalid"}).status_code == 422
    finally:
        clear_settings_cache()
