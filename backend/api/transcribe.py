# api/transcribe.py
"""Transcription API endpoints."""
import json
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import get_db, Transcription, TranscriptionStatus, LLMOperation, LLMOperationType
from config import get_settings, Settings

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])

ALLOWED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"}
AUDIO_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}
AUDIO_STREAM_CHUNK_SIZE = 1024 * 1024
PLAYBACK_PREVIEW_FILENAME = "playback_preview.m4a"


def _format_timestamp(seconds: float) -> str:
    """Format timestamp as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _regenerate_txt_files(output_dir: Path, original_data: Optional[dict], cleaned_data: Optional[dict]):
    """Regenerate TXT files with current speaker names from JSON data."""
    # Regenerate transcript.txt
    if original_data:
        txt_path = output_dir / "transcript.txt"
        meta = original_data.get("metadata", {})
        speakers_dict = original_data.get("speakers", {})
        segments = original_data.get("segments", [])

        # Calculate duration from last segment
        duration_seconds = meta.get("duration_seconds", 0)
        if segments and not duration_seconds:
            duration_seconds = segments[-1].get("end", segments[-1].get("start", 0))

        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        duration_str = f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"

        lines = [
            f"Transcription: {meta.get('filename', 'Unknown')}",
            f"Date: {meta.get('created_at', '')[:10]}",
            f"Duration: {duration_str}",
            f"Participants: {', '.join(speakers_dict.keys())}",
            "",
            "-" * 40,
            "",
        ]

        for seg in segments:
            timestamp = _format_timestamp(seg.get("start", 0))
            speaker_id = seg.get("speaker", "SPEAKER_UNKNOWN")
            speaker = speakers_dict.get(speaker_id, {}).get("name", speaker_id)
            lines.append(f"[{timestamp}] {speaker}: {seg.get('text', '')}")
            lines.append("")

        lines.append("-" * 40)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # Regenerate transcript_cleaned.txt
    if cleaned_data:
        txt_path = output_dir / "transcript_cleaned.txt"
        meta = cleaned_data.get("metadata", {})
        speakers_dict = cleaned_data.get("speakers", {})
        segments = cleaned_data.get("segments", [])

        lines = [
            f"Cleaned Transcript: {meta.get('filename', 'Unknown')}",
            f"Cleaned: {meta.get('cleaned_at', '')[:10]}",
            f"Template: {meta.get('template', '')}",
            f"Model: {meta.get('model', '')}",
            "",
            "-" * 40,
            "",
        ]

        for seg in segments:
            timestamp = _format_timestamp(seg.get("start", 0))
            speaker_id = seg.get("speaker", "SPEAKER_UNKNOWN")
            speaker = speakers_dict.get(speaker_id, {}).get("name", speaker_id)
            lines.append(f"[{timestamp}] {speaker}: {seg.get('text', '')}")
            lines.append("")

        lines.append("-" * 40)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def _resolve_audio_path(transcription: Transcription) -> Path:
    """Resolve the best available audio file for transcript playback."""
    if transcription.output_dir:
        output_dir = Path(transcription.output_dir)

        preview_path = output_dir / PLAYBACK_PREVIEW_FILENAME
        if preview_path.exists():
            return preview_path

        preferred = output_dir / transcription.filename
        if preferred.exists():
            return preferred

        for candidate in output_dir.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in ALLOWED_EXTENSIONS:
                return candidate

    original_path = Path(transcription.original_path)
    if original_path.exists():
        return original_path

    raise HTTPException(status_code=404, detail="Playable audio file not found")


def _get_audio_content_type(audio_path: Path) -> str:
    """Return browser-friendly content type for audio playback."""
    return AUDIO_CONTENT_TYPES.get(audio_path.suffix.lower()) or mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"


def _parse_range_header(range_header: Optional[str], file_size: int) -> Optional[tuple[int, int]]:
    """Parse a single HTTP byte range."""
    if not range_header:
        return None

    if not range_header.startswith("bytes="):
        raise HTTPException(status_code=416, detail="Invalid range unit")

    try:
        start_str, end_str = range_header[len("bytes="):].split("-", 1)
    except ValueError as exc:
        raise HTTPException(status_code=416, detail="Invalid range header") from exc

    if not start_str and not end_str:
        raise HTTPException(status_code=416, detail="Invalid range header")

    try:
        if start_str:
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        else:
            suffix_length = int(end_str)
            if suffix_length <= 0:
                raise ValueError("suffix range must be positive")
            start = max(file_size - suffix_length, 0)
            end = file_size - 1
    except ValueError as exc:
        raise HTTPException(status_code=416, detail="Invalid range header") from exc

    if start < 0 or start >= file_size or end < start:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")

    return start, min(end, file_size - 1)


def _iter_file_range(audio_path: Path, start: int, end: int):
    """Yield a byte range from file without loading everything into memory."""
    with open(audio_path, "rb") as audio_file:
        audio_file.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = audio_file.read(min(AUDIO_STREAM_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


class LLMOperationSummary(BaseModel):
    """Summary of an LLM operation (clean or insights)."""
    operation_type: str  # "cleanup" | "insights"
    provider: str
    model: str
    template_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: Optional[float]
    processing_time_seconds: float
    created_at: datetime


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    id: str
    filename: str
    status: str
    engine: str
    model: str
    language: Optional[str]
    initial_prompt: Optional[str] = None  # Per-file transcription hint
    created_at: datetime
    progress: float
    error_message: Optional[str] = None
    file_size: Optional[int] = None  # File size in bytes
    duration_seconds: Optional[float] = None  # Audio duration
    compute_device: Optional[str] = None  # "cpu" | "mps" | "auto"
    diarization_method: Optional[str] = None  # "none" | "fast" | "accurate"
    # Timing breakdown
    processing_time_seconds: Optional[float] = None  # Total processing time
    transcription_time_seconds: Optional[float] = None  # ASR time only
    diarization_time_seconds: Optional[float] = None  # Speaker ID time only
    workflow_status: str = "pending"
    workflow_comment: Optional[str] = None
    # LLM operations
    llm_operations: List[LLMOperationSummary] = []

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
        initial_prompt=transcription.initial_prompt,
        created_at=transcription.created_at,
        progress=transcription.progress,
        error_message=transcription.error_message,
        file_size=transcription.file_size,
        duration_seconds=transcription.duration_seconds,
        workflow_status=transcription.workflow_status or "pending",
        workflow_comment=transcription.workflow_comment,
        processing_time_seconds=transcription.processing_time_seconds,
        transcription_time_seconds=transcription.transcription_time_seconds,
        diarization_time_seconds=transcription.diarization_time_seconds,
    )


def _build_transcription_response(t: Transcription, db: Session) -> TranscriptionResponse:
    """Build TranscriptionResponse with LLM operations."""
    # Fetch LLM operations for this transcription
    llm_ops = (
        db.query(LLMOperation)
        .filter(LLMOperation.transcription_id == t.id)
        .order_by(LLMOperation.created_at.desc())
        .all()
    )

    llm_operations = [
        LLMOperationSummary(
            operation_type=op.operation_type.value,
            provider=op.provider,
            model=op.model,
            template_id=op.template_id,
            input_tokens=op.input_tokens,
            output_tokens=op.output_tokens,
            cost_usd=op.cost_usd,
            processing_time_seconds=op.processing_time_seconds,
            created_at=op.created_at,
        )
        for op in llm_ops
    ]

    return TranscriptionResponse(
        id=t.id,
        filename=t.filename,
        status=t.status.value,
        engine=t.engine,
        model=t.model,
        language=t.language,
        initial_prompt=t.initial_prompt,
        created_at=t.created_at,
        progress=t.progress,
        error_message=t.error_message,
        file_size=t.file_size,
        duration_seconds=t.duration_seconds,
        compute_device=t.compute_device,
        diarization_method=t.diarization_method,
        processing_time_seconds=t.processing_time_seconds,
        transcription_time_seconds=t.transcription_time_seconds,
        diarization_time_seconds=t.diarization_time_seconds,
        workflow_status=t.workflow_status or "pending",
        workflow_comment=t.workflow_comment,
        llm_operations=llm_operations,
    )


@router.get("/queue", response_model=List[TranscriptionResponse])
async def list_queue(
    db: Session = Depends(get_db),
    limit: Optional[int] = None,
):
    """List transcriptions in reverse chronological order.

    By default returns the full list for the UI. Optional limit is kept for
    ad-hoc callers that want a smaller result set.
    """
    query = db.query(Transcription).order_by(Transcription.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    transcriptions = query.all()
    return [_build_transcription_response(t, db) for t in transcriptions]


class StartRequest(BaseModel):
    """Request model for starting transcriptions."""
    ids: List[str]


class StartResponse(BaseModel):
    """Response model for start operation."""
    started: int
    failed: int


@router.post("/start", response_model=StartResponse)
async def start_transcriptions(
    request: StartRequest,
    db: Session = Depends(get_db),
):
    """Move selected transcriptions from DRAFT to QUEUED status."""
    started = 0
    failed = 0

    for tid in request.ids:
        transcription = db.query(Transcription).filter(
            Transcription.id == tid
        ).first()

        if not transcription:
            failed += 1
            continue

        if transcription.status != TranscriptionStatus.DRAFT:
            failed += 1
            continue

        transcription.status = TranscriptionStatus.QUEUED
        started += 1

    db.commit()
    return StartResponse(started=started, failed=failed)


@router.post("/start-all", response_model=StartResponse)
async def start_all_transcriptions(
    db: Session = Depends(get_db),
):
    """Move ALL draft transcriptions to QUEUED status."""
    result = db.query(Transcription).filter(
        Transcription.status == TranscriptionStatus.DRAFT
    ).update({Transcription.status: TranscriptionStatus.QUEUED})

    db.commit()
    return StartResponse(started=result, failed=0)


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

    return _build_transcription_response(transcription, db)


class TranscriptionUpdate(BaseModel):
    """Request model for updating a transcription."""
    initial_prompt: Optional[str] = None
    workflow_status: Optional[str] = None
    workflow_comment: Optional[str] = None


@router.put("/{transcription_id}", response_model=TranscriptionResponse)
async def update_transcription(
    transcription_id: str,
    update: TranscriptionUpdate,
    db: Session = Depends(get_db),
):
    """Update a transcription's editable fields."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if update.initial_prompt is not None:
        if transcription.status not in [TranscriptionStatus.DRAFT, TranscriptionStatus.QUEUED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update initial_prompt in {transcription.status.value} status"
            )
        transcription.initial_prompt = update.initial_prompt

    if update.workflow_status is not None:
        if update.workflow_status not in {"pending", "processed"}:
            raise HTTPException(status_code=400, detail="workflow_status must be 'pending' or 'processed'")
        transcription.workflow_status = update.workflow_status

    if update.workflow_comment is not None:
        transcription.workflow_comment = update.workflow_comment.strip() or None

    db.commit()
    db.refresh(transcription)

    return _build_transcription_response(transcription, db)


@router.delete("/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Delete a single transcription."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Only allow deleting DRAFT, FAILED, or COMPLETED status
    if transcription.status not in [TranscriptionStatus.DRAFT, TranscriptionStatus.FAILED, TranscriptionStatus.COMPLETED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete transcription in {transcription.status.value} status"
        )

    db.delete(transcription)
    db.commit()
    return {"status": "deleted"}


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

    # Update in transcript files
    if transcription.output_dir:
        output_dir = Path(transcription.output_dir)
        original_data = None
        cleaned_data = None

        # Update transcript.json
        transcript_path = output_dir / "transcript.json"
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)

            for speaker_id, name in update.speaker_names.items():
                if speaker_id in original_data["speakers"]:
                    original_data["speakers"][speaker_id]["name"] = name

            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)

        # Update transcript_cleaned.json if exists
        cleaned_path = output_dir / "transcript_cleaned.json"
        if cleaned_path.exists():
            with open(cleaned_path, "r", encoding="utf-8") as f:
                cleaned_data = json.load(f)

            for speaker_id, name in update.speaker_names.items():
                if speaker_id in cleaned_data.get("speakers", {}):
                    cleaned_data["speakers"][speaker_id]["name"] = name

            with open(cleaned_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        # Regenerate TXT files with updated speaker names
        _regenerate_txt_files(output_dir, original_data, cleaned_data)

    return {"status": "ok"}


@router.get("/{transcription_id}/download/txt")
async def download_transcript_txt(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Download transcript as plain text."""
    from fastapi.responses import FileResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    txt_path = Path(transcription.output_dir) / "transcript.txt"
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail="TXT file not found")

    # Get base filename without extension
    base_name = Path(transcription.filename).stem

    return FileResponse(
        path=txt_path,
        filename=f"{base_name}_original.txt",
        media_type="text/plain",
    )


@router.get("/{transcription_id}/download/json")
async def download_transcript_json(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Download transcript as JSON."""
    from fastapi.responses import FileResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    json_path = Path(transcription.output_dir) / "transcript.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="JSON file not found")

    # Get base filename without extension
    base_name = Path(transcription.filename).stem

    return FileResponse(
        path=json_path,
        filename=f"{base_name}_original.json",
        media_type="application/json",
    )


@router.get("/{transcription_id}/download/raw")
async def download_raw_response(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Download raw API response from cloud provider."""
    from fastapi.responses import FileResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    raw_path = Path(transcription.output_dir) / "raw_response.json"
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Raw response not available (only for cloud engines)")

    return FileResponse(
        path=raw_path,
        filename=f"{transcription.filename}_raw_{transcription.engine}.json",
        media_type="application/json",
    )


@router.api_route("/{transcription_id}/audio", methods=["GET", "HEAD"])
async def stream_original_audio(
    transcription_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Stream the original audio file for transcript playback."""
    from fastapi.responses import FileResponse, StreamingResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    audio_path = _resolve_audio_path(transcription)
    media_type = _get_audio_content_type(audio_path)
    file_size = audio_path.stat().st_size
    base_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }

    byte_range = _parse_range_header(request.headers.get("range"), file_size)
    if byte_range is not None:
        start, end = byte_range
        content_length = end - start + 1
        headers = {
            **base_headers,
            "Content-Length": str(content_length),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
        }
        if request.method == "HEAD":
            return Response(status_code=206, headers=headers, media_type=media_type)
        return StreamingResponse(
            _iter_file_range(audio_path, start, end),
            status_code=206,
            headers=headers,
            media_type=media_type,
        )

    headers = {
        **base_headers,
        "Content-Length": str(file_size),
    }
    if request.method == "HEAD":
        return Response(status_code=200, headers=headers, media_type=media_type)

    return FileResponse(
        path=audio_path,
        media_type=media_type,
        headers=headers,
    )


@router.get("/{transcription_id}/download/cleaned/txt")
async def download_cleaned_txt(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Download cleaned transcript as plain text."""
    from fastapi.responses import FileResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    txt_path = Path(transcription.output_dir) / "transcript_cleaned.txt"
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail="Cleaned transcript not found")

    # Get base filename without extension
    base_name = Path(transcription.filename).stem

    return FileResponse(
        path=txt_path,
        filename=f"{base_name}_cleaned.txt",
        media_type="text/plain",
    )


@router.get("/{transcription_id}/download/cleaned/json")
async def download_cleaned_json(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Download cleaned transcript as JSON."""
    from fastapi.responses import FileResponse

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    json_path = Path(transcription.output_dir) / "transcript_cleaned.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Cleaned transcript not found")

    # Get base filename without extension
    base_name = Path(transcription.filename).stem

    return FileResponse(
        path=json_path,
        filename=f"{base_name}_cleaned.json",
        media_type="application/json",
    )
