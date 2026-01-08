# tests/test_api_engines.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_list_engines():
    """Test listing all available engines."""
    response = client.get("/api/engines")

    assert response.status_code == 200
    data = response.json()
    assert "engines" in data
    engines = data["engines"]
    assert isinstance(engines, list)
    assert len(engines) > 0

    # Check mlx-whisper is in the list
    engine_ids = [e["id"] for e in engines]
    assert "mlx-whisper" in engine_ids


def test_list_engines_includes_models(client=client):
    """Engines endpoint should return models for each engine."""
    response = client.get("/api/engines")
    assert response.status_code == 200
    engines = response.json()["engines"]

    # MLX should always be there
    mlx = next((e for e in engines if e["id"] == "mlx-whisper"), None)
    assert mlx is not None
    assert "models" in mlx
    assert "large-v3-turbo" in mlx["models"]


def test_get_engine_capabilities():
    """Test getting capabilities for a specific engine."""
    response = client.get("/api/engines/mlx-whisper/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "mlx-whisper"
    assert "capabilities" in data
    assert data["capabilities"]["supports_initial_prompt"] is True


def test_get_engine_capabilities_not_found():
    """Test 404 for unknown engine."""
    response = client.get("/api/engines/unknown-engine/capabilities")
    assert response.status_code == 404


def test_get_engine_models():
    """Test getting models for a specific engine."""
    response = client.get("/api/engines/mlx-whisper/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert "large-v3-turbo" in models


def test_get_engine_models_not_found():
    """Test 404 for unknown engine models."""
    response = client.get("/api/engines/unknown-engine/models")
    assert response.status_code == 404
