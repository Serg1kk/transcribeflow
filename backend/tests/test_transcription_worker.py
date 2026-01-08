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
