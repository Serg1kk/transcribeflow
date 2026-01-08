# workers/queue_processor.py
"""Background queue processor for transcription tasks."""
import asyncio
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import Transcription, TranscriptionStatus, SessionLocal
from workers.transcription_worker import TranscriptionWorker

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processes transcription tasks from the queue in the background."""

    def __init__(self):
        self.worker = TranscriptionWorker()
        self._running = False
        self._task: Optional[asyncio.Task] = None

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
                await self._process_next()
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")

            # Wait before checking for next task
            await asyncio.sleep(2)

    async def _process_next(self):
        """Process the next queued task."""
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

                # Run processing in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.worker.process,
                    transcription,
                    db
                )

                logger.info(f"Completed transcription: {transcription.id}")
        finally:
            db.close()


# Global processor instance
queue_processor = QueueProcessor()
