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
    assert isinstance(data, list)
    assert len(data) > 0

    # Check mlx-whisper is in the list
    engine_names = [e["name"] for e in data]
    assert "mlx-whisper" in engine_names


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
