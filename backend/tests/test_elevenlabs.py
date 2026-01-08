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
