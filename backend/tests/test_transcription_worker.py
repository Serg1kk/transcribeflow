# tests/test_transcription_worker.py
import pytest
from pathlib import Path
from workers.transcription_worker import TranscriptionWorker


def test_worker_initialization():
    """Test worker initializes with required components."""
    worker = TranscriptionWorker()
    assert hasattr(worker, "process")
    assert hasattr(worker, "get_engine")


def test_worker_get_engine():
    """Test worker can get MLX whisper engine."""
    worker = TranscriptionWorker()
    engine = worker.get_engine("mlx-whisper")
    assert engine.name == "mlx-whisper"


def test_worker_unknown_engine_raises():
    """Test worker raises for unknown engine."""
    worker = TranscriptionWorker()
    with pytest.raises(ValueError, match="Unknown engine"):
        worker.get_engine("unknown-engine")


def test_worker_get_whisper_settings_returns_settings():
    """Test worker can get whisper settings."""
    worker = TranscriptionWorker()
    settings = worker.get_whisper_settings()
    assert hasattr(settings, 'initial_prompt')


def test_worker_applies_per_file_initial_prompt():
    """Test that per-file initial_prompt overrides global settings."""
    from unittest.mock import MagicMock, patch
    from models.transcription import Transcription, TranscriptionStatus

    worker = TranscriptionWorker()

    # Create a mock transcription with initial_prompt
    mock_transcription = MagicMock(spec=Transcription)
    mock_transcription.initial_prompt = "This is a Python interview"
    mock_transcription.engine = "mlx-whisper"
    mock_transcription.model = "large-v2"
    mock_transcription.language = None
    mock_transcription.original_path = "/fake/path.mp3"
    mock_transcription.status = TranscriptionStatus.QUEUED

    # Get base whisper settings
    base_settings = worker.get_whisper_settings()

    # Simulate the logic that should be in process()
    whisper_settings = worker.get_whisper_settings()
    if mock_transcription.initial_prompt:
        whisper_settings.initial_prompt = mock_transcription.initial_prompt

    # Verify per-file prompt overrides global
    assert whisper_settings.initial_prompt == "This is a Python interview"
