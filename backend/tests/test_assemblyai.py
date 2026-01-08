# tests/test_assemblyai.py
"""Tests for AssemblyAI engine."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from engines.assemblyai import AssemblyAIEngine
from engines.base import TranscriptionEngine, TranscriptionResult


def test_assemblyai_implements_interface():
    """AssemblyAI engine must implement TranscriptionEngine."""
    engine = AssemblyAIEngine(api_key="test-key")
    assert isinstance(engine, TranscriptionEngine)


def test_assemblyai_is_available_with_key():
    """Engine is available when API key is provided."""
    engine = AssemblyAIEngine(api_key="test-key")
    assert engine.is_available() is True


def test_assemblyai_not_available_without_key():
    """Engine is not available without API key."""
    engine = AssemblyAIEngine(api_key=None)
    assert engine.is_available() is False


def test_assemblyai_name():
    """Engine name should be 'assemblyai'."""
    engine = AssemblyAIEngine(api_key="test")
    assert engine.name == "assemblyai"


@pytest.mark.asyncio
async def test_assemblyai_validate_key_success():
    """validate_api_key returns True for valid key."""
    engine = AssemblyAIEngine(api_key="valid-key")

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
async def test_assemblyai_validate_key_failure():
    """validate_api_key returns False for invalid key."""
    engine = AssemblyAIEngine(api_key="invalid-key")

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
