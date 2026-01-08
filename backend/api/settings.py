# api/settings.py
"""Settings API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Current settings response."""
    default_engine: str
    default_model: str
    diarization_enabled: bool
    min_speakers: int
    max_speakers: int
    # API key presence (not actual keys)
    has_hf_token: bool
    has_assemblyai_key: bool
    has_elevenlabs_key: bool
    has_openai_key: bool
    has_deepgram_key: bool
    has_gemini_key: bool


@router.get("", response_model=SettingsResponse)
async def get_current_settings(settings: Settings = Depends(get_settings)):
    """Get current application settings."""
    return SettingsResponse(
        default_engine=settings.default_engine,
        default_model=settings.default_model,
        diarization_enabled=settings.diarization_enabled,
        min_speakers=settings.min_speakers,
        max_speakers=settings.max_speakers,
        has_hf_token=settings.hf_token is not None,
        has_assemblyai_key=settings.assemblyai_api_key is not None,
        has_elevenlabs_key=settings.elevenlabs_api_key is not None,
        has_openai_key=settings.openai_api_key is not None,
        has_deepgram_key=settings.deepgram_api_key is not None,
        has_gemini_key=settings.gemini_api_key is not None,
    )
