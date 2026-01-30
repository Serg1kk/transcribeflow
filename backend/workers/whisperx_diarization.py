# workers/whisperx_diarization.py
"""WhisperX-based diarization with word-level alignment."""
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Workaround for PyTorch 2.6 weights_only=True default change
# Pyannote models need weights_only=False to load properly
try:
    import torch
    _original_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load
except ImportError:
    pass

# Formats that torchaudio/soundfile can read directly
NATIVE_FORMATS = {'.wav', '.flac', '.ogg', '.mp3', '.aiff', '.au'}


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

    def unload_models(self):
        """Unload all cached models to free memory."""
        import gc
        
        if self._align_model is not None:
            del self._align_model
            self._align_model = None
            self._align_metadata = None
            self._current_language = None
        
        if self._diarize_model is not None:
            del self._diarize_model
            self._diarize_model = None
        
        # Force garbage collection
        gc.collect()
        
        # Clear PyTorch cache if available
        try:
            import torch
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass

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
            from pyannote.audio import Pipeline
            self._diarize_model = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
            )
            # Keep on CPU for accurate mode
        return self._diarize_model

    def _load_audio(self, audio_path: Path) -> Tuple[Any, int, Optional[str]]:
        """Load audio, converting if needed. Returns (waveform, sample_rate, temp_path)."""
        import os
        import torchaudio

        suffix = audio_path.suffix.lower()
        temp_path = None

        if suffix in NATIVE_FORMATS:
            waveform, sample_rate = torchaudio.load(str(audio_path))
            return waveform, sample_rate, None

        # For unsupported formats (m4a, webm, etc.), convert using ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            temp_path = tmp_file.name

        result = subprocess.run(
            [
                'ffmpeg', '-y', '-i', str(audio_path),
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # Mono
                '-f', 'wav',
                temp_path
            ],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

        waveform, sample_rate = torchaudio.load(temp_path)
        return waveform, sample_rate, temp_path

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
        import os
        import numpy as np
        import pandas as pd
        import whisperx

        if not self.is_available():
            raise RuntimeError("WhisperX is not available or HF token not set")

        start_time = time.time()

        # Convert segments to whisperx format
        whisperx_segments = []
        for seg in segments:
            whisperx_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })

        # Load audio (handles m4a conversion via ffmpeg)
        waveform, sample_rate, temp_path = self._load_audio(audio_path)

        try:
            # Step 1: Align segments to get word-level timestamps
            align_model, metadata = self._load_align_model(language)
            # Convert to numpy for whisperx.align (expects mono float32)
            audio_np = waveform.squeeze().numpy()
            if waveform.shape[0] > 1:  # stereo to mono
                audio_np = waveform.mean(dim=0).numpy()

            aligned = whisperx.align(
                whisperx_segments,
                align_model,
                metadata,
                audio_np,
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

            # Use preloaded audio dict (workaround for torchcodec issue)
            audio_input = {"waveform": waveform, "sample_rate": sample_rate}
            diarization = diarize_model(audio_input, **diarize_params)

            # Convert pyannote Annotation to DataFrame for whisperx
            # pyannote 4.x returns DiarizeOutput, extract the Annotation
            annotation = diarization.speaker_diarization if hasattr(diarization, 'speaker_diarization') else diarization
            diarize_df = pd.DataFrame(
                annotation.itertracks(yield_label=True),
                columns=['segment', 'label', 'speaker']
            )
            diarize_df['start'] = diarize_df['segment'].apply(lambda x: x.start)
            diarize_df['end'] = diarize_df['segment'].apply(lambda x: x.end)

            # Step 3: Assign speakers to words
            result = whisperx.assign_word_speakers(diarize_df, aligned)

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

        finally:
            # Clean up temp file if created
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
