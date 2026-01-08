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
    error_message: Optional[str] = None
    file_size: Optional[int] = None  # File size in bytes
    duration_seconds: Optional[float] = None  # Audio duration
    # Timing breakdown
    processing_time_seconds: Optional[float] = None  # Total processing time
    transcription_time_seconds: Optional[float] = None  # ASR time only
    diarization_time_seconds: Optional[float] = None  # Speaker ID time only

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

    # Get file size
    file_size = upload_path.stat().st_size

    # Create transcription record
    transcription = Transcription(
        filename=file.filename,
        original_path=str(upload_path),
        file_size=file_size,
        engine=engine,
        model=model,
        language=language,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        status=TranscriptionStatus.DRAFT,  # Default to DRAFT
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
        error_message=transcription.error_message,
        file_size=transcription.file_size,
        duration_seconds=transcription.duration_seconds,
        processing_time_seconds=transcription.processing_time_seconds,
        transcription_time_seconds=transcription.transcription_time_seconds,
        diarization_time_seconds=transcription.diarization_time_seconds,
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
            error_message=t.error_message,
            file_size=t.file_size,
            duration_seconds=t.duration_seconds,
            processing_time_seconds=t.processing_time_seconds,
            transcription_time_seconds=t.transcription_time_seconds,
            diarization_time_seconds=t.diarization_time_seconds,
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
        error_message=transcription.error_message,
        file_size=transcription.file_size,
        duration_seconds=transcription.duration_seconds,
        processing_time_seconds=transcription.processing_time_seconds,
        transcription_time_seconds=transcription.transcription_time_seconds,
        diarization_time_seconds=transcription.diarization_time_seconds,
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


@router.delete("/history/{filter_type}")
async def delete_history(
    filter_type: str,
    db: Session = Depends(get_db),
):
    """Delete transcription history.

    Args:
        filter_type: 'all' to delete everything, 'failed' to delete only failed
    """
    if filter_type == "failed":
        count = db.query(Transcription).filter(
            Transcription.status == TranscriptionStatus.FAILED
        ).count()
        db.query(Transcription).filter(
            Transcription.status == TranscriptionStatus.FAILED
        ).delete()
    elif filter_type == "all":
        count = db.query(Transcription).count()
        db.query(Transcription).delete()
    else:
        raise HTTPException(status_code=400, detail="filter_type must be 'all' or 'failed'")

    db.commit()
    return {"deleted": count}


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
