# tests/test_llm_operation_type.py
"""Tests for LLM operation type field."""
import pytest
from models.llm_operation import LLMOperation, LLMOperationStatus, LLMOperationType


def test_llm_operation_type_enum():
    """Test LLMOperationType enum has correct values."""
    assert LLMOperationType.CLEANUP.value == "cleanup"
    assert LLMOperationType.INSIGHTS.value == "insights"


def test_llm_operation_can_set_type():
    """Test LLMOperation can be created with operation_type."""
    op = LLMOperation(
        transcription_id="test-123",
        provider="gemini",
        model="gemini-2.5-flash",
        template_id="it-meeting",
        temperature=0.2,
        input_tokens=100,
        output_tokens=50,
        processing_time_seconds=1.5,
        status=LLMOperationStatus.SUCCESS,
        operation_type=LLMOperationType.CLEANUP,
    )
    assert op.operation_type == LLMOperationType.CLEANUP


def test_llm_operation_insights_type():
    """Test LLMOperation can be created with INSIGHTS type."""
    op = LLMOperation(
        transcription_id="test-123",
        provider="gemini",
        model="gemini-2.5-flash",
        template_id="it-meeting",
        temperature=0.2,
        input_tokens=100,
        output_tokens=50,
        processing_time_seconds=1.5,
        status=LLMOperationStatus.SUCCESS,
        operation_type=LLMOperationType.INSIGHTS,
    )
    assert op.operation_type == LLMOperationType.INSIGHTS
