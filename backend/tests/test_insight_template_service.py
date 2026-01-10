# tests/test_insight_template_service.py
"""Tests for insight template service."""
import pytest
from pathlib import Path
from services.insight_template_service import InsightTemplateService, InsightTemplate


def test_insight_template_dataclass():
    """Test InsightTemplate dataclass structure."""
    template = InsightTemplate(
        id="test",
        name="Test Template",
        description="A test template",
        include_mindmap=True,
        sections=[
            {"id": "summary", "title": "Summary", "description": "Brief summary"}
        ],
        system_prompt="You are a test.",
        temperature=0.3
    )
    assert template.id == "test"
    assert template.include_mindmap is True
    assert len(template.sections) == 1


def test_insight_template_service_creates_defaults(tmp_path):
    """Test that default insight templates are created on first access."""
    service = InsightTemplateService(templates_path=tmp_path)
    templates = service.list_templates()

    assert len(templates) >= 6
    template_ids = [t.id for t in templates]
    assert "it-meeting" in template_ids
    assert "sales-call" in template_ids
    assert "business-meeting" in template_ids
    assert "interview" in template_ids
    assert "retrospective" in template_ids
    assert "brainstorm" in template_ids


def test_insight_template_service_get_template(tmp_path):
    """Test getting a specific insight template by ID."""
    service = InsightTemplateService(templates_path=tmp_path)

    template = service.get_template("it-meeting")
    assert template is not None
    assert template.id == "it-meeting"
    assert template.name == "IT Meeting"
    assert template.include_mindmap is True
    assert len(template.sections) >= 4


def test_insight_template_service_get_nonexistent(tmp_path):
    """Test getting a nonexistent template returns None."""
    service = InsightTemplateService(templates_path=tmp_path)

    template = service.get_template("nonexistent")
    assert template is None
