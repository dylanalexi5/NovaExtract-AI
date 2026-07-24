"""
Unit tests for the Domain layer schemas (Pydantic Models).

Ensures that structured outputs and validation rules operate correctly.
"""

import pytest
from pydantic import ValidationError

from app.api.routers.documents import StatusUpdateRequest
from app.domain.schemas import CandidateProfile, ExtractionResult


def test_extraction_result_sets_pending_status_on_low_confidence(mock_groq_llm_payload: dict):
    """
    Test 1: If confidence_score is 0.84 (below 0.85 threshold),
    requires_human_review must be True (which translates to PENDING status).
    """
    profile = CandidateProfile(**mock_groq_llm_payload)
    result = ExtractionResult(
        profile=profile,
        confidence_score=0.84,
        source_filename="test.pdf",
    )
    
    assert result.requires_human_review is True


def test_extraction_result_sets_approved_status_on_high_confidence(mock_groq_llm_payload: dict):
    """
    Test 2: If confidence_score is 0.90 (above threshold),
    requires_human_review must be False (which translates to APPROVED status).
    """
    profile = CandidateProfile(**mock_groq_llm_payload)
    result = ExtractionResult(
        profile=profile,
        confidence_score=0.90,
        source_filename="test.pdf",
    )
    
    assert result.requires_human_review is False


def test_status_update_request_rejects_invalid_status():
    """
    Test 3: Validates that the schema throws a ValidationError
    if trying to assign a non-allowed status (e.g., "IN_PROGRESS").
    """
    with pytest.raises(ValidationError) as exc_info:
        StatusUpdateRequest(status="IN_PROGRESS")
        
    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert "String should match pattern" in errors[0]["msg"]
    assert errors[0]["loc"][0] == "status"


def test_status_update_request_accepts_valid_status():
    """Verifies that allowed statuses do not raise errors."""
    req_approved = StatusUpdateRequest(status="APPROVED")
    req_rejected = StatusUpdateRequest(status="REJECTED")
    
    assert req_approved.status == "APPROVED"
    assert req_rejected.status == "REJECTED"
