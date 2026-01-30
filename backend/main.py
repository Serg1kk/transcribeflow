"""TranscribeFlow Backend - Main Application Entry Point."""

# IMPORTANT: Fix for PyTorch 2.6 weights_only=True default change
# This breaks loading of pyannote/speechbrain models
# We need to add safe globals AND patch torch.load
try:
    import torch
    import torch.serialization
    
    # Add commonly needed globals for pyannote/speechbrain
    try:
        torch.serialization.add_safe_globals([torch.torch_version.TorchVersion])
    except Exception:
        pass
    
    # Also patch torch.load as backup
    _original_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load
except ImportError:
    pass

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.transcribe import router as transcribe_router
from api.settings import router as settings_router
from api.engines import router as engines_router
from api.postprocess import router as postprocess_router
from api.insights import router as insights_router
from models import init_db
from workers.queue_processor import queue_processor

# Optional: System monitoring (local-only feature)
try:
    from api.system import router as system_router
    HAS_SYSTEM_MONITOR = True
except ImportError:
    HAS_SYSTEM_MONITOR = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
# Set DEBUG for postprocessing to see LLM responses
logging.getLogger("services.postprocessing_service").setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    
    # Reset any stuck "processing" tasks from previous crash/restart
    from models import SessionLocal, Transcription, TranscriptionStatus
    db = SessionLocal()
    try:
        stuck = db.query(Transcription).filter(
            Transcription.status == TranscriptionStatus.PROCESSING
        ).all()
        if stuck:
            logging.info(f"Resetting {len(stuck)} stuck PROCESSING tasks to QUEUED")
            for t in stuck:
                t.status = TranscriptionStatus.QUEUED
                t.progress = 0
            db.commit()
    except Exception as e:
        logging.error(f"Error resetting stuck tasks: {e}")
    finally:
        db.close()
    
    await queue_processor.start()

    yield

    # Shutdown
    await queue_processor.stop()


app = FastAPI(
    title="TranscribeFlow API",
    description="Local meeting transcription with speaker diarization",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_origin_regex=r"http://192\.168\.\d+\.\d+:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


app.include_router(transcribe_router)
app.include_router(settings_router)
app.include_router(engines_router)
app.include_router(postprocess_router)
app.include_router(insights_router)

# Include system monitoring if available (local-only feature)
if HAS_SYSTEM_MONITOR:
    app.include_router(system_router)
