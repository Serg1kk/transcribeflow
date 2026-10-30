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

    openai_models = service.list_models("openai")
    assert {m.id for m in openai_models} == {
        "gpt-6.1-sol", "gpt-6.1-terra", "gpt-6-luna", "gpt-6-astra",
    }
    assert {m.id for m in service.list_models("anthropic")} == {
        "claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5", "claude-fable-5-1",
    }


def test_existing_catalog_gets_openai_without_losing_custom_models(tmp_path):
    import json
    config_path = tmp_path / "llm_models.json"
    original = {"gemini": {"models": [{"id": "custom", "name": "My model"}]},
                "openrouter": {"models": []}}
    config_path.write_text(json.dumps(original))
    service = LLMModelsService(config_path=config_path)
    config = service.get_all_config()
    assert config["gemini"] == original["gemini"]
    assert config["openrouter"] == original["openrouter"]
    assert service.get_model("openai", "gpt-6.1-sol") is not None
    assert service.get_model("anthropic", "claude-sonnet-5-5") is not None
    assert json.loads(config_path.read_text()) == original

    config["openai"] = {"models": [{"id": "custom-openai", "name": "Custom"}]}
    service.update_config(config)
    assert [m.id for m in service.list_models("openai")] == ["custom-openai"]


def test_llm_models_service_get_model(tmp_path):
    """Test getting a specific model."""
    service = LLMModelsService(config_path=tmp_path / "llm_models.json")

    model = service.get_model("gemini", "gemini-3.1-pro-preview")
    assert model is not None
    assert model.id == "gemini-3.1-pro-preview"
    assert model.name == "Gemini 3.1 Pro Preview (1M)"
    assert model.input_price_per_1m == 2.00


def test_llm_models_service_uses_updated_official_model_ids(tmp_path):
    """Test updated Gemini/OpenRouter model lists match the curated official set."""
    service = LLMModelsService(config_path=tmp_path / "llm_models.json")

    gemini_ids = {model.id for model in service.list_models("gemini")}
    openrouter_ids = {model.id for model in service.list_models("openrouter")}

    assert "gemini-3.1-pro-preview" in gemini_ids
    assert "gemini-3.5-flash" in gemini_ids
    assert "gemini-3-pro-preview" not in gemini_ids

    assert "google/gemini-3.1-pro-preview" in openrouter_ids
    assert "google/gemini-3.5-flash" in openrouter_ids
    assert "google/gemini-3-pro-preview" not in openrouter_ids
    assert "anthropic/claude-haiku-4.5" in openrouter_ids
    assert "anthropic/claude-sonnet-5" in openrouter_ids
    assert "anthropic/claude-opus-4.8" in openrouter_ids
    assert "anthropic/claude-sonnet-4" not in openrouter_ids
    assert "openai/gpt-5.4-mini" in openrouter_ids
    assert "openai/gpt-5.5" in openrouter_ids
    assert "qwen/qwen-turbo" not in openrouter_ids


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
