# tests/test_elevenlabs.py
"""Tests for ElevenLabs Scribe engine."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from engines.elevenlabs import ElevenLabsEngine
from engines.base import TranscriptionEngine


def test_elevenlabs_implements_interface():
    """ElevenLabs engine must implement TranscriptionEngine."""
    engine = ElevenLabsEngine(api_key="test-key")
    assert isinstance(engine, TranscriptionEngine)


def test_elevenlabs_is_available_with_key():
    """Engine is available when API key is provided."""
    engine = ElevenLabsEngine(api_key="test-key")
    assert engine.is_available() is True


def test_elevenlabs_not_available_without_key():
    """Engine is not available without API key."""
    engine = ElevenLabsEngine(api_key=None)
    assert engine.is_available() is False


def test_elevenlabs_name():
    """Engine name should be 'elevenlabs'."""
    engine = ElevenLabsEngine(api_key="test")
    assert engine.name == "elevenlabs"


def test_elevenlabs_supported_models():
    """Engine should expose only Scribe v2 in the product now."""
    assert ElevenLabsEngine.SUPPORTED_MODELS == ("scribe_v2",)


def test_elevenlabs_rejects_unknown_model(tmp_path):
    """Unknown model IDs should fail fast before hitting the API."""
    engine = ElevenLabsEngine(api_key="test-key")
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake-audio")

    with pytest.raises(ValueError, match="Unsupported ElevenLabs model"):
        engine.transcribe(audio_path, model="scribe_v999")


def test_elevenlabs_audio_event_flag_and_advanced_options(tmp_path):
    """Scribe v2 should send advanced payload fields and alias legacy v1 to v2."""
    engine = ElevenLabsEngine(api_key="test-key")
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake-audio")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": "hello", "words": [], "language_code": "en"}

    recorded_payloads = []
    mock_instance = AsyncMock()

    async def post(*args, **kwargs):
        recorded_payloads.append(kwargs["data"])
        return mock_response

    mock_instance.post = AsyncMock(side_effect=post)

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        engine.transcribe(
            audio_path,
            model="scribe_v1",
            keyterms=["ProdSignal", "TranscribeFlow"],
            entity_detection=["pii"],
            entity_redaction=["name"],
            entity_redaction_mode="entity_type",
        )

    payload = recorded_payloads[0]
    assert payload["model_id"] == "scribe_v2"
    assert payload["tag_audio_events"] == "true"
    assert payload["keyterms"] == ["ProdSignal", "TranscribeFlow"]
    assert payload["entity_detection"] == ["pii"]
    assert payload["entity_redaction"] == ["name"]
    assert payload["entity_redaction_mode"] == "entity_type"


def test_elevenlabs_transcribe_includes_audio_events(tmp_path):
    """Tagged ElevenLabs audio events should be preserved in transcript output."""
    engine = ElevenLabsEngine(api_key="test-key")
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake-audio")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "text": "hello [laughter] world",
        "language_code": "en",
        "words": [
            {"type": "word", "text": "hello", "start": 0.0, "end": 0.5, "logprob": -0.1, "speaker_id": "speaker_0"},
            {"type": "audio_event", "text": "laughter", "start": 0.5, "end": 0.7, "speaker_id": "speaker_0"},
            {"type": "word", "text": "world", "start": 0.7, "end": 1.1, "logprob": -0.2, "speaker_id": "speaker_0"},
        ],
    }

    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        result = engine.transcribe(audio_path, model="scribe_v2")

    assert [w["word"] for w in result.words] == ["hello", "[laughter]", "world"]
    assert result.segments[0]["text"] == "hello [laughter] world"


@pytest.mark.asyncio
async def test_elevenlabs_validate_key_success():
    """validate_api_key returns True for valid key."""
    engine = ElevenLabsEngine(api_key="valid-key")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await engine.validate_api_key()
        assert result["valid"] is True


@pytest.mark.asyncio
async def test_elevenlabs_validate_key_failure():
    """validate_api_key returns False for invalid key."""
    engine = ElevenLabsEngine(api_key="invalid-key")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await engine.validate_api_key()
        assert result["valid"] is False
        assert "error" in result
