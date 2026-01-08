# tests/test_registry.py
"""Tests for engine registry."""
import pytest
from engines.registry import PROVIDERS, get_available_engines


def test_providers_has_mlx_whisper():
    """MLX Whisper must always be in providers."""
    assert "mlx-whisper" in PROVIDERS
    assert PROVIDERS["mlx-whisper"]["requires_api_key"] is False


def test_providers_has_cloud_engines():
    """All cloud providers must be defined."""
    assert "assemblyai" in PROVIDERS
    assert "deepgram" in PROVIDERS
    assert "elevenlabs" in PROVIDERS
    assert "yandex" in PROVIDERS


def test_each_provider_has_required_fields():
    """Each provider must have name, models, requires_api_key."""
    for provider_id, provider in PROVIDERS.items():
        assert "name" in provider, f"{provider_id} missing name"
        assert "models" in provider, f"{provider_id} missing models"
        assert "requires_api_key" in provider, f"{provider_id} missing requires_api_key"
        assert isinstance(provider["models"], list), f"{provider_id} models must be list"
        assert len(provider["models"]) > 0, f"{provider_id} must have at least one model"


def test_get_available_engines_returns_mlx_always():
    """MLX should always be available (no API key required)."""
    engines = get_available_engines({})
    assert any(e["id"] == "mlx-whisper" for e in engines)


def test_get_available_engines_filters_by_api_key():
    """Cloud engines only available when API key is set."""
    # No keys - only MLX
    engines = get_available_engines({})
    engine_ids = [e["id"] for e in engines]
    assert "mlx-whisper" in engine_ids
    assert "assemblyai" not in engine_ids

    # With AssemblyAI key
    engines = get_available_engines({"assemblyai_api_key": "test-key"})
    engine_ids = [e["id"] for e in engines]
    assert "assemblyai" in engine_ids
