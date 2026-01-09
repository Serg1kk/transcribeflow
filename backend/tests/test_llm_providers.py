# tests/test_llm_providers.py
"""Tests for LLM provider clients."""
import pytest
from services.llm_providers import GeminiClient, OpenRouterClient, LLMResponse


def test_gemini_client_exists():
    """Test GeminiClient can be instantiated."""
    client = GeminiClient(api_key="test-key")
    assert client is not None


def test_openrouter_client_exists():
    """Test OpenRouterClient can be instantiated."""
    client = OpenRouterClient(api_key="test-key")
    assert client is not None


def test_llm_response_dataclass():
    """Test LLMResponse dataclass structure."""
    response = LLMResponse(
        text="Hello world",
        input_tokens=10,
        output_tokens=5,
    )
    assert response.text == "Hello world"
    assert response.input_tokens == 10
    assert response.output_tokens == 5
