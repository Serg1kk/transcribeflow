# services/llm_models_service.py
"""LLM models configuration service."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_PATH = Path.home() / ".transcribeflow" / "llm_models.json"


@dataclass
class LLMModel:
    """LLM model configuration."""
    id: str
    name: str
    input_price_per_1m: Optional[float] = None
    output_price_per_1m: Optional[float] = None

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """Calculate cost in USD. Returns None if pricing not configured."""
        if self.input_price_per_1m is None or self.output_price_per_1m is None:
            return None
        return (input_tokens * self.input_price_per_1m + output_tokens * self.output_price_per_1m) / 1_000_000


# Default models configuration
# Prices in USD per 1M tokens (input, output)
DEFAULT_MODELS = {
    "gemini": [
        # Gemini 3.x
        LLMModel("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview (1M)", 2.00, 12.00),
        LLMModel("gemini-3.5-flash", "Gemini 3.5 Flash (1M)", 1.50, 9.00),
        LLMModel("gemini-3-flash-preview", "Gemini 3 Flash Preview (1M)", 0.50, 3.00),
        LLMModel("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (1M)", 0.25, 1.50),
        # Gemini 2.5
        LLMModel("gemini-2.5-pro", "Gemini 2.5 Pro (1M)", 1.25, 10.00),
        LLMModel("gemini-2.5-flash", "Gemini 2.5 Flash (1M)", 0.30, 2.50),
        LLMModel("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (1M)", 0.10, 0.40),
    ],
    "openrouter": [
        # Large context models (1M+)
        LLMModel("x-ai/grok-4.1-fast", "Grok 4.1 Fast (2M!)", 0.20, 0.50),
        LLMModel("google/gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview (via OR, 1M)", 2.00, 12.00),
        LLMModel("google/gemini-3.5-flash", "Gemini 3.5 Flash (via OR, 1M)", 1.50, 9.00),
        LLMModel("google/gemini-3-flash-preview", "Gemini 3 Flash (via OR, 1M)", 0.50, 3.00),
        LLMModel("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (via OR, 1M)", 0.25, 1.50),
        LLMModel("google/gemini-2.5-pro", "Gemini 2.5 Pro (via OR, 1M)", 1.25, 10.00),
        LLMModel("google/gemini-2.5-pro-preview", "Gemini 2.5 Pro Preview (via OR, 1M)", 1.25, 10.00),
        LLMModel("google/gemini-2.5-flash", "Gemini 2.5 Flash (via OR, 1M)", 0.30, 2.50),
        LLMModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (via OR, 1M)", 0.10, 0.40),
        LLMModel("anthropic/claude-haiku-4.5", "Claude Haiku 4.5 (200K)", 1.00, 5.00),
        LLMModel("anthropic/claude-sonnet-5", "Claude Sonnet 5 (1M)", 2.00, 10.00),
        LLMModel("anthropic/claude-opus-4.8", "Claude Opus 4.8 (1M)", 5.00, 25.00),
        LLMModel("openai/gpt-4.1-mini", "GPT-4.1 Mini (1M)", 0.40, 1.60),
        LLMModel("openai/gpt-5.4-mini", "GPT-5.4 Mini (400K)", 0.75, 4.50),
        LLMModel("openai/gpt-5.5", "GPT-5.5 (1M)", 5.00, 30.00),
        LLMModel("meta-llama/llama-4-maverick", "Llama 4 Maverick (1M)", 0.15, 0.60),
        # Reasoning
        LLMModel("deepseek/deepseek-r1", "DeepSeek R1 (reasoning)", 0.70, 2.50),
    ],
}


class LLMModelsService:
    """Service for managing LLM model configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self._ensure_config()

    def _ensure_config(self):
        """Ensure config file exists with defaults."""
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_config(self._models_to_dict(DEFAULT_MODELS))

    def _models_to_dict(self, models: Dict[str, List[LLMModel]]) -> dict:
        """Convert models to JSON-serializable dict."""
        return {
            provider: {
                "models": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "input_price_per_1m": m.input_price_per_1m,
                        "output_price_per_1m": m.output_price_per_1m,
                    }
                    for m in model_list
                ]
            }
            for provider, model_list in models.items()
        }

    def _save_config(self, config: dict):
        """Save config to file."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _load_config(self) -> dict:
        """Load config from file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._models_to_dict(DEFAULT_MODELS)

    def list_models(self, provider: str) -> List[LLMModel]:
        """List models for a provider."""
        config = self._load_config()
        provider_config = config.get(provider, {})
        models_data = provider_config.get("models", [])

        return [
            LLMModel(
                id=m["id"],
                name=m["name"],
                input_price_per_1m=m.get("input_price_per_1m"),
                output_price_per_1m=m.get("output_price_per_1m"),
            )
            for m in models_data
        ]

    def get_model(self, provider: str, model_id: str) -> Optional[LLMModel]:
        """Get a specific model by provider and ID."""
        models = self.list_models(provider)
        for model in models:
            if model.id == model_id:
                return model
        return None

    def get_all_config(self) -> dict:
        """Get full configuration."""
        return self._load_config()

    def update_config(self, config: dict):
        """Update full configuration."""
        self._save_config(config)
