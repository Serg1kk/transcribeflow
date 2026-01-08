# workers/diarization.py
"""Speaker diarization using Pyannote Audio."""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


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
    ):
        self.hf_token = hf_token
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self._pipeline = None

    def is_available(self) -> bool:
        """Check if pyannote is installed and token is set."""
        try:
            from pyannote.audio import Pipeline
            return self.hf_token is not None
        except ImportError:
            return False

    def _load_pipeline(self):
        """Lazy load the diarization pipeline."""
        if self._pipeline is None:
            from pyannote.audio import Pipeline
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token
            )
        return self._pipeline

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

        # Run diarization
        diarization = pipeline(str(audio_path), **params)

        # Extract segments
        segments = []
        speakers = set()
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
