# workers/whisperx_diarization.py
"""WhisperX-based diarization with word-level alignment."""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class WhisperXDiarizationResult:
    """Result from WhisperX diarization with word-level alignment."""
    speakers: Set[str]
    segments: List[Dict[str, Any]]
    words: List[Dict[str, Any]]
    processing_time_seconds: float = 0.0


class WhisperXDiarizationWorker:
    """Speaker diarization using WhisperX for word-level alignment."""

    def __init__(
        self,
        hf_token: Optional[str] = None,
        min_speakers: int = 2,
        max_speakers: int = 6,
    ):
        self.hf_token = hf_token
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self._align_model = None
        self._align_metadata = None
        self._diarize_model = None
        self._current_language = None

    def is_available(self) -> bool:
        """Check if whisperx is installed and token is set."""
        try:
            import whisperx
            return self.hf_token is not None
        except ImportError:
            return False

    def _load_align_model(self, language: str):
        """Lazy load the alignment model."""
        if self._align_model is None or self._current_language != language:
            import whisperx
            self._align_model, self._align_metadata = whisperx.load_align_model(
                language_code=language,
                device="cpu"  # WhisperX alignment works on CPU
            )
            self._current_language = language
        return self._align_model, self._align_metadata

    def _load_diarize_model(self):
        """Lazy load the diarization model."""
        if self._diarize_model is None:
            import whisperx
            self._diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=self.hf_token,
                device="cpu"  # WhisperX diarization on CPU
            )
        return self._diarize_model

    def diarize_with_alignment(
        self,
        audio_path: Path,
        segments: List[Dict[str, Any]],
        language: str,
        num_speakers: Optional[int] = None,
    ) -> WhisperXDiarizationResult:
        """Run alignment and diarization on pre-transcribed segments.

        Args:
            audio_path: Path to the audio file
            segments: Transcription segments from MLX Whisper
            language: Detected/specified language code
            num_speakers: Exact number of speakers (optional)

        Returns:
            WhisperXDiarizationResult with word-level speaker labels
        """
        if not self.is_available():
            raise RuntimeError("WhisperX is not available or HF token not set")

        import whisperx

        start_time = time.time()

        # Convert segments to whisperx format
        whisperx_segments = []
        for seg in segments:
            whisperx_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })

        # Step 1: Align segments to get word-level timestamps
        align_model, metadata = self._load_align_model(language)
        audio = whisperx.load_audio(str(audio_path))
        aligned = whisperx.align(
            whisperx_segments,
            align_model,
            metadata,
            audio,
            device="cpu",
            return_char_alignments=False,
        )

        # Step 2: Run diarization
        diarize_model = self._load_diarize_model()

        diarize_params = {}
        if num_speakers:
            diarize_params["num_speakers"] = num_speakers
        else:
            diarize_params["min_speakers"] = self.min_speakers
            diarize_params["max_speakers"] = self.max_speakers

        diarize_segments = diarize_model(audio, **diarize_params)

        # Step 3: Assign speakers to words
        result = whisperx.assign_word_speakers(diarize_segments, aligned)

        # Extract results
        speakers = set()
        output_segments = []
        output_words = []

        for seg in result.get("segments", []):
            speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
            speakers.add(speaker)

            output_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "speaker": speaker,
            })

            for word in seg.get("words", []):
                word_speaker = word.get("speaker", speaker)
                output_words.append({
                    "word": word.get("word", ""),
                    "start": word.get("start", 0),
                    "end": word.get("end", 0),
                    "speaker": word_speaker,
                })

        processing_time = time.time() - start_time

        return WhisperXDiarizationResult(
            speakers=speakers,
            segments=output_segments,
            words=output_words,
            processing_time_seconds=processing_time,
        )
