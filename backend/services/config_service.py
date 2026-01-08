# services/config_service.py
"""Configuration service with config.json priority over .env."""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

CONFIG_PATH = Path.home() / ".transcribeflow" / "config.json"


def _load_config_file() -> Dict[str, Any]:
    """Load config from JSON file if it exists."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save config to JSON file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    # Clear cache so new values are picked up
    get_config_value.cache_clear()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value, preferring config.json over environment."""
    config = _load_config_file()
    if key in config:
        return config[key]
    return default


def get_all_config() -> Dict[str, Any]:
    """Get all config values from config.json."""
    return _load_config_file()


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update config values and save."""
    config = _load_config_file()

    # Only save non-None values
    for key, value in updates.items():
        if value is not None and value != "":
            config[key] = value
        elif key in config and (value is None or value == ""):
            # Remove empty values
            del config[key]

    save_config(config)
    return config
