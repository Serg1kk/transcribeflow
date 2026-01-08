# tests/test_yandex.py
"""Tests for Yandex SpeechKit engine."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from engines.yandex import YandexEngine
from engines.base import TranscriptionEngine


def test_yandex_implements_interface():
    """Yandex engine must implement TranscriptionEngine."""
    engine = YandexEngine(api_key="test-key")
    assert isinstance(engine, TranscriptionEngine)


def test_yandex_is_available_with_key():
    """Engine is available when API key is provided."""
    engine = YandexEngine(api_key="test-key")
    assert engine.is_available() is True


def test_yandex_not_available_without_key():
    """Engine is not available without API key."""
    engine = YandexEngine(api_key=None)
    assert engine.is_available() is False


def test_yandex_name():
    """Engine name should be 'yandex'."""
    engine = YandexEngine(api_key="test")
    assert engine.name == "yandex"


@pytest.mark.asyncio
async def test_yandex_validate_key_success():
    """validate_api_key returns True for valid key (400 = auth passed)."""
    engine = YandexEngine(api_key="valid-key")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400  # Bad request but auth passed
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await engine.validate_api_key()
        assert result["valid"] is True


@pytest.mark.asyncio
async def test_yandex_validate_key_failure():
    """validate_api_key returns False for invalid key."""
    engine = YandexEngine(api_key="invalid-key")

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await engine.validate_api_key()
        assert result["valid"] is False
        assert "error" in result
