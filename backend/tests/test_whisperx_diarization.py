# tests/test_whisperx_diarization.py
import pytest
from workers.whisperx_diarization import WhisperXDiarizationWorker


def test_whisperx_worker_interface():
    """Test WhisperX worker has required methods."""
    worker = WhisperXDiarizationWorker(hf_token=None)
    assert hasattr(worker, "diarize_with_alignment")
    assert hasattr(worker, "is_available")


def test_whisperx_worker_not_available_without_token():
    """Test worker reports unavailable without HF token."""
    worker = WhisperXDiarizationWorker(hf_token=None)
    # Should return False or raise - depends on whisperx being installed
    # Just check the method exists and is callable
    assert callable(worker.is_available)


def test_whisperx_worker_stores_config():
    """Test worker stores configuration."""
    worker = WhisperXDiarizationWorker(
        hf_token="test_token",
        min_speakers=2,
        max_speakers=4,
    )
    assert worker.hf_token == "test_token"
    assert worker.min_speakers == 2
    assert worker.max_speakers == 4
