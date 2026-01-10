# tests/test_insight_service.py
"""Tests for insight service."""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from services.insight_service import InsightService, InsightResult


def test_insight_result_dataclass():
    """Test InsightResult dataclass structure."""
    result = InsightResult(
        description="Test meeting summary",
        sections=[{"id": "test", "title": "Test", "content": "Content"}],
        mindmap={"format": "markdown", "content": "# Topic"},
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
        processing_time_seconds=2.5
    )
    assert result.description == "Test meeting summary"
    assert result.mindmap is not None


def test_insight_result_without_mindmap():
    """Test InsightResult without mindmap."""
    result = InsightResult(
        description="Test",
        sections=[],
        mindmap=None,
        input_tokens=100,
        output_tokens=50,
        cost_usd=None,
        processing_time_seconds=1.0
    )
    assert result.mindmap is None


@pytest.fixture
def mock_transcript_data():
    """Create mock transcript data."""
    return {
        "metadata": {"id": "test-123", "filename": "test.mp3"},
        "speakers": {"SPEAKER_00": {"name": "Speaker 1", "color": "#000"}},
        "segments": [
            {"start": 0.0, "speaker": "SPEAKER_00", "text": "Hello, let's discuss the project."}
        ]
    }


def test_format_transcript_for_insights(mock_transcript_data):
    """Test formatting transcript for insights extraction."""
    service = InsightService()
    formatted = service._format_transcript(mock_transcript_data["segments"])

    assert "[00:00:00]" in formatted
    assert "SPEAKER_00" in formatted
    assert "Hello, let's discuss" in formatted
