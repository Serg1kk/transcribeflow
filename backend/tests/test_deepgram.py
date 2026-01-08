# tests/test_deepgram.py
"""Tests for Deepgram engine."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from engines.deepgram import DeepgramEngine
from engines.base import TranscriptionEngine


def test_deepgram_implements_interface():
    """Deepgram engine must implement TranscriptionEngine."""
    engine = DeepgramEngine(api_key="test-key")
    assert isinstance(engine, TranscriptionEngine)


def test_deepgram_is_available_with_key():
    """Engine is available when API key is provided."""
    engine = DeepgramEngine(api_key="test-key")
    assert engine.is_available() is True


def test_deepgram_not_available_without_key():
    """Engine is not available without API key."""
    engine = DeepgramEngine(api_key=None)
    assert engine.is_available() is False


def test_deepgram_name():
    """Engine name should be 'deepgram'."""
    engine = DeepgramEngine(api_key="test")
    assert engine.name == "deepgram"


@pytest.mark.asyncio
async def test_deepgram_validate_key_success():
    """validate_api_key returns True for valid key."""
    engine = DeepgramEngine(api_key="valid-key")

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
async def test_deepgram_validate_key_failure():
    """validate_api_key returns False for invalid key."""
    engine = DeepgramEngine(api_key="invalid-key")

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
