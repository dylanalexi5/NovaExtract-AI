"""
Concrete SQLAlchemy implementation of the DocumentRepository interface.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories import DocumentRepository
from app.domain.schemas import ExtractionResult
from app.infrastructure.database.models import DocumentModel, DocumentStatus

logger = logging.getLogger(__name__)


class PostgresDocumentRepository(DocumentRepository):
    """
    PostgreSQL-backed implementation of DocumentRepository using SQLAlchemy 2.0.

    Injects the AsyncSession to perform non-blocking database I/O.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Args:
            session: An active SQLAlchemy AsyncSession.
        """
        self._session = session

    async def save(self, result: ExtractionResult, status: str) -> uuid.UUID:
        """Saves a new document extraction to the database."""
        # Map string status to Enum
        try:
            doc_status = DocumentStatus(status.upper())
        except ValueError:
            doc_status = DocumentStatus.PENDING
            logger.warning("Invalid status '%s' provided. Defaulting to PENDING.", status)

        model = DocumentModel(
            filename=result.source_filename,
            raw_text="REDACTED",  # Normally we'd pass raw text if needed, or leave redacted
            extracted_data=result.model_dump(mode="json"),
            confidence_score=result.confidence_score,
            status=doc_status,
        )

        self._session.add(model)
        await self._session.flush()  # Generate UUID without committing yet
        doc_id = model.id

        logger.info("Saved document extraction with ID: %s", doc_id)
        return doc_id

    async def get_by_id(self, document_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieves a document by UUID."""
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_dict(model)

    async def get_pending_documents(self) -> list[dict[str, Any]]:
        """Retrieves all documents awaiting human review."""
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.status == DocumentStatus.PENDING)
            .order_by(DocumentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_dict(m) for m in models]

    async def update_status(self, document_id: uuid.UUID, new_status: str) -> bool:
        """Updates document status (e.g., from PENDING to APPROVED)."""
        try:
            target_status = DocumentStatus(new_status.upper())
        except ValueError:
            logger.error("Attempted to update to invalid status: %s", new_status)
            return False

        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            logger.warning("Attempted to update non-existent document: %s", document_id)
            return False

        model.status = target_status
        await self._session.flush()
        logger.info("Updated document %s status to %s", document_id, target_status.value)
        return True

    @staticmethod
    def _to_dict(model: DocumentModel) -> dict[str, Any]:
        """Maps SQLAlchemy model to a plain dictionary for use case boundary."""
        return {
            "id": str(model.id),
            "filename": model.filename,
            "extracted_data": model.extracted_data,
            "confidence_score": model.confidence_score,
            "status": model.status.value,
            "created_at": model.created_at.isoformat(),
            "updated_at": model.updated_at.isoformat(),
        }
