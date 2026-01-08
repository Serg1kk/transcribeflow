"""TranscribeFlow Backend - Main Application Entry Point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.transcribe import router as transcribe_router
from models import init_db

app = FastAPI(
    title="TranscribeFlow API",
    description="Local meeting transcription with speaker diarization",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


app.include_router(transcribe_router)
