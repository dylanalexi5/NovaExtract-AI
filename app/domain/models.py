"""
Domain models (Entities).

Core business entities independent of external frameworks or infrastructure libraries.
"""

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentSource(StrEnum):
    """Source origin type for ingested documents."""

    PDF = "pdf"
    EMAIL = "email"


class RawDocument(BaseModel):
    """
    Represents an ingested document after text extraction and PII anonymization.

    Serves as the domain entity passed into the AI extraction phase (Phase 3).
    """

    filename: str = Field(
        ...,
        description="Original uploaded file name.",
        examples=["john_doe_cv.pdf"],
    )
    source: DocumentSource = Field(
        ...,
        description="Source document channel origin.",
    )
    content_type: str | None = Field(
        default=None,
        description="MIME content type of the original file.",
        examples=["application/pdf"],
    )
    raw_text: str = Field(
        ...,
        description="Text extracted from the document BEFORE PII anonymization.",
    )
    sanitized_text: str = Field(
        ...,
        description="Text AFTER PII anonymization (sensitive entities replaced with placeholders).",
    )
    page_count: int = Field(
        default=0,
        ge=0,
        description="Total page count of the document (0 if non-applicable).",
    )
    char_count: int = Field(
        default=0,
        ge=0,
        description="Total character count of the sanitized text.",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the document was ingested.",
    )

    @property
    def is_empty(self) -> bool:
        """Checks if the document contains non-whitespace text."""
        return len(self.sanitized_text.strip()) == 0
