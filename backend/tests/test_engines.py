# tests/test_engines.py
import pytest
from engines.base import TranscriptionEngine, TranscriptionResult
from engines.mlx_whisper import MLXWhisperEngine


def test_mlx_engine_implements_interface():
    """Test MLX engine implements the base interface."""
    engine = MLXWhisperEngine()
    assert isinstance(engine, TranscriptionEngine)
    assert hasattr(engine, "transcribe")
    assert hasattr(engine, "is_available")


def test_mlx_engine_result_structure():
    """Test transcription result has correct structure."""
    result = TranscriptionResult(
        text="Hello world",
        segments=[
            {"start": 0.0, "end": 1.5, "text": "Hello world", "confidence": 0.95}
        ],
        language="en",
        duration_seconds=1.5,
    )
    assert result.text == "Hello world"
    assert len(result.segments) == 1
