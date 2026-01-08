"""TranscribeFlow Backend - Main Application Entry Point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.transcribe import router as transcribe_router
from models import init_db
from workers.queue_processor import queue_processor


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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


app.include_router(transcribe_router)
