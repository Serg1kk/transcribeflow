"""Settings persistence and key redaction for direct OpenAI."""
from fastapi.testclient import TestClient

from config import clear_settings_cache, get_settings
from main import app


def test_openai_key_saved_but_never_returned(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("api.settings.CONFIG_PATH", config_path)
    monkeypatch.setattr("config.CONFIG_PATH", config_path)
    clear_settings_cache()
    try:
        with TestClient(app) as client:
            initial = client.get("/api/settings").json()
            assert initial["has_openai_key"] is False
            assert initial["features"]["openai_llm"]["status"] == "implemented"

            response = client.put("/api/settings", json={
                "openai_api_key": "test-secret-never-return",
                "postprocessing_provider": "openai",
                "postprocessing_model": "gpt-6-luna",
                "insights_provider": "openai",
                "insights_model": "gpt-6.1-sol",
                "postprocessing_reasoning_effort": "low",
                "insights_reasoning_effort": "high",
            })
            assert response.status_code == 200
            assert response.json()["has_openai_key"] is True
            assert "test-secret-never-return" not in response.text
            assert "openai_api_key" not in response.json()
            assert get_settings().openai_api_key == "test-secret-never-return"
            assert get_settings().postprocessing_model == "gpt-6-luna"
            assert get_settings().insights_model == "gpt-6.1-sol"
            assert response.json()["postprocessing_reasoning_effort"] == "low"
            assert response.json()["insights_reasoning_effort"] == "high"
            assert client.get("/api/settings").json()["has_openai_key"] is True

            # Saving again with the empty key input must preserve the key.
            response = client.put("/api/settings", json={"openai_api_key": ""})
            assert response.json()["has_openai_key"] is True
            assert get_settings().openai_api_key == "test-secret-never-return"
            response = client.put("/api/settings", json={"insights_reasoning_effort": "default"})
            assert response.json()["insights_reasoning_effort"] == "default"
            assert client.put("/api/settings", json={"insights_reasoning_effort": "invalid"}).status_code == 422
    finally:
        clear_settings_cache()
