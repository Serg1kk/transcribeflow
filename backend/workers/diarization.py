# workers/diarization.py
"""Speaker diarization using Pyannote Audio."""
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

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

# Workaround for torchaudio compatibility issue
# Newer versions removed set_audio_backend, but pyannote may try to use it
try:
    import torchaudio
    if not hasattr(torchaudio, 'set_audio_backend'):
        # Add a no-op stub for compatibility
        torchaudio.set_audio_backend = lambda x: None
except ImportError:
    pass

# Formats that soundfile can read directly (no conversion needed)
NATIVE_FORMATS = {'.wav', '.flac', '.ogg', '.mp3', '.aiff', '.au'}


@dataclass
class DiarizationResult:
    """Result from speaker diarization."""
    speakers: Set[str]
    segments: List[Dict[str, Any]]
    processing_time_seconds: float = 0.0


class DiarizationWorker:
    """Speaker diarization using Pyannote Audio 3.1."""

    def __init__(
        self,
        hf_token: Optional[str] = None,
        min_speakers: int = 2,
        max_speakers: int = 6,
        device: str = "auto",
    ):
        self.hf_token = hf_token
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.device = device
        self._pipeline = None

    def _resolve_device(self) -> str:
        """Resolve 'auto' to actual device, return 'cpu' or 'mps'."""
        if self.device == "auto":
            import torch
            if torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return self.device

    def is_available(self) -> bool:
        """Check if pyannote is installed and token is set."""
        try:
            from pyannote.audio import Pipeline
            return self.hf_token is not None
        except ImportError:
            return False

    def _load_pipeline(self):
        """Lazy load the diarization pipeline with device support."""
        if self._pipeline is None:
            import torch
            from pyannote.audio import Pipeline

            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token
            )

            # Move to device (MPS or CPU)
            resolved_device = self._resolve_device()
            if resolved_device == "mps":
                self._pipeline.to(torch.device("mps"))
            # CPU is default, no need to move

        return self._pipeline

    def _load_audio(self, audio_path: Path) -> Dict[str, Any]:
        """Load audio using torchaudio (workaround for torchcodec/FFmpeg 8 issue).

        For formats not supported by soundfile (like m4a/AAC), uses ffmpeg to convert first.
        Returns audio as a dict with waveform and sample_rate that pyannote accepts.
        """
        suffix = audio_path.suffix.lower()

        if suffix in NATIVE_FORMATS:
            # Direct loading for supported formats
            waveform, sample_rate = torchaudio.load(str(audio_path))
            return {"waveform": waveform, "sample_rate": sample_rate}

        # For unsupported formats (m4a, webm, etc.), convert using ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Convert to 16kHz mono WAV using ffmpeg
            result = subprocess.run(
                [
                    'ffmpeg', '-y', '-i', str(audio_path),
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',      # Mono
                    '-f', 'wav',
                    tmp_path
                ],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

            waveform, sample_rate = torchaudio.load(tmp_path)
            return {"waveform": waveform, "sample_rate": sample_rate}
        finally:
            # Cleanup temp file
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def diarize(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
    ) -> DiarizationResult:
        """Run speaker diarization on an audio file.

        Args:
            audio_path: Path to the audio file
            num_speakers: Exact number of speakers (optional)

        Returns:
            DiarizationResult with speaker segments
        """
        if not self.is_available():
            raise RuntimeError("Pyannote is not available or HF token not set")

        start_time = time.time()
        pipeline = self._load_pipeline()

        # Configure speaker count
        params = {}
        if num_speakers:
            params["num_speakers"] = num_speakers
        else:
            params["min_speakers"] = self.min_speakers
            params["max_speakers"] = self.max_speakers

        # Load audio with torchaudio (workaround for torchcodec/FFmpeg 8 incompatibility)
        # pyannote 4.x requires torchcodec which doesn't support FFmpeg 8
        audio_input = self._load_audio(audio_path)

        # Run diarization with preloaded audio
        diarization = pipeline(audio_input, **params)

        # Extract segments - pyannote 4.x returns DiarizeOutput with .speaker_diarization
        segments = []
        speakers = set()

        # Handle both pyannote 3.x (itertracks) and 4.x (speaker_diarization) APIs
        if hasattr(diarization, 'speaker_diarization'):
            # pyannote 4.x API
            for turn, speaker in diarization.speaker_diarization:
                speakers.add(speaker)
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                })
        else:
            # pyannote 3.x API (fallback)
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.add(speaker)
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                })

        processing_time = time.time() - start_time

        return DiarizationResult(
            speakers=speakers,
            segments=segments,
            processing_time_seconds=processing_time,
        )

    def merge_transcription_with_diarization(
        self,
        transcription_segments: List[Dict],
        diarization_result: DiarizationResult,
    ) -> List[Dict]:
        """Merge transcription segments with speaker labels.

        Assigns speaker labels to transcription segments based on
        overlap with diarization segments.

        Args:
            transcription_segments: Segments from ASR engine
            diarization_result: Result from diarization

        Returns:
            Transcription segments with speaker labels added
        """
        merged = []
        for trans_seg in transcription_segments:
            trans_start = trans_seg["start"]
            trans_end = trans_seg["end"]

            # Find overlapping diarization segment
            best_speaker = "SPEAKER_UNKNOWN"
            best_overlap = 0

            for diar_seg in diarization_result.segments:
                diar_start = diar_seg["start"]
                diar_end = diar_seg["end"]

                # Calculate overlap
                overlap_start = max(trans_start, diar_start)
                overlap_end = min(trans_end, diar_end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar_seg["speaker"]

            merged_seg = {**trans_seg, "speaker": best_speaker}
            merged.append(merged_seg)

        return merged
