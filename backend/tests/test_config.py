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
    """Test default transcription engine is MLX. Note: actual values may be overridden by config.json."""
    settings = Settings()
    assert settings.default_engine == "mlx-whisper"
    # default_model can be overridden by config.json, so just check it's a valid whisper model
    assert settings.default_model in ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo", "turbo"]


def test_ensure_directories_creates_folders():
    """Test that ensure_directories creates all required folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings(base_path=Path(tmpdir) / "Transcriptions")
        settings.ensure_directories()

        assert settings.uploads_path.exists()
        assert settings.transcribed_path.exists()
        assert settings.processing_path.exists()
        assert settings.templates_path.exists()


def test_settings_compute_device_default():
    """Test compute_device defaults to 'auto'."""
    settings = Settings()
    assert settings.compute_device == "auto"


def test_settings_diarization_method_default():
    """Test diarization_method defaults to 'fast'."""
    settings = Settings()
    assert settings.diarization_method == "fast"


def test_settings_compute_device_values():
    """Test compute_device accepts valid values."""
    for value in ["auto", "mps", "cpu"]:
        settings = Settings(compute_device=value)
        assert settings.compute_device == value


def test_settings_diarization_method_values():
    """Test diarization_method accepts valid values."""
    for value in ["none", "fast", "accurate"]:
        settings = Settings(diarization_method=value)
        assert settings.diarization_method == value


def test_settings_postprocessing_provider_default():
    """Test postprocessing_provider defaults to 'gemini'."""
    settings = Settings()
    assert settings.postprocessing_provider == "gemini"


def test_settings_postprocessing_model_default():
    """Test postprocessing_model defaults to 'gemini-2.5-flash'."""
    settings = Settings()
    assert settings.postprocessing_model == "gemini-2.5-flash"


def test_settings_postprocessing_default_template():
    """Test postprocessing_default_template defaults to None."""
    settings = Settings()
    assert settings.postprocessing_default_template is None


def test_insights_settings_exist():
    """Test that AI Insights settings exist in config."""
    settings = Settings()
    assert hasattr(settings, 'insights_provider')
    assert hasattr(settings, 'insights_model')
    assert hasattr(settings, 'insights_default_template')
    assert hasattr(settings, 'insight_templates_path')
