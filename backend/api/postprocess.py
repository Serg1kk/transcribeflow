# api/postprocess.py
"""Post-processing API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_settings
from models import get_db, Transcription, TranscriptionStatus, LLMOperation, LLMOperationStatus
from services.template_service import TemplateService
from services.llm_models_service import LLMModelsService
from services.postprocessing_service import PostProcessingService

router = APIRouter(prefix="/api/postprocess", tags=["post-processing"])


# Response models
class TemplateResponse(BaseModel):
    """Template response model."""
    id: str
    name: str
    description: str
    temperature: float


class TemplateDetailResponse(TemplateResponse):
    """Template detail response with system prompt."""
    system_prompt: str


class LLMModelResponse(BaseModel):
    """LLM model response."""
    id: str
    name: str
    input_price_per_1m: Optional[float]
    output_price_per_1m: Optional[float]


class LLMModelsResponse(BaseModel):
    """LLM models list response."""
    models: List[LLMModelResponse]


class PostProcessRequest(BaseModel):
    """Request to start post-processing."""
    template_id: str
    provider: Optional[str] = None
    model: Optional[str] = None


class PostProcessStatusResponse(BaseModel):
    """Post-processing status response."""
    status: str  # "processing" | "completed" | "failed"
    progress: int  # 0-100
    error_message: Optional[str] = None


class CleanedTranscriptResponse(BaseModel):
    """Cleaned transcript response."""
    metadata: dict
    speakers: dict
    segments: list
    stats: dict


class OperationHistoryResponse(BaseModel):
    """LLM operation history response."""
    id: str
    transcription_id: str
    created_at: str
    provider: str
    model: str
    template_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: Optional[float]
    processing_time_seconds: float
    status: str
    error_message: Optional[str] = None


class SpeakerSuggestionResponse(BaseModel):
    """Speaker suggestion response."""
    speaker_id: str
    display_name: str
    name: Optional[str]
    name_confidence: float
    name_reason: Optional[str]
    role: Optional[str]
    role_confidence: float
    role_reason: Optional[str]
    applied: bool


class SpeakerSuggestionsResponse(BaseModel):
    """Speaker suggestions list response."""
    created_at: str
    template: str
    model: str
    suggestions: List[SpeakerSuggestionResponse]


# Template endpoints
@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates():
    """List all available post-processing templates."""
    service = TemplateService()
    templates = service.list_templates()
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            temperature=t.temperature,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str):
    """Get a specific template by ID."""
    service = TemplateService()
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        temperature=template.temperature,
        system_prompt=template.system_prompt,
    )


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""
    id: str
    name: str
    description: str
    system_prompt: str
    temperature: float = 0.2


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(request: CreateTemplateRequest):
    """Create a new custom template."""
    from services.template_service import Template

    service = TemplateService()

    # Check if template already exists
    if service.get_template(request.id):
        raise HTTPException(status_code=400, detail="Template ID already exists")

    template = Template(
        id=request.id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
    )
    service.create_template(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        temperature=template.temperature,
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, request: CreateTemplateRequest):
    """Update an existing template."""
    from services.template_service import Template

    service = TemplateService()

    existing = service.get_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    template = Template(
        id=template_id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
    )
    service.update_template(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        temperature=template.temperature,
    )


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a custom template."""
    service = TemplateService()

    if not service.delete_template(template_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: template not found or is a default template"
        )

    return {"status": "deleted"}


# LLM Models endpoints
@router.get("/models")
async def list_llm_models():
    """List available LLM models by provider."""
    service = LLMModelsService()
    config = service.get_all_config()

    result = {}
    for provider, data in config.items():
        result[provider] = {
            "models": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "input_price_per_1m": m.get("input_price_per_1m"),
                    "output_price_per_1m": m.get("output_price_per_1m"),
                }
                for m in data.get("models", [])
            ]
        }

    return result


@router.put("/models")
async def update_llm_models(config: dict):
    """Update LLM models configuration."""
    service = LLMModelsService()
    service.update_config(config)
    return service.get_all_config()


# Post-processing endpoints
@router.post("/transcriptions/{transcription_id}")
async def start_postprocessing(
    transcription_id: str,
    request: PostProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start post-processing for a transcription."""
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
    template_service = TemplateService()
    if not template_service.get_template(request.template_id):
        raise HTTPException(status_code=400, detail="Template not found")

    # Get settings for defaults
    settings = get_settings()
    provider = request.provider or settings.postprocessing_provider
    model = request.model or settings.postprocessing_model

    # Extract data needed for background task (session will be closed after request)
    output_dir = transcription.output_dir
    filename = transcription.filename

    # Start processing in background
    async def run_postprocessing():
        import logging
        import time
        logger = logging.getLogger(__name__)
        logger.info(f"Background task started for transcription {transcription_id}")

        from models import SessionLocal
        # Create a new session for background task (request session is closed)
        bg_db = SessionLocal()
        operation = None
        start_time = time.time()
        
        try:
            # Create operation record with PROCESSING status at start
            operation = LLMOperation(
                transcription_id=transcription_id,
                provider=provider,
                model=model,
                template_id=request.template_id,
                temperature=0.2,
                input_tokens=0,
                output_tokens=0,
                cost_usd=None,
                processing_time_seconds=0,
                status=LLMOperationStatus.PROCESSING,
                error_message=None,
            )
            bg_db.add(operation)
            bg_db.commit()
            bg_db.refresh(operation)
            logger.info(f"Created operation {operation.id} with status PROCESSING")
            
            # Re-fetch transcription in new session
            bg_transcription = bg_db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if not bg_transcription:
                raise ValueError(f"Transcription {transcription_id} not found")

            service = PostProcessingService()
            result = await service.process_transcript(
                transcription=bg_transcription,
                template_id=request.template_id,
                provider=request.provider,
                model=request.model,
                db=bg_db,
                existing_operation=operation,  # Pass operation to update instead of create new
            )
            
            # Update operation to SUCCESS (service already updated tokens/cost)
            operation.status = LLMOperationStatus.SUCCESS
            operation.processing_time_seconds = time.time() - start_time
            bg_db.commit()
            logger.info(f"Operation {operation.id} completed successfully")
            
        except Exception as e:
            import traceback
            # Get full error details
            error_msg = str(e) or repr(e) or type(e).__name__
            full_traceback = traceback.format_exc()
            logger.error(f"Post-processing failed: {error_msg}")
            logger.error(f"Full traceback:\n{full_traceback}")
            
            # Update existing operation to FAILED or create new if none exists
            if operation:
                operation.status = LLMOperationStatus.FAILED
                operation.error_message = error_msg if error_msg else f"Exception: {type(e).__name__}"
                operation.processing_time_seconds = time.time() - start_time
            else:
                operation = LLMOperation(
                    transcription_id=transcription_id,
                    provider=provider,
                    model=model,
                    template_id=request.template_id,
                    temperature=0.2,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=None,
                    processing_time_seconds=time.time() - start_time,
                    status=LLMOperationStatus.FAILED,
                    error_message=error_msg if error_msg else f"Exception: {type(e).__name__}",
                )
                bg_db.add(operation)
            bg_db.commit()
        finally:
            bg_db.close()

    background_tasks.add_task(run_postprocessing)

    return {"status": "processing", "transcription_id": transcription_id}


@router.get("/transcriptions/{transcription_id}/cleaned")
async def get_cleaned_transcript(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Get the cleaned transcript for a transcription."""
    import json
    from pathlib import Path

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Transcript not ready")

    cleaned_path = Path(transcription.output_dir) / "transcript_cleaned.json"
    if not cleaned_path.exists():
        raise HTTPException(status_code=404, detail="Cleaned transcript not found")

    with open(cleaned_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Operation history endpoints
@router.get("/operations", response_model=List[OperationHistoryResponse])
async def list_operations(
    transcription_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List LLM operation history."""
    query = db.query(LLMOperation).order_by(LLMOperation.created_at.desc())

    if transcription_id:
        query = query.filter(LLMOperation.transcription_id == transcription_id)

    operations = query.limit(limit).all()

    return [
        OperationHistoryResponse(
            id=op.id,
            transcription_id=op.transcription_id,
            created_at=op.created_at.isoformat(),
            provider=op.provider,
            model=op.model,
            template_id=op.template_id,
            input_tokens=op.input_tokens,
            output_tokens=op.output_tokens,
            cost_usd=op.cost_usd,
            processing_time_seconds=op.processing_time_seconds,
            status=op.status.value,
            error_message=op.error_message,
        )
        for op in operations
    ]


# Speaker suggestions endpoints
@router.get("/transcriptions/{transcription_id}/suggestions")
async def get_speaker_suggestions(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Get speaker name suggestions for a transcription."""
    import json
    from pathlib import Path

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Transcript not ready")

    suggestions_path = Path(transcription.output_dir) / "speaker_suggestions.json"
    if not suggestions_path.exists():
        raise HTTPException(status_code=404, detail="No speaker suggestions available")

    with open(suggestions_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/transcriptions/{transcription_id}/suggestions/{speaker_id}/apply")
async def apply_speaker_suggestion(
    transcription_id: str,
    speaker_id: str,
    db: Session = Depends(get_db),
):
    """Apply a speaker name suggestion."""
    import json
    from pathlib import Path

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Transcript not ready")

    output_dir = Path(transcription.output_dir)
    suggestions_path = output_dir / "speaker_suggestions.json"

    if not suggestions_path.exists():
        raise HTTPException(status_code=404, detail="No speaker suggestions available")

    # Load suggestions
    with open(suggestions_path, "r", encoding="utf-8") as f:
        suggestions_data = json.load(f)

    # Find the suggestion
    suggestion = None
    for sug in suggestions_data["suggestions"]:
        if sug["speaker_id"] == speaker_id:
            suggestion = sug
            break

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found for this speaker")

    if suggestion["applied"]:
        raise HTTPException(status_code=400, detail="Suggestion already applied")

    # Apply the name to both transcript files
    display_name = suggestion["display_name"]
    transcript_data = None

    # Update transcript.json
    transcript_path = output_dir / "transcript.json"
    if transcript_path.exists():
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        if speaker_id in transcript_data.get("speakers", {}):
            transcript_data["speakers"][speaker_id]["name"] = display_name
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    # Update transcript_cleaned.json
    cleaned_path = output_dir / "transcript_cleaned.json"
    cleaned_data = None
    if cleaned_path.exists():
        with open(cleaned_path, "r", encoding="utf-8") as f:
            cleaned_data = json.load(f)
        if speaker_id in cleaned_data.get("speakers", {}):
            cleaned_data["speakers"][speaker_id]["name"] = display_name
            with open(cleaned_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    # Regenerate TXT files
    from api.transcribe import _regenerate_txt_files
    _regenerate_txt_files(output_dir, transcript_data, cleaned_data)

    # Mark suggestion as applied
    suggestion["applied"] = True
    with open(suggestions_path, "w", encoding="utf-8") as f:
        json.dump(suggestions_data, f, ensure_ascii=False, indent=2)

    # Update database
    if transcription.speaker_names is None:
        transcription.speaker_names = {}
    transcription.speaker_names[speaker_id] = display_name
    db.commit()

    return {"status": "applied", "speaker_id": speaker_id, "name": display_name}


@router.post("/transcriptions/{transcription_id}/suggestions/apply-all")
async def apply_all_speaker_suggestions(
    transcription_id: str,
    db: Session = Depends(get_db),
):
    """Apply all non-applied speaker name suggestions."""
    import json
    from pathlib import Path

    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.output_dir:
        raise HTTPException(status_code=404, detail="Transcript not ready")

    output_dir = Path(transcription.output_dir)
    suggestions_path = output_dir / "speaker_suggestions.json"

    if not suggestions_path.exists():
        raise HTTPException(status_code=404, detail="No speaker suggestions available")

    # Load suggestions
    with open(suggestions_path, "r", encoding="utf-8") as f:
        suggestions_data = json.load(f)

    # Load transcript files
    transcript_path = output_dir / "transcript.json"
    cleaned_path = output_dir / "transcript_cleaned.json"

    transcript_data = None
    cleaned_data = None

    if transcript_path.exists():
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)

    if cleaned_path.exists():
        with open(cleaned_path, "r", encoding="utf-8") as f:
            cleaned_data = json.load(f)

    # Apply all non-applied suggestions
    applied_count = 0
    speaker_names = transcription.speaker_names or {}

    for sug in suggestions_data["suggestions"]:
        if sug["applied"] or not sug["display_name"]:
            continue

        speaker_id = sug["speaker_id"]
        display_name = sug["display_name"]

        # Update transcript.json
        if transcript_data and speaker_id in transcript_data.get("speakers", {}):
            transcript_data["speakers"][speaker_id]["name"] = display_name

        # Update transcript_cleaned.json
        if cleaned_data and speaker_id in cleaned_data.get("speakers", {}):
            cleaned_data["speakers"][speaker_id]["name"] = display_name

        # Mark as applied
        sug["applied"] = True
        speaker_names[speaker_id] = display_name
        applied_count += 1

    # Save all files
    if transcript_data:
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    if cleaned_data:
        with open(cleaned_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    with open(suggestions_path, "w", encoding="utf-8") as f:
        json.dump(suggestions_data, f, ensure_ascii=False, indent=2)

    # Regenerate TXT files
    from api.transcribe import _regenerate_txt_files
    _regenerate_txt_files(output_dir, transcript_data, cleaned_data)

    # Update database
    transcription.speaker_names = speaker_names
    db.commit()

    return {"status": "applied", "applied": applied_count}
