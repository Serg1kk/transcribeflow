# tests/test_template_service.py
"""Tests for template service."""
import pytest
import json
from pathlib import Path
from services.template_service import TemplateService, Template


def test_template_service_creates_default_templates(tmp_path):
    """Test that default templates are created on first access."""
    service = TemplateService(templates_path=tmp_path)
    templates = service.list_templates()

    assert len(templates) >= 3
    template_ids = [t.id for t in templates]
    assert "it-meeting" in template_ids
    assert "interview" in template_ids
    assert "business-call" in template_ids


def test_template_service_get_template(tmp_path):
    """Test getting a specific template by ID."""
    service = TemplateService(templates_path=tmp_path)

    template = service.get_template("it-meeting")
    assert template is not None
    assert template.id == "it-meeting"
    assert template.name == "IT Meeting"
    assert template.temperature == 0.2


def test_template_service_get_nonexistent_template(tmp_path):
    """Test getting a nonexistent template returns None."""
    service = TemplateService(templates_path=tmp_path)

    template = service.get_template("nonexistent")
    assert template is None


def test_template_dataclass():
    """Test Template dataclass structure."""
    template = Template(
        id="test",
        name="Test Template",
        description="A test template",
        system_prompt="You are a test.",
        temperature=0.5
    )
    assert template.id == "test"
    assert template.temperature == 0.5
