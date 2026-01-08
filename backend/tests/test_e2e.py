# tests/test_e2e.py
"""End-to-end tests for the transcription workflow."""
import pytest
from io import BytesIO
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_full_transcription_workflow():
    """Test the complete workflow from upload to transcript retrieval."""
    # Step 1: Upload a file (now creates DRAFT status)
    fake_audio = BytesIO(b"fake audio content for e2e test")

    upload_response = client.post(
        "/api/transcribe/upload",
        files={"file": ("e2e_test.mp3", fake_audio, "audio/mpeg")},
        data={"engine": "mlx-whisper", "model": "large-v2"},
    )

    assert upload_response.status_code == 201
    data = upload_response.json()
    transcription_id = data["id"]
    assert data["status"] == "draft"  # Changed from "queued" for DRAFT workflow

    # Step 2: Check it appears in the queue
    queue_response = client.get("/api/transcribe/queue")
    assert queue_response.status_code == 200
    queue = queue_response.json()
    assert any(t["id"] == transcription_id for t in queue)

    # Step 3: Get single transcription status
    status_response = client.get(f"/api/transcribe/{transcription_id}")
    assert status_response.status_code == 200
    assert status_response.json()["id"] == transcription_id

    # Step 4: Start the transcription (move from DRAFT to QUEUED)
    start_response = client.post(
        "/api/transcribe/start",
        json={"ids": [transcription_id]}
    )
    assert start_response.status_code == 200
    assert start_response.json()["started"] == 1

    # Step 5: Verify status changed to queued
    status_response = client.get(f"/api/transcribe/{transcription_id}")
    assert status_response.json()["status"] == "queued"


def test_settings_endpoint():
    """Test settings endpoint returns expected structure."""
    response = client.get("/api/settings")
    assert response.status_code == 200

    data = response.json()
    assert "default_engine" in data
    assert "default_model" in data
    assert "diarization_method" in data
    assert "compute_device" in data
    assert "min_speakers" in data
    assert "max_speakers" in data
    assert "has_hf_token" in data
    assert "has_assemblyai_key" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_multiple_files():
    """Test uploading multiple files creates separate transcription tasks."""
    files_uploaded = []

    for i in range(3):
        fake_audio = BytesIO(f"fake audio content {i}".encode())
        response = client.post(
            "/api/transcribe/upload",
            files={"file": (f"multi_test_{i}.mp3", fake_audio, "audio/mpeg")},
        )
        assert response.status_code == 201
        files_uploaded.append(response.json()["id"])

    # Check all appear in queue
    queue_response = client.get("/api/transcribe/queue")
    queue_ids = [t["id"] for t in queue_response.json()]

    for file_id in files_uploaded:
        assert file_id in queue_ids


def test_nonexistent_transcript_returns_404():
    """Test that requesting transcript for non-completed task returns 404."""
    # First upload a file (it will be queued, not completed)
    fake_audio = BytesIO(b"fake audio")
    upload_response = client.post(
        "/api/transcribe/upload",
        files={"file": ("transcript_test.mp3", fake_audio, "audio/mpeg")},
    )
    transcription_id = upload_response.json()["id"]

    # Try to get transcript (should fail since not processed)
    transcript_response = client.get(f"/api/transcribe/{transcription_id}/transcript")
    assert transcript_response.status_code == 404


def test_invalid_file_extension_rejected():
    """Test that non-audio files are rejected."""
    fake_file = BytesIO(b"not audio")

    response = client.post(
        "/api/transcribe/upload",
        files={"file": ("test.txt", fake_file, "text/plain")},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_queue_ordering():
    """Test that queue returns items in descending order by creation time."""
    # Upload several files
    for i in range(3):
        fake_audio = BytesIO(f"ordering test {i}".encode())
        client.post(
            "/api/transcribe/upload",
            files={"file": (f"order_test_{i}.mp3", fake_audio, "audio/mpeg")},
        )

    # Get queue
    response = client.get("/api/transcribe/queue")
    queue = response.json()

    # Verify ordering (newest first)
    if len(queue) >= 2:
        for i in range(len(queue) - 1):
            assert queue[i]["created_at"] >= queue[i + 1]["created_at"]
