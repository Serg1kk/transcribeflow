# api/settings.py
"""Settings API endpoints."""
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import Settings, get_settings, clear_settings_cache, CONFIG_PATH

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Current settings response."""
    # Transcription
    default_engine: str
    default_model: str

    # Diarization
    diarization_enabled: bool
    min_speakers: int
    max_speakers: int

    # Whisper Anti-Hallucination Settings
    whisper_no_speech_threshold: float
    whisper_logprob_threshold: float
    whisper_compression_ratio_threshold: float
    whisper_hallucination_silence_threshold: Optional[float]
    whisper_condition_on_previous_text: bool
    whisper_initial_prompt: Optional[str]

    # LLM
    default_llm_provider: str

    # API key presence (not actual keys for security)
    has_hf_token: bool
    has_assemblyai_key: bool
    has_elevenlabs_key: bool
    has_deepgram_key: bool
    has_yandex_key: bool
    has_gemini_key: bool
    has_openrouter_key: bool

    # Feature availability status
    features: dict


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""
    # Transcription
    default_engine: Optional[str] = None
    default_model: Optional[str] = None

    # Diarization
    diarization_enabled: Optional[bool] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None

    # Whisper Anti-Hallucination Settings
    whisper_no_speech_threshold: Optional[float] = None
    whisper_logprob_threshold: Optional[float] = None
    whisper_compression_ratio_threshold: Optional[float] = None
    whisper_hallucination_silence_threshold: Optional[float] = None
    whisper_condition_on_previous_text: Optional[bool] = None
    whisper_initial_prompt: Optional[str] = None

    # LLM
    default_llm_provider: Optional[str] = None

    # API keys (can be updated)
    hf_token: Optional[str] = None
    assemblyai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    yandex_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


# Feature status: implemented or TBD
FEATURES = {
    "mlx_whisper": {"status": "implemented", "description": "Local Whisper on Apple Silicon"},
    "assemblyai": {"status": "implemented", "description": "AssemblyAI cloud transcription"},
    "deepgram": {"status": "implemented", "description": "Deepgram cloud transcription"},
    "elevenlabs": {"status": "implemented", "description": "ElevenLabs Scribe transcription"},
    "yandex": {"status": "implemented", "description": "Yandex SpeechKit transcription"},
    "diarization": {"status": "implemented", "description": "Speaker identification (Pyannote)"},
    "gemini_llm": {"status": "tbd", "description": "Google Gemini for post-processing"},
    "openrouter_llm": {"status": "tbd", "description": "OpenRouter for LLM access"},
}


@router.get("", response_model=SettingsResponse)
async def get_current_settings(settings: Settings = Depends(get_settings)):
    """Get current application settings."""
    return SettingsResponse(
        default_engine=settings.default_engine,
        default_model=settings.default_model,
        diarization_enabled=settings.diarization_enabled,
        min_speakers=settings.min_speakers,
        max_speakers=settings.max_speakers,
        whisper_no_speech_threshold=settings.whisper_no_speech_threshold,
        whisper_logprob_threshold=settings.whisper_logprob_threshold,
        whisper_compression_ratio_threshold=settings.whisper_compression_ratio_threshold,
        whisper_hallucination_silence_threshold=settings.whisper_hallucination_silence_threshold,
        whisper_condition_on_previous_text=settings.whisper_condition_on_previous_text,
        whisper_initial_prompt=settings.whisper_initial_prompt,
        default_llm_provider=settings.default_llm_provider,
        has_hf_token=bool(settings.hf_token),
        has_assemblyai_key=bool(settings.assemblyai_api_key),
        has_elevenlabs_key=bool(settings.elevenlabs_api_key),
        has_deepgram_key=bool(settings.deepgram_api_key),
        has_yandex_key=bool(settings.yandex_api_key),
        has_gemini_key=bool(settings.gemini_api_key),
        has_openrouter_key=bool(settings.openrouter_api_key),
        features=FEATURES,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdateRequest):
    """Update application settings. Saves to config.json."""
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Update only provided fields
    update_data = update.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if value is not None and value != "":
            config[key] = value

    # Save config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Clear settings cache to reload
    clear_settings_cache()

    # Return updated settings
    settings = get_settings()
    return SettingsResponse(
        default_engine=settings.default_engine,
        default_model=settings.default_model,
        diarization_enabled=settings.diarization_enabled,
        min_speakers=settings.min_speakers,
        max_speakers=settings.max_speakers,
        whisper_no_speech_threshold=settings.whisper_no_speech_threshold,
        whisper_logprob_threshold=settings.whisper_logprob_threshold,
        whisper_compression_ratio_threshold=settings.whisper_compression_ratio_threshold,
        whisper_hallucination_silence_threshold=settings.whisper_hallucination_silence_threshold,
        whisper_condition_on_previous_text=settings.whisper_condition_on_previous_text,
        whisper_initial_prompt=settings.whisper_initial_prompt,
        default_llm_provider=settings.default_llm_provider,
        has_hf_token=bool(settings.hf_token),
        has_assemblyai_key=bool(settings.assemblyai_api_key),
        has_elevenlabs_key=bool(settings.elevenlabs_api_key),
        has_deepgram_key=bool(settings.deepgram_api_key),
        has_yandex_key=bool(settings.yandex_api_key),
        has_gemini_key=bool(settings.gemini_api_key),
        has_openrouter_key=bool(settings.openrouter_api_key),
        features=FEATURES,
    )


class ValidateKeyRequest(BaseModel):
    """Request to validate an API key."""
    provider: str
    api_key: str


class ValidateKeyResponse(BaseModel):
    """Response from key validation."""
    valid: bool
    error: Optional[str] = None


@router.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_api_key(request: ValidateKeyRequest):
    """Validate an API key for a cloud provider."""
    from engines import AssemblyAIEngine, DeepgramEngine, ElevenLabsEngine, YandexEngine

    engines = {
        "assemblyai": AssemblyAIEngine,
        "deepgram": DeepgramEngine,
        "elevenlabs": ElevenLabsEngine,
        "yandex": YandexEngine,
    }

    if request.provider not in engines:
        return ValidateKeyResponse(valid=False, error=f"Unknown provider: {request.provider}")

    engine = engines[request.provider](api_key=request.api_key)
    result = await engine.validate_api_key()

    return ValidateKeyResponse(**result)
