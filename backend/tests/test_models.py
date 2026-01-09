# tests/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.transcription import Transcription, TranscriptionStatus


def test_transcription_model_creation():
    """Test that a transcription can be created with required fields."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    transcription = Transcription(
        filename="test.mp3",
        original_path="/path/to/test.mp3",
        engine="mlx-whisper",
        model="large-v2",
    )
    session.add(transcription)
    session.commit()

    assert transcription.id is not None
    assert transcription.status == TranscriptionStatus.QUEUED
    assert transcription.filename == "test.mp3"
    session.close()


def test_transcription_status_transitions():
    """Test status can be updated through transitions."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    transcription = Transcription(
        filename="test.mp3",
        original_path="/path/to/test.mp3",
        engine="mlx-whisper",
        model="large-v2",
    )
    session.add(transcription)
    session.commit()

    transcription.status = TranscriptionStatus.PROCESSING
    session.commit()
    assert transcription.status == TranscriptionStatus.PROCESSING

    transcription.status = TranscriptionStatus.COMPLETED
    session.commit()
    assert transcription.status == TranscriptionStatus.COMPLETED
    session.close()


def test_transcription_status_has_draft():
    """Test that DRAFT status exists in TranscriptionStatus enum."""
    from models.transcription import TranscriptionStatus

    assert hasattr(TranscriptionStatus, 'DRAFT')
    assert TranscriptionStatus.DRAFT.value == "draft"


def test_transcription_has_initial_prompt_field():
    """Test that Transcription model has initial_prompt field."""
    from models.transcription import Transcription
    from sqlalchemy import inspect

    mapper = inspect(Transcription)
    column_names = [c.key for c in mapper.columns]
    assert 'initial_prompt' in column_names


def test_transcription_speaker_names_json():
    """Test speaker names are stored as JSON."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    transcription = Transcription(
        filename="test.mp3",
        original_path="/path/to/test.mp3",
        engine="mlx-whisper",
        model="large-v2",
        speaker_names={"SPEAKER_00": "Ivan", "SPEAKER_01": "Maria"}
    )
    session.add(transcription)
    session.commit()

    fetched = session.query(Transcription).filter_by(id=transcription.id).first()
    assert fetched.speaker_names["SPEAKER_00"] == "Ivan"
    session.close()


def test_llm_operation_model_exists():
    """Test LLMOperation model can be imported."""
    from models.llm_operation import LLMOperation, LLMOperationStatus
    assert LLMOperation is not None
    assert LLMOperationStatus is not None


def test_llm_operation_status_values():
    """Test LLMOperationStatus enum has expected values."""
    from models.llm_operation import LLMOperationStatus
    assert LLMOperationStatus.SUCCESS.value == "success"
    assert LLMOperationStatus.FAILED.value == "failed"
