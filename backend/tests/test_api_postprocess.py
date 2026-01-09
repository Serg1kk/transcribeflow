# tests/test_api_postprocess.py
"""Tests for post-processing API endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_list_templates():
    """Test listing available templates."""
    response = client.get("/api/postprocess/templates")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check template structure
    template = data[0]
    assert "id" in template
    assert "name" in template
    assert "description" in template
    assert "temperature" in template


def test_get_template():
    """Test getting a specific template."""
    response = client.get("/api/postprocess/templates/it-meeting")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "it-meeting"
    assert data["name"] == "IT Meeting"


def test_get_nonexistent_template():
    """Test 404 for nonexistent template."""
    response = client.get("/api/postprocess/templates/nonexistent")
    assert response.status_code == 404


def test_list_llm_models():
    """Test listing LLM models."""
    response = client.get("/api/postprocess/models")

    assert response.status_code == 200
    data = response.json()
    assert "gemini" in data
    assert "openrouter" in data
    assert len(data["gemini"]["models"]) >= 3
