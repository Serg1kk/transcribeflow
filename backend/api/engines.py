# api/engines.py
"""Engine capabilities API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import Settings, get_settings
from engines.registry import PROVIDERS, get_available_engines


router = APIRouter(prefix="/api/engines", tags=["engines"])


class EngineCapabilities(BaseModel):
    """Engine capabilities."""
    supports_initial_prompt: bool = False
    supports_timestamps: bool = True
    supports_word_timestamps: bool = True


class EngineInfo(BaseModel):
    """Engine information with models."""
    id: str
    name: str
    models: List[str]
    available: bool


class EnginesResponse(BaseModel):
    """Response with list of engines."""
    engines: List[EngineInfo]


class EngineCapabilitiesResponse(BaseModel):
    """Response model for engine capabilities."""
    name: str
    display_name: str
    capabilities: EngineCapabilities


# Capabilities for each engine
ENGINE_CAPABILITIES = {
    "mlx-whisper": EngineCapabilities(
        supports_initial_prompt=True,
        supports_timestamps=True,
        supports_word_timestamps=True,
    ),
    "assemblyai": EngineCapabilities(
        supports_initial_prompt=False,
        supports_timestamps=True,
        supports_word_timestamps=True,
    ),
    "deepgram": EngineCapabilities(
        supports_initial_prompt=False,
        supports_timestamps=True,
        supports_word_timestamps=True,
    ),
    "elevenlabs": EngineCapabilities(
        supports_initial_prompt=False,
        supports_timestamps=True,
        supports_word_timestamps=True,
    ),
    "yandex": EngineCapabilities(
        supports_initial_prompt=False,
        supports_timestamps=True,
        supports_word_timestamps=True,
    ),
}


@router.get("", response_model=EnginesResponse)
async def list_engines(settings: Settings = Depends(get_settings)):
    """List all available transcription engines with their models.

    Only returns engines that are properly configured (have API keys if required).
    """
    config = {
        "assemblyai_api_key": settings.assemblyai_api_key,
        "deepgram_api_key": settings.deepgram_api_key,
        "elevenlabs_api_key": settings.elevenlabs_api_key,
        "yandex_api_key": settings.yandex_api_key,
    }

    engines = get_available_engines(config)
    return EnginesResponse(engines=[EngineInfo(**e) for e in engines])


@router.get("/{engine_id}/models", response_model=List[str])
async def get_engine_models(engine_id: str):
    """Get available models for a specific engine."""
    if engine_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Engine '{engine_id}' not found")

    return PROVIDERS[engine_id]["models"]


@router.get("/{engine_name}/capabilities", response_model=EngineCapabilitiesResponse)
async def get_engine_capabilities(engine_name: str):
    """Get capabilities for a specific engine."""
    if engine_name not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Engine '{engine_name}' not found")

    provider = PROVIDERS[engine_name]
    capabilities = ENGINE_CAPABILITIES.get(engine_name, EngineCapabilities())

    return EngineCapabilitiesResponse(
        name=engine_name,
        display_name=provider["name"],
        capabilities=capabilities,
    )
