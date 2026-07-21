# tests/conftest.py
"""Test configuration and fixtures.

Redirects every piece of persistent state into a throwaway directory. This has
to happen at import time, before anything from the app is imported: the SQLAlchemy
engine is bound when models.database is imported, and Settings resolves config.json
and .env just as eagerly — once those modules load, nothing a fixture does can
redirect them.

Without this the suite runs against the operator's live installation: TestClient
drives the real app, so uploads land in ~/Transcriptions and rows are written to
~/.transcribeflow/transcribeflow.db, leaving dozens of dummy .mp3 files and
transcription records behind. Tests asserting defaults also failed, because the
real config.json outranks environment variables.
"""
import os
import shutil
import tempfile
from pathlib import Path

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="transcribeflow-tests-"))
_BASE_PATH = _TMP_ROOT / "Transcriptions"

# config.json and .env point at files that deliberately do not exist, so the
# suite sees pristine defaults instead of local settings and API keys.
os.environ["TRANSCRIBEFLOW_DB_PATH"] = str(_TMP_ROOT / "transcribeflow.db")
os.environ["TRANSCRIBEFLOW_CONFIG_PATH"] = str(_TMP_ROOT / "absent-config.json")
os.environ["TRANSCRIBEFLOW_ENV_FILE"] = str(_TMP_ROOT / "absent.env")
os.environ["TRANSCRIBEFLOW_BASE_PATH"] = str(_BASE_PATH)

import pytest  # noqa: E402  (must follow the environment setup above)

from config import get_settings  # noqa: E402
from models import init_db  # noqa: E402
from models.database import DATABASE_PATH  # noqa: E402


def _assert_isolated():
    """Fail loudly rather than touch real data if the redirect did not take."""
    home = Path.home()
    settings = get_settings()

    for label, path in (
        ("database", DATABASE_PATH),
        ("base_path", settings.base_path),
    ):
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(_TMP_ROOT.resolve()):
            raise RuntimeError(
                f"Test isolation failed: {label} resolves to {resolved}, "
                f"outside the temporary root {_TMP_ROOT}. Refusing to run so the "
                f"suite cannot write to real data under {home}."
            )


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize a throwaway database and clean it up afterwards."""
    _assert_isolated()
    get_settings().ensure_directories()
    init_db()
    yield
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)
