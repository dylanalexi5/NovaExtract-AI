"""
Document Ingestion Use Case.

Orchestrates full ingestion pipeline flow:
    Physical File Bytes → Text Extraction → PII Anonymization → RawDocument Entity

Operates exclusively against abstract domain interfaces via Constructor Dependency Injection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.exceptions import UnsupportedFileTypeError
from app.domain.interfaces import DocumentParser, PIIAnonymizer
from app.domain.models import DocumentSource, RawDocument

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    """
    Application service orchestrating document ingestion.

    Dependencies are injected via constructor to enable complete decoupling and unit testability.
    """

    SUPPORTED_PDF_TYPES: frozenset[str] = frozenset(
        {"application/pdf", "application/x-pdf"}
    )

    def __init__(
        self,
        parser: DocumentParser,
        anonymizer: PIIAnonymizer,
    ) -> None:
        """
        Args:
            parser: Concrete DocumentParser implementation.
            anonymizer: Concrete PIIAnonymizer implementation.
        """
        self._parser = parser
        self._anonymizer = anonymizer

    def execute(
        self,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> RawDocument:
        """
        Executes document ingestion pipeline.

        Pipeline steps:
        1. Validate file source type.
        2. Extract raw text via parser.
        3. Anonymize sensitive PII via anonymizer.
        4. Construct and return RawDocument domain entity.

        Args:
            file_content: Binary file bytes.
            filename: Original uploaded file name.
            content_type: MIME content type (optional).

        Returns:
            RawDocument entity populated with raw and sanitized text.

        Raises:
            UnsupportedFileTypeError: If file extension or content_type is unsupported.
            DocumentParsingError: If text extraction fails.
            EmptyDocumentError: If document contains no readable text.
            PIIAnonymizationError: If PII masking fails.
        """
        # Step 1: Validate file type
        source = self._resolve_source(filename, content_type)
        logger.info("Starting ingestion for '%s' (source=%s).", filename, source.value)

        # Step 2: Extract raw text
        parsed = self._parser.extract_text(file_content, filename)
        logger.info(
            "Extracted text from '%s': %d pages, %d characters.",
            filename,
            parsed.page_count,
            len(parsed.text),
        )

        # Step 3: Sanitize PII
        sanitized_text = self._anonymizer.anonymize(parsed.text)
        logger.info(
            "Sanitized text for '%s': %d -> %d characters.",
            filename,
            len(parsed.text),
            len(sanitized_text),
        )

        # Step 4: Build domain model
        return RawDocument(
            filename=filename,
            source=source,
            content_type=content_type,
            raw_text=parsed.text,
            sanitized_text=sanitized_text,
            page_count=parsed.page_count,
            char_count=len(sanitized_text),
            ingested_at=datetime.now(timezone.utc),
        )

    def _resolve_source(
        self, filename: str, content_type: str | None
    ) -> DocumentSource:
        """
        Resolves document source origin.

        Prioritizes explicit MIME content_type; falls back to file extension matching.

        Raises:
            UnsupportedFileTypeError: If file type is unsupported.
        """
        if content_type and content_type in self.SUPPORTED_PDF_TYPES:
            return DocumentSource.PDF

        lower_name = filename.lower()
        if lower_name.endswith(".pdf"):
            return DocumentSource.PDF

        raise UnsupportedFileTypeError(filename, content_type)
