# engines/registry.py
"""Engine registry with provider definitions."""
from typing import Any, Dict, List

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "mlx-whisper": {
        "name": "MLX Local",
        "requires_api_key": False,
        "key_field": None,
        "models": [
            "large-v3-turbo",
            "large-v3",
            "large-v2",
            "medium",
            "small",
            "base",
            "tiny",
        ],
        "supports_diarization": False,  # Uses Pyannote locally
    },
    "assemblyai": {
        "name": "AssemblyAI",
        "requires_api_key": True,
        "key_field": "assemblyai_api_key",
        "models": ["best", "nano"],
        "supports_diarization": True,
    },
    "deepgram": {
        "name": "Deepgram",
        "requires_api_key": True,
        "key_field": "deepgram_api_key",
        "models": ["nova-3", "nova-2"],
        "supports_diarization": True,
    },
    "elevenlabs": {
        "name": "ElevenLabs Scribe",
        "requires_api_key": True,
        "key_field": "elevenlabs_api_key",
        "models": ["scribe_v1"],
        "supports_diarization": True,
    },
    "yandex": {
        "name": "Yandex SpeechKit",
        "requires_api_key": True,
        "key_field": "yandex_api_key",
        "models": ["general", "general:rc"],
        "supports_diarization": True,
    },
}


def get_available_engines(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get list of available engines based on configured API keys.

    Args:
        config: Dict with API key fields (assemblyai_api_key, deepgram_api_key, etc.)

    Returns:
        List of engine dicts with id, name, models, available fields
    """
    engines = []

    for engine_id, provider in PROVIDERS.items():
        available = True

        if provider["requires_api_key"]:
            key_field = provider["key_field"]
            available = bool(config.get(key_field))

        if available:
            engines.append({
                "id": engine_id,
                "name": provider["name"],
                "models": provider["models"],
                "available": True,
            })

    return engines
