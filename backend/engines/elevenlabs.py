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

        # Parse response - ElevenLabs returns utterances with speaker info
        segments = []
        words = []

        for utterance in result.get("utterances", []):
            speaker_id = f"SPEAKER_{utterance.get('speaker_id', 0):02d}"

            segments.append({
                "start": utterance["start"],
                "end": utterance["end"],
                "text": utterance["text"],
                "speaker": speaker_id,
                "confidence": utterance.get("confidence", 0.0),
            })

            # Extract words from utterance
            for word in utterance.get("words", []):
                words.append({
                    "word": word["text"],
                    "start": word["start"],
                    "end": word["end"],
                    "confidence": word.get("confidence", 0.0),
                })

        # Combine all text
        full_text = " ".join(u["text"] for u in result.get("utterances", []))

        # Calculate duration from last segment
        duration = segments[-1]["end"] if segments else 0

        return TranscriptionResult(
            text=full_text,
            segments=segments,
            words=words,
            language=result.get("language_code", "unknown"),
            duration_seconds=duration,
            processing_time_seconds=processing_time,
        )

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
