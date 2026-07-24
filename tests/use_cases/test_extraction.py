"""
Unit tests for the ExtractInformationUseCase.

Ensures the use case orchestration correctly delegates to the AI Extractor,
without hitting the actual Groq API or network.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.domain.exceptions import LLMExtractionError
from app.domain.models import DocumentSource, RawDocument
from app.domain.schemas import CandidateProfile, ExtractionResult
from app.use_cases.extract_information import ExtractInformationUseCase


@pytest.fixture
def mock_raw_document() -> RawDocument:
    return RawDocument(
        filename="test.pdf",
        source=DocumentSource.PDF,
        content_type="application/pdf",
        raw_text="Mock raw text",
        sanitized_text="Mock sanitized text",
        page_count=1,
        char_count=20,
    )


@pytest.mark.asyncio
async def test_extraction_use_case_happy_path(
    mock_raw_document: RawDocument, mock_groq_llm_payload: dict
):
    """
    Test 1 (Happy Path): Mocks the AI extractor, calls the use case,
    and verifies that it returns the expected ExtractionResult properly structured.
    """
    # Arrange
    mock_ai_extractor = AsyncMock()
    # Simulate a successful return from the LLM
    mock_ai_extractor.extract.return_value = CandidateProfile(**mock_groq_llm_payload)
    
    use_case = ExtractInformationUseCase(ai_extractor=mock_ai_extractor)

    # Act
    result = await use_case.execute(mock_raw_document)

    # Assert
    mock_ai_extractor.extract.assert_called_once_with(
        text=mock_raw_document.sanitized_text,
        response_model=CandidateProfile,
    )
    assert isinstance(result, ExtractionResult)
    assert result.source_filename == "test.pdf"
    assert result.extraction_method == "hybrid"
    assert result.profile.full_name == "Dylan M"
    # Given the use case sets confidence to 0.95 artificially in the current implementation 
    # (since LLM extraction succeeded), let's ensure it has a score.
    assert result.confidence_score > 0.0


@pytest.mark.asyncio
async def test_extraction_use_case_handles_ai_error(mock_raw_document: RawDocument):
    """
    Test 2 (Error Handling): Simulates an error thrown by the AI engine (e.g. Tenacity
    failing after retries), verifying that the Use Case propagates the domain exception.
    """
    # Arrange
    mock_ai_extractor = AsyncMock()
    mock_ai_extractor.extract.side_effect = LLMExtractionError("Mock LLM Failure")
    
    use_case = ExtractInformationUseCase(ai_extractor=mock_ai_extractor)

    # Act & Assert
    with pytest.raises(LLMExtractionError, match="Mock LLM Failure"):
        await use_case.execute(mock_raw_document)
