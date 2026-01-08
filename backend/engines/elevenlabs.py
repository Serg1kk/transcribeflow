# engines/elevenlabs.py
"""ElevenLabs Scribe transcription engine."""
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from engines.base import TranscriptionEngine, TranscriptionResult


class ElevenLabsEngine(TranscriptionEngine):
    """ElevenLabs Scribe cloud transcription engine."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "elevenlabs"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def validate_api_key(self) -> Dict[str, Any]:
        """Validate API key by making a test request."""
        if not self.api_key:
            return {"valid": False, "error": "No API key provided"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user",
                headers={"xi-api-key": self.api_key},
            )

            if response.status_code == 200:
                return {"valid": True}
            else:
                return {"valid": False, "error": response.text}

    def transcribe(
        self,
        audio_path: Path,
        model: str = "scribe_v1",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using ElevenLabs Scribe API."""
        return asyncio.run(self._transcribe_async(audio_path, model, language))

    async def _transcribe_async(
        self,
        audio_path: Path,
        model: str = "scribe_v1",
        language: Optional[str] = None,
        diarization: bool = True,
    ) -> TranscriptionResult:
        """Async transcription implementation."""
        if not self.is_available():
            raise RuntimeError("ElevenLabs API key not configured")

        start_time = time.time()

        headers = {"xi-api-key": self.api_key}

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Upload and transcribe in one request
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, self._get_content_type(audio_path))}
                data = {
                    "model_id": model,
                    "tag_audio_events": "true",
                    "diarize": str(diarization).lower(),
                }

                response = await client.post(
                    f"{self.BASE_URL}/speech-to-text",
                    headers=headers,
                    files=files,
                    data=data,
                )

            response.raise_for_status()
            result = response.json()

        processing_time = time.time() - start_time

        # Parse response - ElevenLabs returns text and words array
        full_text = result.get("text", "")
        raw_words = result.get("words", [])

        # Build words list (filter out spacing and audio events)
        words = []
        for w in raw_words:
            if w.get("type") == "word":
                words.append({
                    "word": w.get("text", ""),
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                    "confidence": abs(w.get("logprob", 0)),  # logprob is negative
                    "speaker": w.get("speaker_id", "speaker_0"),
                })

        # Build segments by grouping consecutive words by speaker
        segments = []
        if words:
            current_segment = {
                "start": words[0]["start"],
                "end": words[0]["end"],
                "text": words[0]["word"],
                "speaker": self._format_speaker_id(words[0].get("speaker")),
                "confidence": words[0]["confidence"],
            }

            for word in words[1:]:
                word_speaker = self._format_speaker_id(word.get("speaker"))
                if word_speaker == current_segment["speaker"]:
                    # Same speaker - extend segment
                    current_segment["end"] = word["end"]
                    current_segment["text"] += " " + word["word"]
                else:
                    # New speaker - save current and start new
                    segments.append(current_segment)
                    current_segment = {
                        "start": word["start"],
                        "end": word["end"],
                        "text": word["word"],
                        "speaker": word_speaker,
                        "confidence": word["confidence"],
                    }

            # Don't forget last segment
            segments.append(current_segment)

        # Calculate duration from last word
        duration = words[-1]["end"] if words else 0

        return TranscriptionResult(
            text=full_text,
            segments=segments,
            words=[{"word": w["word"], "start": w["start"], "end": w["end"], "confidence": w["confidence"]} for w in words],
            language=result.get("language_code", "unknown"),
            duration_seconds=duration,
            processing_time_seconds=processing_time,
            raw_response=result,  # Original ElevenLabs response
        )

    def _format_speaker_id(self, speaker_id: Optional[str]) -> str:
        """Format speaker ID to standard format (SPEAKER_00, SPEAKER_01, etc.)"""
        if not speaker_id:
            return "SPEAKER_00"
        # ElevenLabs returns "speaker_0", "speaker_1" etc.
        if speaker_id.startswith("speaker_"):
            num = speaker_id.replace("speaker_", "")
            try:
                return f"SPEAKER_{int(num):02d}"
            except ValueError:
                return "SPEAKER_00"
        return speaker_id

    def _get_content_type(self, audio_path: Path) -> str:
        """Get content type based on file extension."""
        ext = audio_path.suffix.lower()
        content_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
        }
        return content_types.get(ext, "audio/mpeg")
