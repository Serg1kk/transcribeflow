# models/llm_operation.py
"""LLM operation tracking model."""
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, Text, ForeignKey
from models.database import Base


class LLMOperationStatus(enum.Enum):
    """Status of an LLM operation."""
    SUCCESS = "success"
    FAILED = "failed"


class LLMOperation(Base):
    """LLM post-processing operation model."""
    __tablename__ = "llm_operations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String(36), ForeignKey("transcriptions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # LLM Configuration
    provider = Column(String(50), nullable=False)  # "gemini" | "openrouter"
    model = Column(String(100), nullable=False)  # "gemini-2.5-flash"
    template_id = Column(String(100), nullable=False)  # "it-meeting"
    temperature = Column(Float, nullable=False)

    # Token Usage
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Float, nullable=True)  # NULL if price not configured

    # Processing Info
    processing_time_seconds = Column(Float, nullable=False)
    status = Column(Enum(LLMOperationStatus), nullable=False)
    error_message = Column(Text, nullable=True)
