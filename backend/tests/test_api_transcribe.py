# tests/test_api_transcribe.py
import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from main import app


client = TestClient(app)


def test_upload_audio_file():
    """Test uploading an audio file creates a transcription task."""
    # Create a fake audio file
    fake_audio = BytesIO(b"fake audio content")
    fake_audio.name = "test_meeting.mp3"

    response = client.post(
        "/api/transcribe/upload",
        files={"file": ("test_meeting.mp3", fake_audio, "audio/mpeg")},
        data={
            "engine": "mlx-whisper",
            "model": "large-v2",
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_meeting.mp3"
    assert data["status"] == "queued"


def test_upload_invalid_file_type():
    """Test that invalid file types are rejected."""
    fake_file = BytesIO(b"not an audio file")

    response = client.post(
        "/api/transcribe/upload",
        files={"file": ("document.pdf", fake_file, "application/pdf")},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_list_transcriptions_queue():
    """Test listing all transcriptions in queue."""
    response = client.get("/api/transcribe/queue")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_transcription_by_id():
    """Test getting a specific transcription by ID."""
    # First upload a file
    fake_audio = BytesIO(b"fake audio content")
    upload_response = client.post(
        "/api/transcribe/upload",
        files={"file": ("get_test.mp3", fake_audio, "audio/mpeg")},
    )
    transcription_id = upload_response.json()["id"]

    # Then fetch it
    response = client.get(f"/api/transcribe/{transcription_id}")

    assert response.status_code == 200
    assert response.json()["id"] == transcription_id


def test_get_nonexistent_transcription():
    """Test 404 for nonexistent transcription."""
    response = client.get("/api/transcribe/nonexistent-id")
    assert response.status_code == 404
