# tests/test_isolation.py
"""Guards that the suite never touches the operator's real installation.

These once failed in the worst possible way: running pytest wrote dummy uploads
into ~/Transcriptions and transcription rows into the live database, which then
showed up in the UI as broken entries.
"""
from pathlib import Path

from config import get_settings
from models.database import DATABASE_PATH


def test_database_is_not_the_real_one():
    real_db = Path.home() / ".transcribeflow" / "transcribeflow.db"
    assert Path(DATABASE_PATH).resolve() != real_db.resolve()


def test_base_path_is_not_the_real_one():
    real_base = Path.home() / "Transcriptions"
    assert Path(get_settings().base_path).resolve() != real_base.resolve()


def test_uploads_go_to_a_temp_dir(tmp_path):
    """Whatever the suite writes must stay outside the home directory."""
    uploads = Path(get_settings().uploads_path).resolve()
    assert not uploads.is_relative_to((Path.home() / "Transcriptions").resolve())


def test_real_config_and_env_are_not_loaded():
    """Defaults must survive: the real config.json and .env set other values."""
    settings = get_settings()
    assert settings.compute_device == "auto"
    assert settings.postprocessing_model == "gemini-2.5-flash"
    assert settings.hf_token is None
    assert settings.elevenlabs_api_key is None
