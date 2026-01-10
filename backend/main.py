"""TranscribeFlow Backend - Main Application Entry Point."""
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
