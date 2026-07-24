"""
Custom domain exceptions.

Captures specific business logic error scenarios, allowing the API layer
to translate them into appropriate HTTP status codes without coupling.
"""


class DomainError(Exception):
    """Base domain exception. All custom domain exceptions inherit from this."""

    def __init__(self, message: str = "Unspecified domain error") -> None:
        self.message = message
        super().__init__(self.message)


class DocumentParsingError(DomainError):
    """
    Exception raised when a document cannot be parsed.

    Typical causes: corrupted file, password-protected PDF, empty bytes.
    """

    def __init__(self, filename: str, reason: str) -> None:
        self.filename = filename
        self.reason = reason
        super().__init__(f"Failed to parse document '{filename}': {reason}")


class EmptyDocumentError(DomainError):
    """
    Exception raised when a document is parsed successfully but contains no extractable text.

    Commonly occurs with scanned PDFs lacking an OCR text layer.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(
            f"Document '{filename}' contains no extractable text. "
            "It may be a scanned image PDF requiring OCR preprocessing."
        )


class PIIAnonymizationError(DomainError):
    """
    Exception raised when PII anonymization fails.

    Commonly occurs if the required NLP model is unavailable or processing fails.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"PII anonymization processing failed: {reason}")


class UnsupportedFileTypeError(DomainError):
    """
    Exception raised when the provided file type is not supported by any parser.
    """

    def __init__(self, filename: str, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
        super().__init__(
            f"Unsupported file type for '{filename}' "
            f"(content_type={content_type}). Allowed formats: PDF."
        )


class LLMExtractionError(DomainError):
    """
    Exception raised when LLM-based extraction fails.

    Wraps unexpected errors from the AI provider (OpenAI, Groq, etc.).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"LLM extraction failed: {reason}")


class LLMTimeoutError(LLMExtractionError):
    """
    Exception raised when the LLM request exceeds the configured timeout.

    Indicates the AI provider is overloaded or the request payload is too large.
    """

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"LLM request timed out after {timeout_seconds}s. "
            "The provider may be overloaded or the document is too large."
        )


class LLMRateLimitError(LLMExtractionError):
    """
    Exception raised when the AI provider returns a rate limit (429) response.

    Clients should implement exponential backoff or queue the request for retry.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Rate limit exceeded for LLM provider '{provider}'. "
            "Retry after backoff or upgrade API tier."
        )

