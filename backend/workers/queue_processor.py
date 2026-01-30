# workers/queue_processor.py
"""Background queue processor for transcription tasks."""
import asyncio
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from models import Transcription, TranscriptionStatus, SessionLocal
from workers.transcription_worker import TranscriptionWorker

logger = logging.getLogger(__name__)

# Unload models after this many seconds of inactivity
MODEL_UNLOAD_TIMEOUT = 30


class QueueProcessor:
    """Processes transcription tasks from the queue in the background."""

    def __init__(self):
        self.worker = TranscriptionWorker()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_activity_time: float = 0
        self._models_loaded: bool = False

    def reset_workers(self):
        """Reset worker caches when settings change."""
        self.worker.reset_workers()
        self._models_loaded = False

    async def start(self):
        """Start the background queue processor."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Queue processor started")

    async def stop(self):
        """Stop the background queue processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Queue processor stopped")

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                processed = await self._process_next()
                
                # Check if we should unload models (no activity for MODEL_UNLOAD_TIMEOUT seconds)
                if not processed and self._models_loaded:
                    idle_time = time.time() - self._last_activity_time
                    if idle_time >= MODEL_UNLOAD_TIMEOUT:
                        logger.info(f"No activity for {idle_time:.0f}s, unloading models...")
                        self.worker.unload_models()
                        self._models_loaded = False
                        
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")

            # Wait before checking for next task
            await asyncio.sleep(2)

    async def _process_next(self) -> bool:
        """Process the next queued task. Returns True if a task was processed."""
        db = SessionLocal()
        try:
            # Find next queued transcription
            transcription = (
                db.query(Transcription)
                .filter(Transcription.status == TranscriptionStatus.QUEUED)
                .order_by(Transcription.created_at)
                .first()
            )

            if transcription:
                logger.info(f"Processing transcription: {transcription.id}")
                self._models_loaded = True
                self._last_activity_time = time.time()

                # Run processing in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.worker.process,
                    transcription,
                    db
                )

                # Update activity time after processing completes
                self._last_activity_time = time.time()
                logger.info(f"Completed transcription: {transcription.id}")
                return True
            return False
        finally:
            db.close()


# Global processor instance
queue_processor = QueueProcessor()
