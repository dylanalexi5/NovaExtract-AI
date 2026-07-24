"""
Extraction API endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import (
    get_document_repository,
    get_extract_use_case,
    get_ingest_use_case,
)
from app.domain.exceptions import (
    DocumentParsingError,
    EmptyDocumentError,
    LLMExtractionError,
    LLMRateLimitError,
    LLMTimeoutError,
    PIIAnonymizationError,
    UnsupportedFileTypeError,
)
from app.domain.repositories import DocumentRepository
from app.infrastructure.database.models import DocumentStatus
from app.use_cases.extract_information import ExtractInformationUseCase
from app.use_cases.ingest_document import IngestDocumentUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["Extraction"])


@router.post(
    "/pdf",
    status_code=status.HTTP_201_CREATED,
    summary="Extract structured data from a PDF resume",
)
async def extract_pdf(
    file: UploadFile = File(...),
    ingest_use_case: IngestDocumentUseCase = Depends(get_ingest_use_case),
    extract_use_case: ExtractInformationUseCase = Depends(get_extract_use_case),
    repository: DocumentRepository = Depends(get_document_repository),
) -> dict[str, Any]:
    """
    Ingests, sanitizes, and extracts structured profile data from a PDF document.

    The extraction happens via a hybrid engine (Regex + LLM). The result is persisted
    automatically to the database. If the confidence score is high, it is marked
    as APPROVED, otherwise it goes to the PENDING queue for human review.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    try:
        content = await file.read()

        # Step 1: Ingest and Anonymize
        raw_document = ingest_use_case.execute(
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )

        # Step 2: Extract Structured Information
        extraction_result = await extract_use_case.execute(raw_document)

        # Step 3: Persist and determine workflow status
        initial_status = (
            DocumentStatus.PENDING.value
            if extraction_result.requires_human_review
            else DocumentStatus.APPROVED.value
        )

        document_id = await repository.save(
            result=extraction_result,
            status=initial_status,
        )

        return {
            "document_id": str(document_id),
            "status": initial_status,
            "confidence_score": extraction_result.confidence_score,
            "extracted_data": extraction_result.profile.model_dump(exclude_none=True),
        }

    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=exc.message)
    except (DocumentParsingError, EmptyDocumentError, PIIAnonymizationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except LLMRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message)
    except LLMExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during PDF extraction: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during extraction.",
        )
