"""
Deterministic regex extraction layer.

Extracts structured fields from raw text using compiled regular expressions.
Runs before the LLM layer to capture predictable patterns at zero token cost
and O(n) time complexity. Fields extracted here are merged into the final
ExtractionResult and excluded from the LLM prompt context.

Supported extractions:
- Email addresses (RFC 5322 simplified)
- Phone numbers (international formats)
- URLs / LinkedIn profiles
- Date ranges (employment periods)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Compiled Regex Patterns ──────────────────────────────────────────────

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?"  # Optional country code
    r"(?:\(?\d{2,4}\)?[\s\-.]?)?"  # Optional area code
    r"\d{3,4}[\s\-.]?\d{3,4}",  # Local number segments
)

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?",
    re.IGNORECASE,
)

# Date range: "Jan 2020 - Dec 2023", "2019 - Present", "03/2018 - 07/2021"
# Requires at least a month prefix OR a 4-digit year to avoid phone number false positives
DATE_RANGE_PATTERN = re.compile(
    r"(?:"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})"  # Month YYYY
    r"|(?:\d{4})"  # or bare YYYY
    r")"
    r"\s*[-–—]\s*"
    r"(?:"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})"  # Month YYYY
    r"|(?:\d{4})"  # or YYYY
    r"|(?:[Pp]resent|[Aa]ctual|[Cc]urrent)"  # or Present/Actual/Current
    r")",
    re.IGNORECASE,
)


@dataclass
class RegexExtractionResult:
    """Container for deterministically extracted field values."""

    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    linkedin_url: str | None = None
    date_ranges: list[str] = field(default_factory=list)

    @property
    def extracted_field_names(self) -> list[str]:
        """Returns list of field names that contain extracted values."""
        fields: list[str] = []
        if self.emails:
            fields.append("email")
        if self.phones:
            fields.append("phone")
        if self.urls:
            fields.append("urls")
        if self.linkedin_url:
            fields.append("linkedin_url")
        if self.date_ranges:
            fields.append("date_ranges")
        return fields


def extract_with_regex(text: str) -> RegexExtractionResult:
    """
    Applies deterministic regex patterns against document text.

    Runs all compiled patterns in a single pass, deduplicates results,
    and returns structured extraction without any LLM cost.

    Args:
        text: Raw or sanitized document text.

    Returns:
        RegexExtractionResult with all pattern matches.
    """
    # Extract emails (deduplicated, lowercased)
    emails = list({m.lower() for m in EMAIL_PATTERN.findall(text)})

    # Extract phone numbers (deduplicated, stripped)
    raw_phones = PHONE_PATTERN.findall(text)
    phones = list({p.strip() for p in raw_phones if len(p.strip()) >= 7})

    # Extract URLs (deduplicated)
    urls = list({m for m in URL_PATTERN.findall(text)})

    # Extract LinkedIn specifically (first match)
    linkedin_match = LINKEDIN_PATTERN.search(text)
    linkedin_url = linkedin_match.group(0) if linkedin_match else None

    # Extract date ranges for employment periods
    date_ranges = list({m.strip() for m in DATE_RANGE_PATTERN.findall(text)})

    result = RegexExtractionResult(
        emails=emails,
        phones=phones,
        urls=urls,
        linkedin_url=linkedin_url,
        date_ranges=date_ranges,
    )

    logger.info(
        "Regex extraction completed. Fields extracted: %s",
        result.extracted_field_names,
    )

    return result
