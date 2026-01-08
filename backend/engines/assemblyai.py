# engines/assemblyai.py
"""AssemblyAI transcription engine."""
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from engines.base import TranscriptionEngine, TranscriptionResult


class AssemblyAIEngine(TranscriptionEngine):
    """AssemblyAI cloud transcription engine."""

    BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "assemblyai"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def validate_api_key(self) -> Dict[str, Any]:
        """Validate API key by making a test request."""
        if not self.api_key:
            return {"valid": False, "error": "No API key provided"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/transcript",
                headers={"authorization": self.api_key},
                params={"limit": 1},
            )

            if response.status_code == 200:
                return {"valid": True}
            else:
                return {"valid": False, "error": response.text}

    def transcribe(
        self,
        audio_path: Path,
        model: str = "best",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using AssemblyAI API.

        This is a synchronous wrapper around the async implementation.
        """
        return asyncio.run(self._transcribe_async(audio_path, model, language))

    async def _transcribe_async(
        self,
        audio_path: Path,
        model: str = "best",
        language: Optional[str] = None,
        diarization: bool = True,
    ) -> TranscriptionResult:
        """Async transcription implementation."""
        if not self.is_available():
            raise RuntimeError("AssemblyAI API key not configured")

        start_time = time.time()
        headers = {"authorization": self.api_key}

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Step 1: Upload audio file
            with open(audio_path, "rb") as f:
                upload_response = await client.post(
                    f"{self.BASE_URL}/upload",
                    headers=headers,
                    content=f.read(),
                )
            upload_response.raise_for_status()
            audio_url = upload_response.json()["upload_url"]

            # Step 2: Create transcription request
            transcript_request = {
                "audio_url": audio_url,
                "speech_model": model,  # "best" or "nano"
                "speaker_labels": diarization,
            }

            create_response = await client.post(
                f"{self.BASE_URL}/transcript",
                headers=headers,
                json=transcript_request,
            )
            create_response.raise_for_status()
            transcript_id = create_response.json()["id"]

            # Step 3: Poll for completion
            while True:
                poll_response = await client.get(
                    f"{self.BASE_URL}/transcript/{transcript_id}",
                    headers=headers,
                )
                poll_response.raise_for_status()
                result = poll_response.json()

                if result["status"] == "completed":
                    break
                elif result["status"] == "error":
                    raise RuntimeError(f"AssemblyAI error: {result.get('error', 'Unknown error')}")

                await asyncio.sleep(3)

        processing_time = time.time() - start_time

        # Convert response to unified format
        segments = []
        words = []

        # Process utterances (speaker-labeled segments)
        if result.get("utterances"):
            for utterance in result["utterances"]:
                segments.append({
                    "start": utterance["start"] / 1000,  # ms to seconds
                    "end": utterance["end"] / 1000,
                    "text": utterance["text"],
                    "speaker": f"SPEAKER_{utterance['speaker']}",
                    "confidence": utterance.get("confidence", 0.0),
                })
        else:
            # Fallback to single segment if no utterances
            if result.get("text"):
                segments.append({
                    "start": 0.0,
                    "end": result.get("audio_duration", 0),
                    "text": result["text"],
                    "speaker": "SPEAKER_00",
                })

        # Extract words
        for word in result.get("words", []):
            words.append({
                "word": word["text"],
                "start": word["start"] / 1000,
                "end": word["end"] / 1000,
                "confidence": word.get("confidence", 0.0),
            })

        return TranscriptionResult(
            text=result.get("text", ""),
            segments=segments,
            words=words,
            language=result.get("language_code", "unknown"),
            duration_seconds=result.get("audio_duration", 0),
            processing_time_seconds=processing_time,
            raw_response=result,  # Original AssemblyAI response
        )
