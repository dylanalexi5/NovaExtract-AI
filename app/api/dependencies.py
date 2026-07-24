"""
Centralized Dependency Injection (DI) providers for FastAPI.

This module acts as the Composition Root of the application, wiring together
Infrastructure adapters, Domain repositories, and Use Cases.
By centralizing DI here, we keep the API routers completely free of instantiation
logic, making them thin and highly testable.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.interfaces import DocumentParser, PIIAnonymizer
from app.domain.repositories import DocumentRepository
from app.infrastructure.ai.instructor_client import AIExtractor
from app.infrastructure.database.repository import PostgresDocumentRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.parsers.pdf_parser import PyMuPDFParser
from app.infrastructure.security.presidio_anonymizer import PresidioPIIAnonymizer
from app.use_cases.extract_information import ExtractInformationUseCase
from app.use_cases.ingest_document import IngestDocumentUseCase

# ── Infrastructure Providers ───────────────────────────────────────────

def get_document_parser() -> DocumentParser:
    """Provides a concrete PDF parser."""
    return PyMuPDFParser()


def get_pii_anonymizer() -> PIIAnonymizer:
    """Provides the Presidio PII anonymizer engine."""
    return PresidioPIIAnonymizer()


def get_ai_extractor(
    settings: Settings = Depends(get_settings),
) -> AIExtractor:
    """Provides the configured instructor LLM client."""
    return AIExtractor(settings=settings)


def get_document_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentRepository:
    """Provides the PostgreSQL document repository."""
    return PostgresDocumentRepository(session=session)


# ── Use Case Providers ─────────────────────────────────────────────────

def get_ingest_use_case(
    parser: DocumentParser = Depends(get_document_parser),
    anonymizer: PIIAnonymizer = Depends(get_pii_anonymizer),
) -> IngestDocumentUseCase:
    """Assembles the Document Ingestion use case."""
    return IngestDocumentUseCase(parser=parser, anonymizer=anonymizer)


def get_extract_use_case(
    ai_extractor: AIExtractor = Depends(get_ai_extractor),
) -> ExtractInformationUseCase:
    """Assembles the Hybrid Information Extraction use case."""
    return ExtractInformationUseCase(ai_extractor=ai_extractor)
