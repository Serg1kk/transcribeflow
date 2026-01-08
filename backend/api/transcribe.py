# api/transcribe.py
"""Transcription API endpoints."""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
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


@router.get("/queue", response_model=List[TranscriptionResponse])
async def list_queue(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """List all transcriptions in the queue."""
    transcriptions = (
        db.query(Transcription)
        .order_by(Transcription.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        TranscriptionResponse(
            id=t.id,
            filename=t.filename,
            status=t.status.value,
            engine=t.engine,
            model=t.model,
            language=t.language,
            created_at=t.created_at,
            progress=t.progress,
        )
        for t in transcriptions
    ]


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific transcription by ID."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

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


@router.get("/{transcription_id}/transcript")
async def get_transcript_data(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Get the full transcript JSON data."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Transcript not ready")

    transcript_path = Path(transcription.output_dir) / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript file not found")

    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


class SpeakerNamesUpdate(BaseModel):
    """Request model for updating speaker names."""
    speaker_names: dict


@router.put("/{transcription_id}/speakers")
async def update_speakers(
    transcription_id: str,
    update: SpeakerNamesUpdate,
    db: Session = Depends(get_db),
):
    """Update speaker names for a transcription."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Update in database
    transcription.speaker_names = update.speaker_names
    db.commit()

    # Update in transcript.json file
    if transcription.output_dir:
        transcript_path = Path(transcription.output_dir) / "transcript.json"
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update speaker names in the speakers dict
            for speaker_id, name in update.speaker_names.items():
                if speaker_id in data["speakers"]:
                    data["speakers"][speaker_id]["name"] = name

            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "ok"}
