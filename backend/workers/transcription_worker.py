# workers/transcription_worker.py
"""Main transcription processing worker."""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from config import Settings, get_settings
from engines import MLXWhisperEngine, TranscriptionEngine
from models import Transcription, TranscriptionStatus
from workers.diarization import DiarizationWorker


class TranscriptionWorker:
    """Worker that processes transcription tasks from the queue."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._engines: Dict[str, TranscriptionEngine] = {}
        self._diarization_worker: Optional[DiarizationWorker] = None

    def get_engine(self, engine_name: str) -> TranscriptionEngine:
        """Get or create a transcription engine by name."""
        if engine_name not in self._engines:
            if engine_name == "mlx-whisper":
                self._engines[engine_name] = MLXWhisperEngine()
            else:
                raise ValueError(f"Unknown engine: {engine_name}")
        return self._engines[engine_name]

    def get_diarization_worker(self) -> DiarizationWorker:
        """Get or create the diarization worker."""
        if self._diarization_worker is None:
            self._diarization_worker = DiarizationWorker(
                hf_token=self.settings.hf_token,
                min_speakers=self.settings.min_speakers,
                max_speakers=self.settings.max_speakers,
            )
        return self._diarization_worker

    def process(self, transcription: Transcription, db: Session) -> bool:
        """Process a single transcription task.

        Args:
            transcription: The transcription record to process
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update status to processing
            transcription.status = TranscriptionStatus.PROCESSING
            transcription.started_at = datetime.utcnow()
            db.commit()

            audio_path = Path(transcription.original_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Step 1: Transcribe with ASR engine
            engine = self.get_engine(transcription.engine)
            result = engine.transcribe(
                audio_path=audio_path,
                model=transcription.model,
                language=transcription.language,
            )

            transcription.progress = 50.0
            db.commit()

            # Step 2: Speaker diarization (if enabled and available)
            segments = result.segments
            speakers_count = 1

            if self.settings.diarization_enabled:
                transcription.status = TranscriptionStatus.DIARIZING
                db.commit()

                diarization_worker = self.get_diarization_worker()
                if diarization_worker.is_available():
                    num_speakers = None
                    if transcription.min_speakers == transcription.max_speakers:
                        num_speakers = transcription.min_speakers

                    diarization_result = diarization_worker.diarize(
                        audio_path=audio_path,
                        num_speakers=num_speakers,
                    )

                    segments = diarization_worker.merge_transcription_with_diarization(
                        result.segments, diarization_result
                    )
                    speakers_count = len(diarization_result.speakers)

            transcription.progress = 80.0
            db.commit()

            # Step 3: Save results
            output_dir = self._create_output_directory(transcription, audio_path)
            self._save_results(
                output_dir=output_dir,
                transcription=transcription,
                text=result.text,
                segments=segments,
                words=result.words,
                language=result.language,
                duration=result.duration_seconds,
                speakers_count=speakers_count,
                processing_time=result.processing_time_seconds,
            )

            # Update transcription record
            transcription.output_dir = str(output_dir)
            transcription.duration_seconds = result.duration_seconds
            transcription.speakers_count = speakers_count
            transcription.language_detected = result.language
            transcription.processing_time_seconds = result.processing_time_seconds
            transcription.status = TranscriptionStatus.COMPLETED
            transcription.completed_at = datetime.utcnow()
            transcription.progress = 100.0
            db.commit()

            return True

        except Exception as e:
            transcription.status = TranscriptionStatus.FAILED
            transcription.error_message = str(e)
            db.commit()
            return False

    def _create_output_directory(
        self, transcription: Transcription, audio_path: Path
    ) -> Path:
        """Create output directory for transcription results."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        stem = audio_path.stem
        dir_name = f"{date_str}_{stem}"

        output_dir = self.settings.transcribed_path / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy original audio to output directory
        shutil.copy2(audio_path, output_dir / audio_path.name)

        return output_dir

    def _save_results(
        self,
        output_dir: Path,
        transcription: Transcription,
        text: str,
        segments: list,
        words: list,
        language: str,
        duration: float,
        speakers_count: int,
        processing_time: float,
    ):
        """Save transcription results to files."""
        # Build transcript.json
        transcript_data = {
            "metadata": {
                "id": transcription.id,
                "filename": transcription.filename,
                "duration_seconds": duration,
                "created_at": datetime.utcnow().isoformat(),
                "engine": transcription.engine,
                "model": transcription.model,
                "language": language,
            },
            "speakers": self._build_speakers_dict(segments),
            "segments": segments,
            "words": words,
            "stats": {
                "total_words": len(words),
                "speakers_count": speakers_count,
                "language_detected": language,
                "processing_time_seconds": processing_time,
            },
        }

        # Save JSON
        json_path = output_dir / "transcript.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)

        # Save human-readable TXT
        txt_path = output_dir / "transcript.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self._format_transcript_txt(transcript_data))

    def _build_speakers_dict(self, segments: list) -> dict:
        """Build speakers dictionary with default names and colors."""
        colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
        speakers = {}

        for seg in segments:
            speaker_id = seg.get("speaker", "SPEAKER_UNKNOWN")
            if speaker_id not in speakers:
                idx = len(speakers)
                speakers[speaker_id] = {
                    "name": speaker_id,
                    "color": colors[idx % len(colors)],
                }

        return speakers

    def _format_transcript_txt(self, data: dict) -> str:
        """Format transcript as human-readable text."""
        meta = data["metadata"]
        lines = [
            f"Transcription: {meta['filename']}",
            f"Date: {meta['created_at'][:10]}",
            f"Duration: {self._format_duration(meta['duration_seconds'])}",
            f"Participants: {', '.join(s['name'] for s in data['speakers'].values())}",
            "",
            "-" * 40,
            "",
        ]

        speakers_dict = data["speakers"]
        for seg in data["segments"]:
            timestamp = self._format_timestamp(seg["start"])
            speaker = speakers_dict.get(seg.get("speaker", ""), {}).get("name", "Unknown")
            text = seg["text"]
            lines.append(f"[{timestamp}] {speaker}: {text}")
            lines.append("")

        lines.append("-" * 40)
        return "\n".join(lines)

    def _format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS or HH:MM:SS."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp as HH:MM:SS."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
