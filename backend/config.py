# config.py
"""Application configuration using pydantic-settings with config.json priority."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

CONFIG_PATH = Path.home() / ".transcribeflow" / "config.json"


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that reads from config.json file."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        """Get value for a field from config.json."""
        config = self._load_config()
        if field_name in config:
            return config[field_name], field_name, False
        return None, field_name, False

    # Deprecated fields that should be ignored when loading config
    DEPRECATED_FIELDS = {"diarization_enabled"}

    def _load_config(self) -> Dict[str, Any]:
        """Load config from JSON file, filtering out deprecated fields."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Filter out deprecated fields
                    return {k: v for k, v in config.items() if k not in self.DEPRECATED_FIELDS}
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def __call__(self) -> Dict[str, Any]:
        """Return all config values."""
        return self._load_config()


class Settings(BaseSettings):
    """Application settings with config.json priority over environment."""

    # Paths
    base_path: Path = Field(default_factory=lambda: Path.home() / "Transcriptions")

    @property
    def uploads_path(self) -> Path:
        return self.base_path / "uploads"

    @property
    def transcribed_path(self) -> Path:
        return self.base_path / "transcribed"

    @property
    def processing_path(self) -> Path:
        return self.base_path / "processing"

    @property
    def templates_path(self) -> Path:
        return self.base_path / "templates"

    # Transcription defaults
    default_engine: str = "mlx-whisper"
    default_model: str = "large-v2"

    # Diarization
    diarization_method: str = "fast"  # "none" | "fast" | "accurate"
    compute_device: str = "auto"  # "auto" | "mps" | "cpu"
    hf_token: Optional[str] = None
    min_speakers: int = 2
    max_speakers: int = 6

    @property
    def diarization_enabled(self) -> bool:
        """Backwards compatibility: True if diarization_method is not 'none'."""
        return self.diarization_method != "none"

    # Whisper Anti-Hallucination Settings
    # These help prevent "Субтитры сделал DimaTorzok" and similar artifacts
    whisper_no_speech_threshold: float = 0.6  # Skip segments where no_speech_prob > this (0.0-1.0)
    whisper_logprob_threshold: float = -1.0   # Skip segments with avg_logprob < this (more negative = stricter)
    whisper_compression_ratio_threshold: float = 2.4  # Skip repetitive/garbled text
    whisper_hallucination_silence_threshold: Optional[float] = 2.0  # Skip silence gaps > N seconds
    whisper_condition_on_previous_text: bool = True  # Use previous text as context
    whisper_initial_prompt: Optional[str] = None  # Optional context prompt (e.g., "Это рабочий митинг")

    # Cloud API keys (optional)
    assemblyai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    yandex_api_key: Optional[str] = None

    # LLM settings
    default_llm_provider: str = "gemini"
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Post-processing settings
    postprocessing_provider: str = "gemini"  # "gemini" | "openrouter"
    postprocessing_model: str = "gemini-2.5-flash"
    postprocessing_default_template: Optional[str] = None  # None = always ask

    # AI Insights (Level 2) settings
    insights_provider: str = "gemini"  # "gemini" | "openrouter" | "anthropic"
    insights_model: str = "gemini-2.5-flash"
    insights_default_template: Optional[str] = None  # None = always ask

    @property
    def insight_templates_path(self) -> Path:
        return self.base_path / "insight-templates"

    # Server
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    class Config:
        env_file = ".env"
        env_prefix = "TRANSCRIBEFLOW_"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources priority: config.json > env > .env > defaults."""
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),  # config.json has priority
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def ensure_directories(self):
        """Create all required directories."""
        for path in [self.uploads_path, self.transcribed_path,
                     self.processing_path, self.templates_path,
                     self.insight_templates_path]:
            path.mkdir(parents=True, exist_ok=True)


def clear_settings_cache():
    """Clear the settings cache to reload config."""
    get_settings.cache_clear()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
