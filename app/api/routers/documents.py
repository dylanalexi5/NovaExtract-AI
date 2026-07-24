"""
Human-In-The-Loop (HITL) document management endpoints.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_document_repository
from app.domain.repositories import DocumentRepository
from app.infrastructure.database.models import DocumentStatus

router = APIRouter(prefix="/documents", tags=["HITL Documents"])


class StatusUpdateRequest(BaseModel):
    """Payload for updating a document's status in the HITL workflow."""

    status: str = Field(
        ...,
        description="The new status. Must be APPROVED or REJECTED.",
        pattern="^(APPROVED|REJECTED)$",
    )


@router.get(
    "/pending",
    status_code=status.HTTP_200_OK,
    summary="List all documents requiring human review",
)
async def list_pending_documents(
    repository: DocumentRepository = Depends(get_document_repository),
) -> list[dict[str, Any]]:
    """
    Returns all documents in PENDING state (usually due to a low confidence score
    from the AI extractor).
    """
    return await repository.get_pending_documents()


@router.patch(
    "/{document_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update document status",
)
async def update_document_status(
    document_id: uuid.UUID,
    payload: StatusUpdateRequest,
    repository: DocumentRepository = Depends(get_document_repository),
) -> dict[str, str]:
    """
    Updates a document's status (e.g., after human review).
    Normally transitions from PENDING to APPROVED or REJECTED.
    """
    success = await repository.update_status(document_id, payload.status)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    return {"message": f"Document status updated to {payload.status}."}
