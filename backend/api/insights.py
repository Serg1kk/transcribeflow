# api/insights.py
"""AI Insights API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_settings
from models import get_db, Transcription, TranscriptionStatus, LLMOperation, LLMOperationStatus, LLMOperationType
from services.insight_template_service import InsightTemplateService
from services.insight_service import InsightService

router = APIRouter(prefix="/api/insights", tags=["ai-insights"])


# Response models
class InsightSectionResponse(BaseModel):
    """Insight section response."""
    id: str
    title: str
    description: str


class InsightTemplateResponse(BaseModel):
    """Insight template response model."""
    id: str
    name: str
    description: str
    include_mindmap: bool
    sections: List[InsightSectionResponse]
    temperature: float


class InsightTemplateDetailResponse(InsightTemplateResponse):
    """Insight template detail with system prompt."""
    system_prompt: str


class GenerateInsightsRequest(BaseModel):
    """Request to generate insights."""
    template_id: str
    source: str = "original"  # "original" | "cleaned"
    provider: Optional[str] = None
    model: Optional[str] = None


class InsightsMetadataResponse(BaseModel):
    """Insights metadata response."""
    template_id: str
    template_name: str
    created_at: str


class SourceAvailabilityResponse(BaseModel):
    """Source availability response."""
    original: bool
    cleaned: bool


# Template endpoints
@router.get("/templates", response_model=List[InsightTemplateResponse])
async def list_insight_templates():
    """List all available insight templates."""
    service = InsightTemplateService()
    templates = service.list_templates()
    return [
        InsightTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            include_mindmap=t.include_mindmap,
            sections=[
                InsightSectionResponse(
                    id=s["id"],
                    title=s["title"],
                    description=s["description"]
                )
                for s in t.sections
            ],
            temperature=t.temperature,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=InsightTemplateDetailResponse)
async def get_insight_template(template_id: str):
    """Get a specific insight template by ID."""
    service = InsightTemplateService()
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Insight template not found")
    return InsightTemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        include_mindmap=template.include_mindmap,
        sections=[
            InsightSectionResponse(
                id=s["id"],
                title=s["title"],
                description=s["description"]
            )
            for s in template.sections
        ],
        temperature=template.temperature,
        system_prompt=template.system_prompt,
    )


# Insights generation endpoints
@router.post("/transcriptions/{transcription_id}")
async def generate_insights(
    transcription_id: str,
    request: GenerateInsightsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate AI Insights for a transcription."""
    # Verify transcription exists and is completed
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Transcription must be completed. Current status: {transcription.status.value}"
        )

    # Verify template exists
    template_service = InsightTemplateService()
    template = template_service.get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=400, detail="Insight template not found")

    # Check source availability
    insight_service = InsightService()
    sources = insight_service.check_source_available(transcription)

    if request.source == "cleaned" and not sources["cleaned"]:
        raise HTTPException(
            status_code=400,
            detail="Cleaned transcript not available. Use 'original' or run post-processing first."
        )
    if request.source == "original" and not sources["original"]:
        raise HTTPException(status_code=400, detail="Original transcript not found")

    # Get settings for defaults
    settings = get_settings()
    provider = request.provider or settings.insights_provider
    model = request.model or settings.insights_model

    # Start processing in background
    async def run_insights():
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.info(f"Background insights task started for transcription {transcription_id}")

        from models import SessionLocal
        # Create a new session for background task (request session is closed)
        bg_db = SessionLocal()
        try:
            # Re-fetch transcription in new session
            bg_transcription = bg_db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if not bg_transcription:
                raise ValueError(f"Transcription {transcription_id} not found")

            service = InsightService()
            await service.generate_insights(
                transcription=bg_transcription,
                template_id=request.template_id,
                source=request.source,
                provider=request.provider,
                model=request.model,
                db=bg_db,
            )
        except Exception as e:
            # Get full error details
            error_msg = str(e) or repr(e) or type(e).__name__
            full_traceback = traceback.format_exc()
            logger.error(f"Insights generation failed: {error_msg}")
            logger.error(f"Full traceback:\n{full_traceback}")
            # Log failed operation
            operation = LLMOperation(
                transcription_id=transcription_id,
                operation_type=LLMOperationType.INSIGHTS,
                provider=provider,
                model=model,
                template_id=request.template_id,
                temperature=template.temperature,
                input_tokens=0,
                output_tokens=0,
                cost_usd=None,
                processing_time_seconds=0,
                status=LLMOperationStatus.FAILED,
                error_message=error_msg if error_msg else f"Exception: {type(e).__name__}",
            )
            bg_db.add(operation)
            bg_db.commit()
        finally:
            bg_db.close()

    background_tasks.add_task(run_insights)

    return {"status": "processing", "transcription_id": transcription_id}


@router.get("/transcriptions/{transcription_id}/sources")
async def check_sources(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Check which transcript sources are available for insights."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    service = InsightService()
    return service.check_source_available(transcription)


@router.get("/transcriptions/{transcription_id}")
async def list_transcription_insights(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """List all generated insights for a transcription."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        return []

    service = InsightService()
    return service.list_insights(transcription)


@router.get("/transcriptions/{transcription_id}/{template_id}")
async def get_insights(
    transcription_id: str,
    template_id: str,
    db: Session = Depends(get_db),
):
    """Get generated insights for a specific template."""
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Insights not found")

    service = InsightService()
    insights = service.get_insights(transcription, template_id)

    if not insights:
        raise HTTPException(status_code=404, detail="Insights not found for this template")

    return insights
