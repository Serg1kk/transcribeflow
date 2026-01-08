# tests/test_config.py
import pytest
import tempfile
from pathlib import Path
from config import Settings, get_settings


def test_settings_default_paths():
    """Test default paths are set correctly."""
    settings = Settings()
    assert settings.base_path == Path.home() / "Transcriptions"
    assert settings.uploads_path == settings.base_path / "uploads"
    assert settings.transcribed_path == settings.base_path / "transcribed"


def test_settings_default_engine():
    """Test default transcription engine is MLX."""
    settings = Settings()
    assert settings.default_engine == "mlx-whisper"
    assert settings.default_model == "large-v2"


def test_ensure_directories_creates_folders():
    """Test that ensure_directories creates all required folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings(base_path=Path(tmpdir) / "Transcriptions")
        settings.ensure_directories()

        assert settings.uploads_path.exists()
        assert settings.transcribed_path.exists()
        assert settings.processing_path.exists()
        assert settings.templates_path.exists()
