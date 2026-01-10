# tests/test_api_insights.py
"""Tests for AI Insights API endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_list_insight_templates():
    """Test listing insight templates."""
    response = client.get("/api/insights/templates")
    assert response.status_code == 200

    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) >= 6

    template_ids = [t["id"] for t in templates]
    assert "it-meeting" in template_ids


def test_get_insight_template():
    """Test getting a specific insight template."""
    response = client.get("/api/insights/templates/it-meeting")
    assert response.status_code == 200

    template = response.json()
    assert template["id"] == "it-meeting"
    assert template["name"] == "IT Meeting"
    assert template["include_mindmap"] is True
    assert "sections" in template


def test_get_nonexistent_insight_template():
    """Test getting a nonexistent template returns 404."""
    response = client.get("/api/insights/templates/nonexistent")
    assert response.status_code == 404
