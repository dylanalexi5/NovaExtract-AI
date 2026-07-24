"""
SQLAlchemy 2.0 ORM Models using DeclarativeBase and strict typing (Mapped[T]).
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


class DocumentStatus(enum.Enum):
    """Status lifecycle of an ingested document."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def _utcnow() -> datetime:
    """Helper to return aware UTC datetime for defaults."""
    return datetime.now(timezone.utc)


class DocumentModel(Base):
    """
    Persisted document entity representing the extraction results.

    Stored in PostgreSQL using asyncpg.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum", create_type=False),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
