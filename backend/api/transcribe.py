# api/transcribe.py
"""Transcription API endpoints."""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import get_db, Transcription, TranscriptionStatus
from config import get_settings, Settings

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])

ALLOWED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"}


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    id: str
    filename: str
    status: str
    engine: str
    model: str
    language: Optional[str]
    created_at: datetime
    progress: float

    class Config:
        from_attributes = True


@router.post("/upload", response_model=TranscriptionResponse, status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    engine: str = Form(default="mlx-whisper"),
    model: str = Form(default="large-v2"),
    language: Optional[str] = Form(default=None),
    min_speakers: Optional[int] = Form(default=None),
    max_speakers: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Upload an audio file for transcription."""
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Ensure directories exist
    settings.ensure_directories()

    # Save uploaded file
    upload_path = settings.uploads_path / file.filename
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create transcription record
    transcription = Transcription(
        filename=file.filename,
        original_path=str(upload_path),
        engine=engine,
        model=model,
        language=language,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    return TranscriptionResponse(
        id=transcription.id,
        filename=transcription.filename,
        status=transcription.status.value,
        engine=transcription.engine,
        model=transcription.model,
        language=transcription.language,
        created_at=transcription.created_at,
        progress=transcription.progress,
    )
