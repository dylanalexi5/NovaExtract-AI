"""
PyMuPDF (fitz) implementation of DocumentParser interface.

Responsibilities:
- Parse PDF documents directly from memory bytes (no disk I/O).
- Extract text blocks ordered by top-to-bottom, left-to-right reading position.
- Handle encrypted, corrupted, or image-only scanned PDFs gracefully.
"""

from __future__ import annotations

import logging

import pymupdf

from app.domain.exceptions import DocumentParsingError, EmptyDocumentError
from app.domain.interfaces import DocumentParser, ParsedDocument

logger = logging.getLogger(__name__)


class PyMuPDFParser(DocumentParser):
    """
    PDF text parser implementation powered by PyMuPDF.

    Extracts text using page.get_text("blocks") to preserve spatial block layout,
    producing cleaner reading order for multi-column resumes and layouts.
    """

    SUPPORTED_CONTENT_TYPES: frozenset[str] = frozenset(
        {"application/pdf", "application/x-pdf"}
    )

    def extract_text(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Extracts text content from PDF file bytes in memory.

        Raises:
            DocumentParsingError: If file is empty, corrupted, or password-encrypted.
            EmptyDocumentError: If no extractable text blocks are found.
        """
        if not file_content:
            raise DocumentParsingError(filename, "File buffer is empty (0 bytes).")

        try:
            doc = pymupdf.open(stream=file_content, filetype="pdf")
        except Exception as exc:
            logger.error("PyMuPDF failed to open '%s': %s", filename, exc)
            raise DocumentParsingError(
                filename,
                f"Failed to open PDF document. It may be corrupted or protected. Detail: {exc}",
            ) from exc

        try:
            if doc.is_encrypted:
                raise DocumentParsingError(
                    filename,
                    "PDF document is password protected. Text extraction is not supported.",
                )

            page_texts: list[str] = []

            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                blocks = page.get_text("blocks")

                # Block tuple structure: (x0, y0, x1, y1, "text", block_no, block_type)
                # block_type: 0 = text block, 1 = image block
                text_blocks = [
                    block[4].strip()
                    for block in sorted(blocks, key=lambda b: (b[1], b[0]))
                    if block[6] == 0 and isinstance(block[4], str) and block[4].strip()
                ]

                if text_blocks:
                    page_texts.append("\n".join(text_blocks))

            full_text = "\n\n".join(page_texts)
            page_count = doc.page_count
            metadata = self._extract_metadata(doc)

        except DocumentParsingError:
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error extracting text from '%s': %s", filename, exc
            )
            raise DocumentParsingError(
                filename, f"Unexpected error during extraction: {exc}"
            ) from exc
        finally:
            doc.close()

        if not full_text.strip():
            raise EmptyDocumentError(filename)

        logger.info(
            "Extracted text from '%s': %d pages, %d characters.",
            filename,
            page_count,
            len(full_text),
        )

        return ParsedDocument(
            text=full_text,
            page_count=page_count,
            metadata=metadata,
        )

    @staticmethod
    def _extract_metadata(doc: pymupdf.Document) -> dict[str, str | int | float]:
        """Extracts basic document metadata from PyMuPDF document properties."""
        raw_meta = doc.metadata or {}
        return {
            key: value
            for key, value in {
                "title": raw_meta.get("title", ""),
                "author": raw_meta.get("author", ""),
                "subject": raw_meta.get("subject", ""),
                "creator": raw_meta.get("creator", ""),
                "producer": raw_meta.get("producer", ""),
                "page_count": doc.page_count,
            }.items()
            if value
        }
