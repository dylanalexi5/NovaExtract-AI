"""
Extraction domain schemas (Structured Outputs).

These Pydantic models define the structured output contract for the LLM.
Field descriptions serve dual purpose:
1. API documentation via OpenAPI/Swagger.
2. Implicit prompt engineering — instructor passes Field descriptions directly
   to the LLM system prompt, guiding structured extraction without manual prompts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


# ── Nested Entity Schemas ────────────────────────────────────────────────


class WorkExperience(BaseModel):
    """Single work experience entry extracted from a CV."""

    job_title: str = Field(
        ...,
        description=(
            "Exact job title or role held by the candidate. "
            "Extract verbatim from the document (e.g. 'Senior Python Developer', 'Data Analyst')."
        ),
    )
    company: str = Field(
        ...,
        description=(
            "Company or organization name where the candidate worked. "
            "If not explicitly stated, return 'Unknown'."
        ),
    )
    duration: str | None = Field(
        default=None,
        description=(
            "Employment period as a human-readable string (e.g. 'Jan 2020 - Dec 2023', "
            "'3 years'). Return null if dates are not mentioned."
        ),
    )
    description: str | None = Field(
        default=None,
        description=(
            "Brief summary of responsibilities or achievements in this role. "
            "Limit to 2-3 sentences maximum. Return null if no description is present."
        ),
    )


class Education(BaseModel):
    """Single education entry extracted from a CV."""

    degree: str = Field(
        ...,
        description=(
            "Degree or certification obtained (e.g. 'B.Sc. Computer Science', "
            "'AWS Solutions Architect'). Extract verbatim."
        ),
    )
    institution: str = Field(
        ...,
        description="Name of the educational institution or certifying body.",
    )
    year: str | None = Field(
        default=None,
        description="Graduation or completion year (e.g. '2021'). Return null if not mentioned.",
    )


# ── Main Extraction Schema ──────────────────────────────────────────────


class CandidateProfile(BaseModel):
    """
    Structured candidate profile extracted from CV text.

    This model is the primary extraction target for the LLM via instructor.
    Each Field description acts as an implicit extraction instruction.
    """

    full_name: str | None = Field(
        default=None,
        description=(
            "Full name of the candidate as it appears in the document header or introduction. "
            "Note: PII may have been anonymized to <PERSON>. If so, return '<PERSON>'."
        ),
    )
    email: str | None = Field(
        default=None,
        description=(
            "Primary email address of the candidate. "
            "Note: may appear as <EMAIL_ADDRESS> if anonymized. Return the placeholder if so."
        ),
    )
    phone: str | None = Field(
        default=None,
        description=(
            "Primary phone number including country code if present. "
            "Note: may appear as <PHONE_NUMBER> if anonymized."
        ),
    )
    location: str | None = Field(
        default=None,
        description=(
            "City, state, or country where the candidate is based. "
            "Extract from address or location sections. Return null if not found."
        ),
    )
    professional_summary: str | None = Field(
        default=None,
        description=(
            "Brief professional summary or career objective stated by the candidate. "
            "Limit to 3 sentences maximum. Return null if no summary section exists."
        ),
    )
    skills: list[str] = Field(
        default_factory=list,
        description=(
            "List of technical and soft skills mentioned throughout the document. "
            "Include programming languages, frameworks, tools, methodologies, and soft skills. "
            "Normalize to lowercase (e.g. ['python', 'fastapi', 'docker', 'team leadership'])."
        ),
    )
    years_of_experience: int | None = Field(
        default=None,
        ge=0,
        le=60,
        description=(
            "Total estimated years of professional work experience. "
            "Calculate from earliest to latest employment date, or extract if explicitly stated. "
            "Return null if not determinable."
        ),
    )
    work_experience: list[WorkExperience] = Field(
        default_factory=list,
        description=(
            "Ordered list of work experience entries from most recent to oldest. "
            "Extract each role with its job title, company, duration, and description."
        ),
    )
    education: list[Education] = Field(
        default_factory=list,
        description=(
            "List of educational degrees, certifications, or relevant coursework. "
            "Extract degree name, institution, and completion year when available."
        ),
    )
    languages: list[str] = Field(
        default_factory=list,
        description=(
            "List of human languages spoken by the candidate with proficiency level if stated "
            "(e.g. ['Spanish - Native', 'English - Professional', 'Portuguese - Basic'])."
        ),
    )


# ── Extraction Result Envelope ───────────────────────────────────────────


class ExtractionResult(BaseModel):
    """
    Final extraction output combining deterministic regex results with LLM semantic analysis.

    Wraps the extracted CandidateProfile with confidence scoring and HITL flagging.
    """

    profile: CandidateProfile = Field(
        ...,
        description="Structured candidate profile extracted from the document.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Overall confidence score for the extraction quality (0.0 to 1.0). "
            "Score 1.0 means all fields were extracted with high certainty. "
            "Score below 0.5 indicates significant missing or ambiguous data. "
            "Consider: completeness of fields, clarity of source text, and extraction certainty."
        ),
    )
    source_filename: str = Field(
        ...,
        description="Original document filename that was processed.",
    )
    extraction_method: str = Field(
        default="hybrid",
        description="Extraction method used: 'regex', 'llm', or 'hybrid'.",
    )
    regex_fields_extracted: list[str] = Field(
        default_factory=list,
        description="List of field names that were extracted deterministically via regex.",
    )
    llm_fields_extracted: list[str] = Field(
        default_factory=list,
        description="List of field names that required LLM semantic analysis.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def requires_human_review(self) -> bool:
        """
        Dynamically flags documents needing HITL review.

        Triggered when confidence_score falls below 0.85 threshold,
        indicating ambiguous or incomplete extraction requiring human validation.
        """
        return self.confidence_score < 0.85
