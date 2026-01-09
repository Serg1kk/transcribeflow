# workers/transcription_worker.py
"""Main transcription processing worker."""
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from config import Settings, get_settings
from engines import (
    MLXWhisperEngine,
    TranscriptionEngine,
    WhisperSettings,
    AssemblyAIEngine,
    DeepgramEngine,
    ElevenLabsEngine,
    YandexEngine,
)
from models import Transcription, TranscriptionStatus
# Lazy imports to avoid loading PyTorch before MLX transcription
# from workers.diarization import DiarizationWorker
# from workers.whisperx_diarization import WhisperXDiarizationWorker


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
            elif engine_name == "assemblyai":
                self._engines[engine_name] = AssemblyAIEngine(
                    api_key=self.settings.assemblyai_api_key
                )
            elif engine_name == "deepgram":
                self._engines[engine_name] = DeepgramEngine(
                    api_key=self.settings.deepgram_api_key
                )
            elif engine_name == "elevenlabs":
                self._engines[engine_name] = ElevenLabsEngine(
                    api_key=self.settings.elevenlabs_api_key
                )
            elif engine_name == "yandex":
                self._engines[engine_name] = YandexEngine(
                    api_key=self.settings.yandex_api_key
                )
            else:
                raise ValueError(f"Unknown engine: {engine_name}")
        return self._engines[engine_name]

    def get_diarization_worker(self):
        """Get or create the diarization worker (lazy import to avoid PyTorch loading)."""
        if self._diarization_worker is None:
            # Lazy import to avoid loading PyTorch before MLX transcription completes
            from workers.diarization import DiarizationWorker
            self._diarization_worker = DiarizationWorker(
                hf_token=self.settings.hf_token,
                min_speakers=self.settings.min_speakers,
                max_speakers=self.settings.max_speakers,
                device=self.settings.compute_device,
            )
        return self._diarization_worker

    def get_whisperx_worker(self):
        """Get or create the WhisperX diarization worker (lazy import to avoid PyTorch loading)."""
        if not hasattr(self, '_whisperx_worker') or self._whisperx_worker is None:
            # Lazy import to avoid loading PyTorch before MLX transcription completes
            from workers.whisperx_diarization import WhisperXDiarizationWorker
            self._whisperx_worker = WhisperXDiarizationWorker(
                hf_token=self.settings.hf_token,
                min_speakers=self.settings.min_speakers,
                max_speakers=self.settings.max_speakers,
            )
        return self._whisperx_worker

    def get_whisper_settings(self) -> WhisperSettings:
        """Get Whisper anti-hallucination settings from config."""
        return WhisperSettings(
            no_speech_threshold=self.settings.whisper_no_speech_threshold,
            logprob_threshold=self.settings.whisper_logprob_threshold,
            compression_ratio_threshold=self.settings.whisper_compression_ratio_threshold,
            hallucination_silence_threshold=self.settings.whisper_hallucination_silence_threshold,
            condition_on_previous_text=self.settings.whisper_condition_on_previous_text,
            initial_prompt=self.settings.whisper_initial_prompt,
        )

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

            total_start_time = time.time()

            audio_path = Path(transcription.original_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Step 1: Transcribe with ASR engine
            transcription_start_time = time.time()
            engine = self.get_engine(transcription.engine)

            # Only MLX Whisper uses the settings parameter
            if transcription.engine == "mlx-whisper":
                whisper_settings = self.get_whisper_settings()
                # Override with per-file initial_prompt if set
                if transcription.initial_prompt:
                    whisper_settings.initial_prompt = transcription.initial_prompt

                result = engine.transcribe(
                    audio_path=audio_path,
                    model=transcription.model,
                    language=transcription.language,
                    settings=whisper_settings,
                )
            else:
                # Cloud engines don't use Whisper settings
                result = engine.transcribe(
                    audio_path=audio_path,
                    model=transcription.model,
                    language=transcription.language,
                )
            transcription_time = time.time() - transcription_start_time

            transcription.progress = 50.0
            db.commit()

            # Step 2: Speaker diarization
            segments = result.segments
            speakers_count = 1
            diarization_time = 0.0

            # Check if engine supports built-in diarization
            from engines.registry import PROVIDERS
            engine_info = PROVIDERS.get(transcription.engine, {})

            diarization_method = self.settings.diarization_method

            if diarization_method != "none":
                if engine_info.get("supports_diarization"):
                    # Cloud engine already did diarization - count speakers from segments
                    speaker_ids = set(seg.get("speaker", "SPEAKER_00") for seg in segments)
                    speakers_count = len(speaker_ids)
                elif diarization_method == "fast":
                    # Fast: Pyannote on MPS/GPU
                    transcription.status = TranscriptionStatus.DIARIZING
                    db.commit()

                    diarization_worker = self.get_diarization_worker()
                    if diarization_worker.is_available():
                        diarization_start_time = time.time()

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
                        diarization_time = time.time() - diarization_start_time

                elif diarization_method == "accurate":
                    # Accurate: WhisperX alignment + diarization
                    transcription.status = TranscriptionStatus.DIARIZING
                    db.commit()

                    whisperx_worker = self.get_whisperx_worker()
                    if whisperx_worker.is_available():
                        diarization_start_time = time.time()

                        num_speakers = None
                        if transcription.min_speakers == transcription.max_speakers:
                            num_speakers = transcription.min_speakers

                        whisperx_result = whisperx_worker.diarize_with_alignment(
                            audio_path=audio_path,
                            segments=result.segments,
                            language=result.language,
                            num_speakers=num_speakers,
                        )

                        segments = whisperx_result.segments
                        speakers_count = len(whisperx_result.speakers)
                        diarization_time = whisperx_result.processing_time_seconds

            transcription.progress = 80.0
            db.commit()

            total_processing_time = time.time() - total_start_time

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
                processing_time=total_processing_time,
                transcription_time=transcription_time,
                diarization_time=diarization_time,
                raw_response=result.raw_response,
            )

            # Update transcription record
            transcription.output_dir = str(output_dir)
            transcription.duration_seconds = result.duration_seconds
            transcription.speakers_count = speakers_count
            transcription.language_detected = result.language
            transcription.processing_time_seconds = total_processing_time
            transcription.transcription_time_seconds = transcription_time
            transcription.diarization_time_seconds = diarization_time if diarization_time > 0 else None
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
        transcription_time: float = 0.0,
        diarization_time: float = 0.0,
        raw_response: dict = None,
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
                "processing_time_seconds": round(processing_time, 2),
                "transcription_time_seconds": round(transcription_time, 2),
                "diarization_time_seconds": round(diarization_time, 2) if diarization_time > 0 else None,
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

        # Save raw API response (for cloud engines)
        if raw_response:
            raw_path = output_dir / "raw_response.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_response, f, ensure_ascii=False, indent=2)

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
        speakers_dict = data["speakers"]

        # Check if diarization was disabled (only SPEAKER_UNKNOWN)
        has_real_speakers = len(speakers_dict) > 1 or (
            len(speakers_dict) == 1 and "SPEAKER_UNKNOWN" not in speakers_dict
        )

        # Build header
        lines = [
            f"Transcription: {meta['filename']}",
            f"Date: {meta['created_at'][:10]}",
            f"Duration: {self._format_duration(meta['duration_seconds'])}",
        ]

        if has_real_speakers:
            participants = ', '.join(s['name'] for s in speakers_dict.values())
            lines.append(f"Participants: {participants}")

        lines.extend(["", "-" * 40, ""])

        # Format segments
        for seg in data["segments"]:
            timestamp = self._format_timestamp(seg["start"])
            text = seg["text"]

            if has_real_speakers:
                speaker = speakers_dict.get(seg.get("speaker", ""), {}).get("name", "Unknown")
                lines.append(f"[{timestamp}] {speaker}: {text}")
            else:
                # No diarization - just timestamp and text
                lines.append(f"[{timestamp}] {text}")
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
