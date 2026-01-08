# engines/yandex.py
"""Yandex SpeechKit transcription engine."""
import asyncio
import base64
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from engines.base import TranscriptionEngine, TranscriptionResult


class YandexEngine(TranscriptionEngine):
    """Yandex SpeechKit cloud transcription engine."""

    BASE_URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "yandex"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def validate_api_key(self) -> Dict[str, Any]:
        """Validate API key by making a test request."""
        if not self.api_key:
            return {"valid": False, "error": "No API key provided"}

        # Yandex doesn't have a simple validation endpoint
        # We'll try to start a recognition and check for auth errors
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/longRunningRecognize",
                headers={"Authorization": f"Api-Key {self.api_key}"},
                json={"config": {}, "audio": {"content": ""}},
            )

            # 400 = bad request (but auth passed), 401/403 = auth failed
            if response.status_code in [200, 400]:
                return {"valid": True}
            else:
                return {"valid": False, "error": response.text}

    def transcribe(
        self,
        audio_path: Path,
        model: str = "general",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using Yandex SpeechKit API."""
        return asyncio.run(self._transcribe_async(audio_path, model, language))

    async def _transcribe_async(
        self,
        audio_path: Path,
        model: str = "general",
        language: Optional[str] = None,
        diarization: bool = True,
    ) -> TranscriptionResult:
        """Async transcription implementation."""
        if not self.is_available():
            raise RuntimeError("Yandex SpeechKit API key not configured")

        start_time = time.time()

        # Read and encode audio
        with open(audio_path, "rb") as f:
            audio_content = base64.b64encode(f.read()).decode("utf-8")

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build recognition config
        config = {
            "specification": {
                "languageCode": language or "auto",
                "model": model,
                "audioEncoding": self._get_audio_encoding(audio_path),
                "sampleRateHertz": 48000,
                "audioChannelCount": 1,
                "rawResults": True,
            },
        }

        if diarization:
            config["specification"]["enableSpeakerLabeling"] = True

        request_body = {
            "config": config,
            "audio": {"content": audio_content},
        }

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Start long-running recognition
            response = await client.post(
                f"{self.BASE_URL}/longRunningRecognize",
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
            operation = response.json()
            operation_id = operation["id"]

            # Poll for completion
            while True:
                poll_response = await client.get(
                    f"https://operation.api.cloud.yandex.net/operations/{operation_id}",
                    headers=headers,
                )
                poll_response.raise_for_status()
                result = poll_response.json()

                if result.get("done"):
                    break

                await asyncio.sleep(3)

        processing_time = time.time() - start_time

        # Parse response
        response_data = result.get("response", {})
        chunks = response_data.get("chunks", [])

        segments = []
        words = []
        full_text_parts = []

        for chunk in chunks:
            alternatives = chunk.get("alternatives", [])
            if not alternatives:
                continue

            best_alt = alternatives[0]
            text = best_alt.get("text", "")
            full_text_parts.append(text)

            # Extract timing if available
            start_ms = chunk.get("channelTag", "0")

            speaker_id = "SPEAKER_00"
            if diarization and "speakerTag" in chunk:
                speaker_id = f"SPEAKER_{chunk['speakerTag']:02d}"

            segments.append({
                "start": float(start_ms) / 1000 if start_ms else 0,
                "end": 0,  # Yandex doesn't always provide end times
                "text": text,
                "speaker": speaker_id,
                "confidence": best_alt.get("confidence", 0.0),
            })

            # Extract words
            for word_info in best_alt.get("words", []):
                words.append({
                    "word": word_info.get("word", ""),
                    "start": float(word_info.get("startTime", "0s").rstrip("s")),
                    "end": float(word_info.get("endTime", "0s").rstrip("s")),
                    "confidence": word_info.get("confidence", 0.0),
                })

        # Calculate duration from last word
        duration = words[-1]["end"] if words else 0

        return TranscriptionResult(
            text=" ".join(full_text_parts),
            segments=segments,
            words=words,
            language=language or "auto",
            duration_seconds=duration,
            processing_time_seconds=processing_time,
            raw_response=result,  # Original Yandex response
        )

    def _get_audio_encoding(self, audio_path: Path) -> str:
        """Get Yandex audio encoding based on file extension."""
        ext = audio_path.suffix.lower()
        encodings = {
            ".mp3": "MP3",
            ".wav": "LINEAR16_PCM",
            ".ogg": "OGG_OPUS",
            ".flac": "FLAC",
        }
        return encodings.get(ext, "MP3")
