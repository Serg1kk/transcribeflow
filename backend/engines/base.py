# engines/base.py
"""Base class for transcription engines."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class TranscriptionResult:
    """Result from a transcription engine."""
    text: str
    segments: List[Dict[str, Any]]
    language: str
    duration_seconds: float
    words: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_seconds: float = 0.0


class TranscriptionEngine(ABC):
    """Abstract base class for transcription engines."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        model: str = "large-v2",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file
            model: Model name to use
            language: Language code or None for auto-detect

        Returns:
            TranscriptionResult with text, segments, and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available and properly configured."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name identifier."""
        pass
