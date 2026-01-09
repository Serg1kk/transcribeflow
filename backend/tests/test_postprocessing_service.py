# tests/test_postprocessing_service.py
"""Tests for post-processing service."""
import pytest
from pathlib import Path
from services.postprocessing_service import PostProcessingService, format_transcript_for_llm


def test_format_transcript_for_llm():
    """Test transcript formatting for LLM input."""
    segments = [
        {"start": 0.0, "speaker": "SPEAKER_01", "text": "Hello"},
        {"start": 1.0, "speaker": "SPEAKER_02", "text": "Hi there"},
    ]

    result = format_transcript_for_llm(segments)

    assert "[00:00:00]" in result
    assert "SPEAKER_01" in result
    assert "Hello" in result


def test_postprocessing_service_exists():
    """Test PostProcessingService can be instantiated."""
    service = PostProcessingService()
    assert service is not None
