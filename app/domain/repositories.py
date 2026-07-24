"""
Abstract repository interfaces (Ports) for the domain layer.

Ensures that Use Cases depend on abstractions, not on concrete ORM implementations.
"""

import uuid
from abc import ABC, abstractmethod

from app.domain.schemas import ExtractionResult


class DocumentRepository(ABC):
    """
    Abstract interface for persisting and retrieving extracted documents.
    """

    @abstractmethod
    async def save(self, result: ExtractionResult, status: str) -> uuid.UUID:
        """
        Persists a new extraction result into the database.

        Args:
            result: The structured extraction result to save.
            status: Initial status string (e.g. "PENDING", "APPROVED").

        Returns:
            The generated UUID of the saved document.
        """
        ...

    @abstractmethod
    async def get_by_id(self, document_id: uuid.UUID) -> dict | None:
        """
        Retrieves a document by its ID.

        Returns:
            A dictionary representing the document, or None if not found.
        """
        ...

    @abstractmethod
    async def get_pending_documents(self) -> list[dict]:
        """
        Retrieves all documents currently in PENDING status.
        Useful for the HITL (Human-in-the-loop) review queue.

        Returns:
            A list of dictionary representations of pending documents.
        """
        ...

    @abstractmethod
    async def update_status(self, document_id: uuid.UUID, new_status: str) -> bool:
        """
        Updates the status of a specific document (e.g. after human review).

        Args:
            document_id: The UUID of the document.
            new_status: The new status string to apply.

        Returns:
            True if the document was updated, False if it was not found.
        """
        ...
