# engines/mlx_whisper.py
"""MLX Whisper transcription engine for Apple Silicon."""
import time
from pathlib import Path
from typing import Optional

from engines.base import TranscriptionEngine, TranscriptionResult


class MLXWhisperEngine(TranscriptionEngine):
    """MLX-optimized Whisper engine for Apple Silicon Macs."""

    def __init__(self):
        self._mlx_whisper = None

    @property
    def name(self) -> str:
        return "mlx-whisper"

    def is_available(self) -> bool:
        """Check if mlx-whisper is installed and working."""
        try:
            import mlx_whisper
            self._mlx_whisper = mlx_whisper
            return True
        except ImportError:
            return False

    def transcribe(
        self,
        audio_path: Path,
        model: str = "large-v2",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using MLX Whisper.

        Args:
            audio_path: Path to the audio file
            model: Model name (large-v2, large-v3-turbo, etc.)
            language: Language code or None for auto-detect

        Returns:
            TranscriptionResult with transcription data
        """
        if not self.is_available():
            raise RuntimeError("mlx-whisper is not installed")

        start_time = time.time()

        # Build transcription options
        options = {"word_timestamps": True}
        if language:
            options["language"] = language

        # Run transcription
        result = self._mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{model}-mlx",
            **options
        )

        processing_time = time.time() - start_time

        # Extract segments with word-level timestamps
        segments = []
        all_words = []
        for segment in result.get("segments", []):
            seg_data = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": segment.get("confidence", 0.0),
            }
            segments.append(seg_data)

            # Extract word-level data
            for word in segment.get("words", []):
                all_words.append({
                    "word": word["word"].strip(),
                    "start": word["start"],
                    "end": word["end"],
                    "confidence": word.get("confidence", 0.0),
                })

        # Calculate duration from last segment
        duration = segments[-1]["end"] if segments else 0.0

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            segments=segments,
            words=all_words,
            language=result.get("language", language or "unknown"),
            duration_seconds=duration,
            processing_time_seconds=processing_time,
        )
