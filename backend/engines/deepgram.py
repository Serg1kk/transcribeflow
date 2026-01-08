# engines/deepgram.py
"""Deepgram transcription engine."""
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from engines.base import TranscriptionEngine, TranscriptionResult


class DeepgramEngine(TranscriptionEngine):
    """Deepgram cloud transcription engine."""

    BASE_URL = "https://api.deepgram.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "deepgram"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def validate_api_key(self) -> Dict[str, Any]:
        """Validate API key by making a test request."""
        if not self.api_key:
            return {"valid": False, "error": "No API key provided"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/projects",
                headers={"Authorization": f"Token {self.api_key}"},
            )

            if response.status_code == 200:
                return {"valid": True}
            else:
                return {"valid": False, "error": response.text}

    def transcribe(
        self,
        audio_path: Path,
        model: str = "nova-3",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using Deepgram API."""
        return asyncio.run(self._transcribe_async(audio_path, model, language))

    async def _transcribe_async(
        self,
        audio_path: Path,
        model: str = "nova-3",
        language: Optional[str] = None,
        diarization: bool = True,
    ) -> TranscriptionResult:
        """Async transcription implementation."""
        if not self.is_available():
            raise RuntimeError("Deepgram API key not configured")

        start_time = time.time()

        # Build query parameters
        params = {
            "model": model,
            "smart_format": "true",
            "punctuate": "true",
            "diarize": str(diarization).lower(),
            "utterances": "true",
        }

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": self._get_content_type(audio_path),
        }

        async with httpx.AsyncClient(timeout=600.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    f"{self.BASE_URL}/listen",
                    headers=headers,
                    params=params,
                    content=f.read(),
                )

            response.raise_for_status()
            result = response.json()

        processing_time = time.time() - start_time

        # Parse response
        channel = result.get("results", {}).get("channels", [{}])[0]
        alternative = channel.get("alternatives", [{}])[0]

        # Build segments from utterances
        segments = []
        utterances = result.get("results", {}).get("utterances", [])

        if utterances:
            for utterance in utterances:
                segments.append({
                    "start": utterance["start"],
                    "end": utterance["end"],
                    "text": utterance["transcript"],
                    "speaker": f"SPEAKER_{utterance.get('speaker', 0):02d}",
                    "confidence": utterance.get("confidence", 0.0),
                })
        else:
            # Fallback to paragraphs
            for paragraph in alternative.get("paragraphs", {}).get("paragraphs", []):
                segments.append({
                    "start": paragraph["start"],
                    "end": paragraph["end"],
                    "text": " ".join(s["text"] for s in paragraph.get("sentences", [])),
                    "speaker": f"SPEAKER_{paragraph.get('speaker', 0):02d}",
                })

        # Build words list
        words = []
        for word in alternative.get("words", []):
            words.append({
                "word": word["word"],
                "start": word["start"],
                "end": word["end"],
                "confidence": word.get("confidence", 0.0),
            })

        metadata = result.get("metadata", {})

        return TranscriptionResult(
            text=alternative.get("transcript", ""),
            segments=segments,
            words=words,
            language=metadata.get("detected_language", "unknown"),
            duration_seconds=metadata.get("duration", 0),
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
