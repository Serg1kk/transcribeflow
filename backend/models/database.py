# models/database.py
"""Database configuration and session management."""
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# The engine is bound at import time, so the location has to be settable from
# the environment — by the time any fixture runs it is already too late to
# redirect it. Without this the test suite writes into the real database.
DEFAULT_DATABASE_PATH = Path.home() / ".transcribeflow" / "transcribeflow.db"
DATABASE_PATH = Path(
    os.environ.get("TRANSCRIBEFLOW_DB_PATH") or DEFAULT_DATABASE_PATH
).expanduser()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(transcriptions)"))
        }

        if "workflow_status" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN workflow_status VARCHAR(20) DEFAULT 'pending'"
                )
            )

        if "workflow_comment" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN workflow_comment TEXT"
                )
            )

        if "elevenlabs_keyterms" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN elevenlabs_keyterms JSON"
                )
            )

        if "elevenlabs_entity_detection" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN elevenlabs_entity_detection JSON"
                )
            )

        if "elevenlabs_entity_redaction" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN elevenlabs_entity_redaction JSON"
                )
            )

        if "elevenlabs_entity_redaction_mode" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE transcriptions "
                    "ADD COLUMN elevenlabs_entity_redaction_mode VARCHAR(50)"
                )
            )

        conn.execute(
            text(
                "UPDATE transcriptions "
                "SET workflow_status = 'pending' "
                "WHERE workflow_status IS NULL OR workflow_status = ''"
            )
        )

        conn.execute(
            text(
                "UPDATE transcriptions "
                "SET model = 'scribe_v2' "
                "WHERE engine = 'elevenlabs' AND model = 'scribe_v1'"
            )
        )
