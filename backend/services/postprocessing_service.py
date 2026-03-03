# services/postprocessing_service.py
"""Post-processing service for LLM-based transcript cleanup."""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from config import get_settings
from models import Transcription, LLMOperation, LLMOperationStatus
from services.template_service import TemplateService, Template
from services.llm_models_service import LLMModelsService
from services.llm_providers import GeminiClient, OpenRouterClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class CleanedSegment:
    """A cleaned transcript segment."""
    start: float
    speaker: str
    text: str


@dataclass
class SpeakerSuggestion:
    """A speaker name/role suggestion from LLM."""
    speaker_id: str
    display_name: str
    name: Optional[str]
    name_confidence: float
    name_reason: Optional[str]
    role: Optional[str]
    role_confidence: float
    role_reason: Optional[str]
    applied: bool = False


@dataclass
class PostProcessingResult:
    """Result of post-processing operation."""
    segments: List[CleanedSegment]
    speaker_suggestions: List[SpeakerSuggestion]
    input_tokens: int
    output_tokens: int
    cost_usd: Optional[float]
    processing_time_seconds: float


def format_transcript_for_llm(segments: list) -> str:
    """Format transcript segments for LLM input."""
    lines = []
    for seg in segments:
        timestamp = format_timestamp(seg["start"])
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        text = seg.get("text", "")
        lines.append(f"[{timestamp}] {speaker}: {text}")
    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
    """Format timestamp as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


IDENTIFY_SPEAKERS_PROMPT = """You are an expert at analyzing meeting transcripts and identifying speakers.

## TASK
Analyze the transcript below and identify who each speaker is based on conversational context.

## WHAT TO LOOK FOR
- Direct addressing: "Привет, Андрей", "Лена, покажи...", "Thanks, Mike"
- Self-introduction: "Меня зовут...", "Это Сергей", "I'm John"
- Role indicators: discusses code → developer, discusses design → designer, asks about deadlines → manager
- Topic expertise: who knows what, who asks vs who answers
- Social dynamics: who leads the meeting, who reports

## USER CONTEXT
{context}

## OUTPUT FORMAT (STRICT JSON)

Return ONLY a JSON object:

```json
{{
  "speaker_suggestions": [
    {{
      "speaker_id": "SPEAKER_00",
      "name": "Лена",
      "name_confidence": 0.9,
      "name_reason": "SPEAKER_01 said 'Лена, покажи макеты'",
      "role": "designer",
      "role_confidence": 0.85,
      "role_reason": "Discusses UI, mockups, visual design"
    }}
  ]
}}
```

## RULES
- Include ALL speakers from input, even if name/role unknown
- If name unknown: "name": null, "name_confidence": 0, "name_reason": null
- If role unknown: "role": null, "role_confidence": 0, "role_reason": null
- confidence is 0.0 to 1.0
- reason should quote or describe the evidence from the transcript
- PRESERVE original language in names and reasons (if Russian transcript, use Russian names)

Return ONLY the JSON object, no explanations."""


class PostProcessingService:
    """Service for LLM-based transcript post-processing."""

    def __init__(self):
        self.settings = get_settings()
        self.template_service = TemplateService()
        self.models_service = LLMModelsService()

    def _get_client(self, provider: str):
        """Get LLM client for provider."""
        if provider == "gemini":
            api_key = self.settings.gemini_api_key
            if not api_key:
                raise ValueError("Gemini API key not configured")
            return GeminiClient(api_key=api_key)
        elif provider == "openrouter":
            api_key = self.settings.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key not configured")
            return OpenRouterClient(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def process_transcript(
        self,
        transcription: Transcription,
        template_id: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        db: Optional[Session] = None,
        existing_operation: Optional[LLMOperation] = None,
    ) -> PostProcessingResult:
        """Process a transcript with LLM cleanup.

        Args:
            transcription: The transcription to process
            template_id: ID of template to use
            provider: LLM provider (default from settings)
            model: LLM model (default from settings)
            db: Database session for logging operation
            existing_operation: Optional existing operation to update (instead of creating new)

        Returns:
            PostProcessingResult with cleaned segments and usage stats
        """
        start_time = time.time()

        # Get template
        template = self.template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Use defaults from settings if not specified
        provider = provider or self.settings.postprocessing_provider
        model = model or self.settings.postprocessing_model

        # Load original transcript
        transcript_path = Path(transcription.output_dir) / "transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError("Original transcript not found")

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)

        segments = transcript_data.get("segments", [])
        if not segments:
            raise ValueError("No segments in transcript")

        # Format transcript for LLM
        user_message = format_transcript_for_llm(segments)

        # Add user context if provided (from initial_prompt field)
        if transcription.initial_prompt:
            user_message = f"""USER CONTEXT:
{transcription.initial_prompt}

TRANSCRIPT:
{user_message}"""

        # Call LLM
        client = self._get_client(provider)
        logger.info(f"Calling LLM: provider={provider}, model={model}, template={template_id}")
        llm_response = await client.complete(
            system_prompt=template.system_prompt,
            user_message=user_message,
            model=model,
            temperature=template.temperature,
        )
        logger.info(f"LLM response: tokens_in={llm_response.input_tokens}, tokens_out={llm_response.output_tokens}")
        logger.debug(f"LLM raw response:\n{llm_response.text[:2000]}")

        # Parse response
        cleaned_segments, speaker_suggestions = self._parse_llm_response(llm_response.text)
        logger.info(f"Parsed: segments={len(cleaned_segments)}, suggestions={len(speaker_suggestions)}")

        # Calculate cost
        model_info = self.models_service.get_model(provider, model)
        cost_usd = None
        if model_info:
            cost_usd = model_info.calculate_cost(
                llm_response.input_tokens,
                llm_response.output_tokens
            )

        processing_time = time.time() - start_time

        # Save cleaned transcript
        self._save_cleaned_transcript(
            transcription=transcription,
            segments=cleaned_segments,
            speaker_suggestions=speaker_suggestions,
            original_data=transcript_data,
            template=template,
            provider=provider,
            model=model,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            cost_usd=cost_usd,
            processing_time=processing_time,
        )

        # Log operation to database (update existing or create new)
        if db:
            if existing_operation:
                # Update existing operation with results
                existing_operation.input_tokens = llm_response.input_tokens
                existing_operation.output_tokens = llm_response.output_tokens
                existing_operation.cost_usd = cost_usd
                existing_operation.temperature = template.temperature
                # Note: status and processing_time will be set by caller
                db.commit()
            else:
                # Create new operation (legacy path)
                operation = LLMOperation(
                    transcription_id=transcription.id,
                    provider=provider,
                    model=model,
                    template_id=template_id,
                    temperature=template.temperature,
                    input_tokens=llm_response.input_tokens,
                    output_tokens=llm_response.output_tokens,
                    cost_usd=cost_usd,
                    processing_time_seconds=processing_time,
                    status=LLMOperationStatus.SUCCESS,
                )
                db.add(operation)
                db.commit()

        return PostProcessingResult(
            segments=cleaned_segments,
            speaker_suggestions=speaker_suggestions,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            cost_usd=cost_usd,
            processing_time_seconds=processing_time,
        )

    async def identify_speakers(
        self,
        transcription: Transcription,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        db: Optional[Session] = None,
        existing_operation: Optional[LLMOperation] = None,
    ) -> List[SpeakerSuggestion]:
        """Identify speakers from transcript context without cleaning.

        Used for cloud-engine transcriptions where text quality is already good
        but speakers are labeled as Speaker 1, Speaker 2, etc.

        Args:
            transcription: The transcription to analyze
            provider: LLM provider (default from settings)
            model: LLM model (default from settings)
            db: Database session for logging operation
            existing_operation: Optional existing operation to update

        Returns:
            List of SpeakerSuggestion
        """
        start_time = time.time()

        provider = provider or self.settings.postprocessing_provider
        model = model or self.settings.postprocessing_model

        # Load transcript (prefer cleaned if exists, otherwise original)
        output_dir = Path(transcription.output_dir)
        cleaned_path = output_dir / "transcript_cleaned.json"
        transcript_path = output_dir / "transcript.json"

        if cleaned_path.exists():
            with open(cleaned_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
            segments = transcript_data.get("segments", [])
        elif transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
            segments = transcript_data.get("segments", [])
        else:
            raise FileNotFoundError("No transcript found")

        if not segments:
            raise ValueError("No segments in transcript")

        # Format transcript for LLM
        user_message = format_transcript_for_llm(segments)

        # Build context from initial_prompt
        context = transcription.initial_prompt or "No additional context provided."

        # Build system prompt
        system_prompt = IDENTIFY_SPEAKERS_PROMPT.format(context=context)

        # Call LLM
        client = self._get_client(provider)
        logger.info(f"Identify speakers: provider={provider}, model={model}")
        llm_response = await client.complete(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            temperature=0.2,
        )
        logger.info(f"LLM response: tokens_in={llm_response.input_tokens}, tokens_out={llm_response.output_tokens}")

        # Parse response — expect only speaker_suggestions
        suggestions = self._parse_speaker_suggestions(llm_response.text)
        logger.info(f"Identified {len(suggestions)} speaker suggestions")

        # Calculate cost
        model_info = self.models_service.get_model(provider, model)
        cost_usd = None
        if model_info:
            cost_usd = model_info.calculate_cost(
                llm_response.input_tokens,
                llm_response.output_tokens
            )

        processing_time = time.time() - start_time

        # Save speaker_suggestions.json
        if suggestions:
            suggestions_path = output_dir / "speaker_suggestions.json"
            suggestions_data = {
                "created_at": datetime.utcnow().isoformat(),
                "template": "identify-speakers",
                "model": model,
                "suggestions": [
                    {
                        "speaker_id": s.speaker_id,
                        "display_name": s.display_name,
                        "name": s.name,
                        "name_confidence": s.name_confidence,
                        "name_reason": s.name_reason,
                        "role": s.role,
                        "role_confidence": s.role_confidence,
                        "role_reason": s.role_reason,
                        "applied": s.applied,
                    }
                    for s in suggestions
                ]
            }
            with open(suggestions_path, "w", encoding="utf-8") as f:
                json.dump(suggestions_data, f, ensure_ascii=False, indent=2)

        # Log operation to database
        if db:
            if existing_operation:
                existing_operation.input_tokens = llm_response.input_tokens
                existing_operation.output_tokens = llm_response.output_tokens
                existing_operation.cost_usd = cost_usd
                existing_operation.temperature = 0.2
                db.commit()
            else:
                operation = LLMOperation(
                    transcription_id=transcription.id,
                    provider=provider,
                    model=model,
                    template_id="identify-speakers",
                    temperature=0.2,
                    input_tokens=llm_response.input_tokens,
                    output_tokens=llm_response.output_tokens,
                    cost_usd=cost_usd,
                    processing_time_seconds=processing_time,
                    status=LLMOperationStatus.SUCCESS,
                )
                db.add(operation)
                db.commit()

        return suggestions

    def _parse_speaker_suggestions(self, response_text: str) -> List[SpeakerSuggestion]:
        """Parse LLM response that contains only speaker suggestions."""
        try:
            data = json.loads(response_text)

            if isinstance(data, dict):
                suggestions_data = data.get("speaker_suggestions", [])
            else:
                suggestions_data = []

            suggestions = []
            for sug in suggestions_data:
                name = sug.get("name")
                role = sug.get("role")

                if name and role:
                    display_name = f"{name} ({role})"
                elif name:
                    display_name = name
                elif role:
                    display_name = role
                else:
                    display_name = ""

                if display_name:
                    suggestions.append(SpeakerSuggestion(
                        speaker_id=sug.get("speaker_id", ""),
                        display_name=display_name,
                        name=name,
                        name_confidence=float(sug.get("name_confidence", 0)),
                        name_reason=sug.get("name_reason"),
                        role=role,
                        role_confidence=float(sug.get("role_confidence", 0)),
                        role_reason=sug.get("role_reason"),
                        applied=False,
                    ))

            return suggestions
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Failed to parse speaker identification response: {e}")

    def _parse_llm_response(self, response_text: str) -> tuple[List[CleanedSegment], List[SpeakerSuggestion]]:
        """Parse LLM response into cleaned segments and speaker suggestions."""
        try:
            data = json.loads(response_text)

            # Backwards compatibility: if just array, treat as segments
            if isinstance(data, list):
                segments_data = data
                suggestions_data = []
            else:
                segments_data = data.get("segments", [])
                suggestions_data = data.get("speaker_suggestions", [])

            segments = []
            for seg in segments_data:
                segments.append(CleanedSegment(
                    start=float(seg.get("start", 0)),
                    speaker=seg.get("speaker", "SPEAKER_UNKNOWN"),
                    text=seg.get("text", ""),
                ))

            # Parse speaker suggestions
            suggestions = []
            for sug in suggestions_data:
                name = sug.get("name")
                role = sug.get("role")

                # Build display_name
                if name and role:
                    display_name = f"{name} ({role})"
                elif name:
                    display_name = name
                elif role:
                    display_name = role
                else:
                    display_name = ""

                if display_name:  # Only add if we have something to suggest
                    suggestions.append(SpeakerSuggestion(
                        speaker_id=sug.get("speaker_id", ""),
                        display_name=display_name,
                        name=name,
                        name_confidence=float(sug.get("name_confidence", 0)),
                        name_reason=sug.get("name_reason"),
                        role=role,
                        role_confidence=float(sug.get("role_confidence", 0)),
                        role_reason=sug.get("role_reason"),
                        applied=False,
                    ))

            return segments, suggestions
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}")

    def _save_cleaned_transcript(
        self,
        transcription: Transcription,
        segments: List[CleanedSegment],
        speaker_suggestions: List[SpeakerSuggestion],
        original_data: dict,
        template: Template,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float],
        processing_time: float,
    ):
        """Save cleaned transcript to files."""
        output_dir = Path(transcription.output_dir)

        # Build cleaned transcript JSON
        cleaned_data = {
            "metadata": {
                "id": transcription.id,
                "filename": transcription.filename,
                "cleaned_at": datetime.utcnow().isoformat(),
                "template": template.id,
                "provider": provider,
                "model": model,
            },
            "speakers": original_data.get("speakers", {}),
            "segments": [
                {
                    "start": seg.start,
                    "speaker": seg.speaker,
                    "text": seg.text,
                }
                for seg in segments
            ],
            "stats": {
                "original_segments": len(original_data.get("segments", [])),
                "cleaned_segments": len(segments),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "processing_time_seconds": round(processing_time, 2),
            },
        }

        # Save transcript_cleaned.json
        json_path = output_dir / "transcript_cleaned.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        # Save transcript_cleaned.txt
        txt_path = output_dir / "transcript_cleaned.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self._format_cleaned_txt(cleaned_data))

        # Save speaker_suggestions.json
        if speaker_suggestions:
            suggestions_path = output_dir / "speaker_suggestions.json"
            suggestions_data = {
                "created_at": datetime.utcnow().isoformat(),
                "template": template.id,
                "model": model,
                "suggestions": [
                    {
                        "speaker_id": s.speaker_id,
                        "display_name": s.display_name,
                        "name": s.name,
                        "name_confidence": s.name_confidence,
                        "name_reason": s.name_reason,
                        "role": s.role,
                        "role_confidence": s.role_confidence,
                        "role_reason": s.role_reason,
                        "applied": s.applied,
                    }
                    for s in speaker_suggestions
                ]
            }
            with open(suggestions_path, "w", encoding="utf-8") as f:
                json.dump(suggestions_data, f, ensure_ascii=False, indent=2)

        # Append to postprocessing_log.json
        log_path = output_dir / "postprocessing_log.json"
        log_data = {"operations": []}
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except json.JSONDecodeError:
                pass

        log_data["operations"].append({
            "id": str(len(log_data["operations"]) + 1),
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "model": model,
            "template": template.id,
            "temperature": template.temperature,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "processing_time_seconds": round(processing_time, 2),
            "status": "success",
        })

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    def _format_cleaned_txt(self, data: dict) -> str:
        """Format cleaned transcript as human-readable text."""
        meta = data["metadata"]
        speakers_dict = data["speakers"]

        lines = [
            f"Cleaned Transcript: {meta['filename']}",
            f"Cleaned: {meta['cleaned_at'][:10]}",
            f"Template: {meta['template']}",
            f"Model: {meta['model']}",
            "",
            "-" * 40,
            "",
        ]

        for seg in data["segments"]:
            timestamp = format_timestamp(seg["start"])
            speaker = speakers_dict.get(seg["speaker"], {}).get("name", seg["speaker"])
            lines.append(f"[{timestamp}] {speaker}: {seg['text']}")
            lines.append("")

        lines.append("-" * 40)
        return "\n".join(lines)
