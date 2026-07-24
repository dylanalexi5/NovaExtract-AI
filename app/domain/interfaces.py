"""
Abstract domain interfaces (Ports).

Defines architectural contracts implemented in the `infrastructure` layer.
Use cases depend exclusively on these abstract interfaces (Dependency Inversion Principle).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedDocument:
    """
    Immutable Value Object representing extracted text and metadata from a document parser.
    """

    text: str
    page_count: int
    metadata: dict[str, str | int | float]


class DocumentParser(ABC):
    """Abstract port interface for document text parsers."""

    @abstractmethod
    def extract_text(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Extracts raw text content from binary file bytes.

        Args:
            file_content: Raw file content bytes.
            filename: Original file name.

        Returns:
            ParsedDocument containing extracted text and document metadata.

        Raises:
            DocumentParsingError: If parsing fails due to corruption or protection.
            EmptyDocumentError: If the document contains no readable text.
        """
        ...


class PIIAnonymizer(ABC):
    """Abstract port interface for Personally Identifiable Information (PII) anonymization."""

    @abstractmethod
    def anonymize(self, text: str) -> str:
        """
        Detects and replaces sensitive PII entities in text with safe placeholders.

        Args:
            text: Raw input text potentially containing PII.

        Returns:
            Sanitized text with PII entities masked by placeholders (e.g. <PERSON>).

        Raises:
            PIIAnonymizationError: If anonymization processing fails.
        """
        ...
