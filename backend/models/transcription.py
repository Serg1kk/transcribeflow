# models/transcription.py
"""Transcription database model."""
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Enum, DateTime, Text, JSON
from models.database import Base


class TranscriptionStatus(enum.Enum):
    """Status of a transcription task."""
    QUEUED = "queued"
    PROCESSING = "processing"
    DIARIZING = "diarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(Base):
    """Transcription task model."""
    __tablename__ = "transcriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=False)
    output_dir = Column(String(500), nullable=True)

    # Processing settings
    engine = Column(String(50), nullable=False, default="mlx-whisper")
    model = Column(String(100), nullable=False, default="large-v2")
    language = Column(String(10), nullable=True)  # None = auto-detect
    min_speakers = Column(Integer, nullable=True)
    max_speakers = Column(Integer, nullable=True)

    # Status & progress
    status = Column(Enum(TranscriptionStatus), default=TranscriptionStatus.QUEUED)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    # Results
    duration_seconds = Column(Float, nullable=True)
    speakers_count = Column(Integer, nullable=True)
    language_detected = Column(String(10), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Speaker name mappings (JSON: {"SPEAKER_00": "Ivan", ...})
    speaker_names = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
