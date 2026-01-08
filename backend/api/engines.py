# api/engines.py
"""Engine capabilities API endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/engines", tags=["engines"])


class EngineCapabilities(BaseModel):
    """Engine capabilities."""
    supports_initial_prompt: bool = False
    supports_timestamps: bool = True
    supports_word_timestamps: bool = True


class EngineInfo(BaseModel):
    """Engine information."""
    name: str
    display_name: str
    description: str


class EngineCapabilitiesResponse(BaseModel):
    """Response model for engine capabilities."""
    name: str
    display_name: str
    capabilities: EngineCapabilities


# Define available engines and their capabilities
ENGINES = {
    "mlx-whisper": {
        "display_name": "MLX Whisper",
        "description": "Local transcription using MLX-optimized Whisper for Apple Silicon",
        "capabilities": EngineCapabilities(
            supports_initial_prompt=True,
            supports_timestamps=True,
            supports_word_timestamps=True,
        ),
    },
}


@router.get("", response_model=List[EngineInfo])
async def list_engines():
    """List all available transcription engines."""
    return [
        EngineInfo(
            name=name,
            display_name=info["display_name"],
            description=info["description"],
        )
        for name, info in ENGINES.items()
    ]


@router.get("/{engine_name}/capabilities", response_model=EngineCapabilitiesResponse)
async def get_engine_capabilities(engine_name: str):
    """Get capabilities for a specific engine."""
    if engine_name not in ENGINES:
        raise HTTPException(status_code=404, detail=f"Engine '{engine_name}' not found")

    info = ENGINES[engine_name]
    return EngineCapabilitiesResponse(
        name=engine_name,
        display_name=info["display_name"],
        capabilities=info["capabilities"],
    )
