# tests/test_llm_models_service.py
"""Tests for LLM models configuration service."""
import pytest
from services.llm_models_service import LLMModelsService, LLMModel


def test_llm_models_service_default_models(tmp_path):
    """Test that default models are created on first access."""
    service = LLMModelsService(config_path=tmp_path / "llm_models.json")

    gemini_models = service.list_models("gemini")
    assert len(gemini_models) >= 3

    openrouter_models = service.list_models("openrouter")
    assert len(openrouter_models) >= 3


def test_llm_models_service_get_model(tmp_path):
    """Test getting a specific model."""
    service = LLMModelsService(config_path=tmp_path / "llm_models.json")

    model = service.get_model("gemini", "gemini-2.5-flash")
    assert model is not None
    assert model.id == "gemini-2.5-flash"
    assert model.name == "Gemini 2.5 Flash"
    assert model.input_price_per_1m == 0.30


def test_llm_model_cost_calculation():
    """Test cost calculation for a model."""
    model = LLMModel(
        id="test",
        name="Test",
        input_price_per_1m=1.0,
        output_price_per_1m=2.0
    )
    cost = model.calculate_cost(1000, 500)
    # (1000 * 1.0 + 500 * 2.0) / 1_000_000 = 0.002
    assert cost == pytest.approx(0.002)


def test_llm_model_cost_none_if_no_price():
    """Test cost is None if price not configured."""
    model = LLMModel(
        id="test",
        name="Test",
        input_price_per_1m=None,
        output_price_per_1m=None
    )
    cost = model.calculate_cost(1000, 500)
    assert cost is None
