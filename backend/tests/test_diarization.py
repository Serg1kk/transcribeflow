# tests/test_diarization.py
import pytest
from workers.diarization import DiarizationWorker, DiarizationResult


def test_diarization_result_structure():
    """Test diarization result has correct structure."""
    result = DiarizationResult(
        speakers={"SPEAKER_00", "SPEAKER_01"},
        segments=[
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
    )
    assert len(result.speakers) == 2
    assert len(result.segments) == 2


def test_diarization_worker_interface():
    """Test diarization worker has required methods."""
    worker = DiarizationWorker(hf_token=None)
    assert hasattr(worker, "diarize")
    assert hasattr(worker, "is_available")


def test_merge_transcription_with_diarization():
    """Test merging ASR segments with speaker labels."""
    worker = DiarizationWorker(hf_token=None)

    transcription_segments = [
        {"start": 0.0, "end": 3.0, "text": "Hello there"},
        {"start": 3.5, "end": 6.0, "text": "How are you"},
        {"start": 6.5, "end": 9.0, "text": "I'm fine thanks"},
    ]

    diarization_result = DiarizationResult(
        speakers={"SPEAKER_00", "SPEAKER_01"},
        segments=[
            {"start": 0.0, "end": 3.2, "speaker": "SPEAKER_00"},
            {"start": 3.2, "end": 6.5, "speaker": "SPEAKER_01"},
            {"start": 6.5, "end": 10.0, "speaker": "SPEAKER_00"},
        ]
    )

    merged = worker.merge_transcription_with_diarization(
        transcription_segments, diarization_result
    )

    assert len(merged) == 3
    assert merged[0]["speaker"] == "SPEAKER_00"
    assert merged[1]["speaker"] == "SPEAKER_01"
    assert merged[2]["speaker"] == "SPEAKER_00"


def test_diarization_worker_accepts_device():
    """Test diarization worker accepts device parameter."""
    worker = DiarizationWorker(hf_token=None, device="cpu")
    assert worker.device == "cpu"


def test_diarization_worker_default_device():
    """Test diarization worker defaults to 'auto' device."""
    worker = DiarizationWorker(hf_token=None)
    assert worker.device == "auto"


def test_diarization_worker_resolve_device_auto():
    """Test _resolve_device returns valid torch device for 'auto'."""
    worker = DiarizationWorker(hf_token=None, device="auto")
    device = worker._resolve_device()
    assert device in ["cpu", "mps"]


def test_diarization_worker_resolve_device_cpu():
    """Test _resolve_device returns 'cpu' when set to 'cpu'."""
    worker = DiarizationWorker(hf_token=None, device="cpu")
    assert worker._resolve_device() == "cpu"
