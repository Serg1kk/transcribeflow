# services/insight_service.py
"""AI Insights service for Level 2 post-processing."""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from config import get_settings
from models import Transcription, LLMOperation, LLMOperationStatus, LLMOperationType
from services.insight_template_service import InsightTemplateService, InsightTemplate
from services.llm_models_service import LLMModelsService
from services.llm_providers import GeminiClient, OpenRouterClient

logger = logging.getLogger(__name__)


@dataclass
class InsightResult:
    """Result of AI Insights extraction."""
    description: str
    sections: List[Dict[str, Any]]
    mindmap: Optional[Dict[str, str]]
    input_tokens: int
    output_tokens: int
    cost_usd: Optional[float]
    processing_time_seconds: float


def _format_timestamp(seconds: float) -> str:
    """Format timestamp as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class InsightService:
    """Service for extracting AI Insights from transcripts."""

    def __init__(self):
        self.settings = get_settings()
        self.template_service = InsightTemplateService()
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

    def _format_transcript(self, segments: list) -> str:
        """Format transcript segments for LLM input."""
        lines = []
        for seg in segments:
            timestamp = _format_timestamp(seg.get("start", 0))
            speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
            text = seg.get("text", "")
            lines.append(f"[{timestamp}] {speaker}: {text}")
        return "\n".join(lines)

    def _load_source_transcript(
        self,
        transcription: Transcription,
        source: str
    ) -> Dict[str, Any]:
        """Load the source transcript (original or cleaned)."""
        output_dir = Path(transcription.output_dir)

        if source == "cleaned":
            cleaned_path = output_dir / "transcript_cleaned.json"
            if cleaned_path.exists():
                with open(cleaned_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise FileNotFoundError("Cleaned transcript not found")

        # Default to original
        transcript_path = output_dir / "transcript.json"
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError("Original transcript not found")

    async def generate_insights(
        self,
        transcription: Transcription,
        template_id: str,
        source: str = "original",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> InsightResult:
        """Generate insights from a transcript.

        Args:
            transcription: The transcription to analyze
            template_id: ID of insight template to use
            source: "original" or "cleaned"
            provider: LLM provider (default from settings)
            model: LLM model (default from settings)
            db: Database session for logging operation

        Returns:
            InsightResult with extracted insights and usage stats
        """
        start_time = time.time()

        # Get template
        template = self.template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Insight template not found: {template_id}")

        # Use defaults from settings if not specified
        provider = provider or self.settings.insights_provider
        model = model or self.settings.insights_model

        # Load source transcript
        transcript_data = self._load_source_transcript(transcription, source)
        segments = transcript_data.get("segments", [])
        if not segments:
            raise ValueError("No segments in transcript")

        # Format transcript for LLM
        user_message = self._format_transcript(segments)

        # Call LLM
        client = self._get_client(provider)
        logger.info(f"Generating insights: provider={provider}, model={model}, template={template_id}")

        llm_response = await client.complete(
            system_prompt=template.system_prompt,
            user_message=user_message,
            model=model,
            temperature=template.temperature,
        )

        logger.info(f"LLM response: tokens_in={llm_response.input_tokens}, tokens_out={llm_response.output_tokens}")

        # Parse response
        parsed = self._parse_llm_response(llm_response.text, template)

        # Calculate cost
        model_info = self.models_service.get_model(provider, model)
        cost_usd = None
        if model_info:
            cost_usd = model_info.calculate_cost(
                llm_response.input_tokens,
                llm_response.output_tokens
            )

        processing_time = time.time() - start_time

        # Build result
        result = InsightResult(
            description=parsed.get("description", ""),
            sections=parsed.get("sections", []),
            mindmap=parsed.get("mindmap"),
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            cost_usd=cost_usd,
            processing_time_seconds=processing_time,
        )

        # Save insights to file
        self._save_insights(
            transcription=transcription,
            template=template,
            result=result,
            source=source,
            provider=provider,
            model=model,
        )

        # Log operation to database
        if db:
            operation = LLMOperation(
                transcription_id=transcription.id,
                operation_type=LLMOperationType.INSIGHTS,
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

        return result

    def _parse_llm_response(
        self,
        response_text: str,
        template: InsightTemplate
    ) -> Dict[str, Any]:
        """Parse LLM response into structured insights."""
        try:
            # Handle potential markdown code blocks
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            data = json.loads(text.strip())

            # Validate required fields
            result = {
                "description": data.get("description", ""),
                "sections": data.get("sections", []),
            }

            # Only include mindmap if template requires it
            if template.include_mindmap and data.get("mindmap"):
                result["mindmap"] = data["mindmap"]
            else:
                result["mindmap"] = None

            return result

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError(f"Failed to parse LLM response: {e}")

    def _save_insights(
        self,
        transcription: Transcription,
        template: InsightTemplate,
        result: InsightResult,
        source: str,
        provider: str,
        model: str,
    ):
        """Save insights to file."""
        output_dir = Path(transcription.output_dir)

        # Build insights JSON
        insights_data = {
            "metadata": {
                "id": transcription.id,
                "transcription_id": transcription.id,
                "template_id": template.id,
                "template_name": template.name,
                "source": source,
                "created_at": datetime.utcnow().isoformat(),
                "provider": provider,
                "model": model,
            },
            "description": result.description,
            "sections": result.sections,
            "mindmap": result.mindmap,
            "stats": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
                "processing_time_seconds": round(result.processing_time_seconds, 2),
            },
        }

        # Save insights_<template-id>.json
        insights_path = output_dir / f"insights_{template.id}.json"
        with open(insights_path, "w", encoding="utf-8") as f:
            json.dump(insights_data, f, ensure_ascii=False, indent=2)

        # Append to insights_log.json
        log_path = output_dir / "insights_log.json"
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
            "template_id": template.id,
            "source": source,
            "provider": provider,
            "model": model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": result.cost_usd,
            "processing_time_seconds": round(result.processing_time_seconds, 2),
            "status": "success",
        })

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    def get_insights(
        self,
        transcription: Transcription,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get saved insights for a transcription and template."""
        output_dir = Path(transcription.output_dir)
        insights_path = output_dir / f"insights_{template_id}.json"

        if insights_path.exists():
            with open(insights_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_insights(self, transcription: Transcription) -> List[Dict[str, Any]]:
        """List all generated insights for a transcription."""
        output_dir = Path(transcription.output_dir)
        insights = []

        for path in output_dir.glob("insights_*.json"):
            if path.name == "insights_log.json":
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    insights.append({
                        "template_id": data["metadata"]["template_id"],
                        "template_name": data["metadata"]["template_name"],
                        "created_at": data["metadata"]["created_at"],
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(insights, key=lambda x: x["created_at"], reverse=True)

    def check_source_available(
        self,
        transcription: Transcription
    ) -> Dict[str, bool]:
        """Check which sources are available for insights."""
        output_dir = Path(transcription.output_dir)
        return {
            "original": (output_dir / "transcript.json").exists(),
            "cleaned": (output_dir / "transcript_cleaned.json").exists(),
        }
