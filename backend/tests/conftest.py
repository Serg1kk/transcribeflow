# tests/conftest.py
"""Test configuration and fixtures."""
import pytest
from models import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize database tables before running tests."""
    init_db()
