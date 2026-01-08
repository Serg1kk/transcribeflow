# engines/mlx_whisper.py
"""MLX Whisper transcription engine for Apple Silicon."""
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from engines.base import TranscriptionEngine, TranscriptionResult


@dataclass
class WhisperSettings:
    """Anti-hallucination settings for Whisper transcription."""
    no_speech_threshold: float = 0.6
    logprob_threshold: float = -1.0
    compression_ratio_threshold: float = 2.4
    hallucination_silence_threshold: Optional[float] = 2.0
    condition_on_previous_text: bool = True
    initial_prompt: Optional[str] = None

# Model name to HuggingFace repo mapping
# Some models have -mlx suffix, some don't
MODEL_REPOS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-mlx",
    "large-v1": "mlx-community/whisper-large-v1-mlx",
    "large-v2": "mlx-community/whisper-large-v2-mlx-8bit",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "turbo": "mlx-community/whisper-turbo",
}


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
        settings: Optional[WhisperSettings] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using MLX Whisper.

        Args:
            audio_path: Path to the audio file
            model: Model name (large-v2, large-v3-turbo, etc.)
            language: Language code or None for auto-detect
            settings: Anti-hallucination settings (optional)

        Returns:
            TranscriptionResult with transcription data
        """
        if not self.is_available():
            raise RuntimeError("mlx-whisper is not installed")

        start_time = time.time()

        # Use default settings if not provided
        if settings is None:
            settings = WhisperSettings()

        # Build transcription options
        options = {
            "word_timestamps": True,
            # Anti-hallucination parameters
            "no_speech_threshold": settings.no_speech_threshold,
            "logprob_threshold": settings.logprob_threshold,
            "compression_ratio_threshold": settings.compression_ratio_threshold,
            "condition_on_previous_text": settings.condition_on_previous_text,
        }

        # Optional parameters
        if language:
            options["language"] = language
        if settings.hallucination_silence_threshold is not None:
            options["hallucination_silence_threshold"] = settings.hallucination_silence_threshold
        if settings.initial_prompt:
            options["initial_prompt"] = settings.initial_prompt

        # Get the correct HuggingFace repo for the model
        repo = MODEL_REPOS.get(model)
        if not repo:
            # Fallback to standard naming pattern
            repo = f"mlx-community/whisper-{model}-mlx"

        # Run transcription
        result = self._mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=repo,
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
