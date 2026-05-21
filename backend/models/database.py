# models/database.py
"""Database configuration and session management."""
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_PATH = Path.home() / ".transcribeflow" / "transcribeflow.db"
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

        conn.execute(
            text(
                "UPDATE transcriptions "
                "SET workflow_status = 'pending' "
                "WHERE workflow_status IS NULL OR workflow_status = ''"
            )
        )
