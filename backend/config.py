# config.py
"""Application configuration using pydantic-settings."""
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

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
    diarization_enabled: bool = True
    hf_token: Optional[str] = None
    min_speakers: int = 2
    max_speakers: int = 6

    # Cloud API keys (optional)
    assemblyai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None

    # LLM settings
    default_llm_provider: str = "gemini"
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Server
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    class Config:
        env_file = ".env"
        env_prefix = "TRANSCRIBEFLOW_"

    def ensure_directories(self):
        """Create all required directories."""
        for path in [self.uploads_path, self.transcribed_path,
                     self.processing_path, self.templates_path]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
