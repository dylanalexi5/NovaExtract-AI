"""
Hybrid Information Extraction Use Case.

Orchestrates the two-layer extraction strategy:
    1. Deterministic layer (Regex): Captures structured patterns at zero cost.
    2. Semantic layer (LLM via instructor): Analyzes unstructured text for complex fields.
    3. Fusion: Merges regex results into the LLM-extracted profile.

The use case depends on injected AIExtractor (infrastructure) and operates
against domain schemas, maintaining Clean Architecture boundaries.
"""

from __future__ import annotations

import logging

from app.domain.models import RawDocument
from app.domain.schemas import CandidateProfile, ExtractionResult
from app.infrastructure.ai.instructor_client import AIExtractor
from app.infrastructure.extractors import RegexExtractionResult, extract_with_regex

logger = logging.getLogger(__name__)


class ExtractInformationUseCase:
    """
    Application service for hybrid CV data extraction.

    Injects AIExtractor via constructor. The regex layer is stateless
    and called as a pure function (no injection needed).
    """

    def __init__(self, ai_extractor: AIExtractor) -> None:
        """
        Args:
            ai_extractor: Instructor-patched LLM client for semantic extraction.
        """
        self._ai_extractor = ai_extractor

    async def execute(self, document: RawDocument) -> ExtractionResult:
        """
        Executes the full hybrid extraction pipeline on a sanitized document.

        Pipeline:
        1. Run regex extraction on sanitized_text (O(n), zero cost).
        2. Send sanitized_text to LLM for semantic extraction via instructor.
        3. Merge regex-extracted fields into the LLM profile (regex takes priority
           for structured fields like email, phone).
        4. Build final ExtractionResult with confidence scoring and HITL flag.

        Args:
            document: RawDocument entity with sanitized text from Phase 2.

        Returns:
            ExtractionResult with merged profile, confidence score, and metadata.

        Raises:
            LLMExtractionError: If LLM processing fails.
            LLMTimeoutError: If LLM request exceeds timeout.
            LLMRateLimitError: If provider rate limit is exceeded.
        """
        logger.info("Starting hybrid extraction for '%s'.", document.filename)

        # ── Layer 1: Deterministic Regex Extraction ──────────────────
        regex_result = extract_with_regex(document.sanitized_text)
        logger.info(
            "Regex layer completed for '%s'. Fields: %s",
            document.filename,
            regex_result.extracted_field_names,
        )

        # ── Layer 2: LLM Semantic Extraction ─────────────────────────
        llm_profile = await self._ai_extractor.extract(
            text=document.sanitized_text,
            response_model=CandidateProfile,
        )

        llm_fields = self._identify_llm_fields(llm_profile)
        logger.info(
            "LLM layer completed for '%s'. Fields extracted: %s",
            document.filename,
            llm_fields,
        )

        # ── Layer 3: Fusion (Regex overrides LLM for structured fields) ──
        merged_profile = self._merge_results(llm_profile, regex_result)

        # ── Build Final Result ───────────────────────────────────────
        # Request confidence score from LLM in a separate lightweight call
        confidence = await self._compute_confidence(document.sanitized_text, merged_profile)

        result = ExtractionResult(
            profile=merged_profile,
            confidence_score=confidence,
            source_filename=document.filename,
            extraction_method="hybrid",
            regex_fields_extracted=regex_result.extracted_field_names,
            llm_fields_extracted=llm_fields,
        )

        logger.info(
            "Extraction completed for '%s'. Confidence: %.2f, Requires review: %s",
            document.filename,
            result.confidence_score,
            result.requires_human_review,
        )

        return result

    @staticmethod
    def _merge_results(
        llm_profile: CandidateProfile,
        regex_result: RegexExtractionResult,
    ) -> CandidateProfile:
        """
        Merges regex-extracted fields into the LLM profile.

        Priority rules:
        - Regex results override LLM for structured fields (email, phone)
          because regex has higher precision for pattern-based data.
        - LLM results are preserved for semantic fields (skills, experience).
        """
        updates: dict[str, str | None] = {}

        # Override email if regex found one (higher precision than LLM for patterns)
        if regex_result.emails:
            updates["email"] = regex_result.emails[0]

        # Override phone if regex found one
        if regex_result.phones:
            updates["phone"] = regex_result.phones[0]

        if updates:
            return llm_profile.model_copy(update=updates)

        return llm_profile

    @staticmethod
    def _identify_llm_fields(profile: CandidateProfile) -> list[str]:
        """Returns list of field names that the LLM populated with non-empty values."""
        fields: list[str] = []

        if profile.full_name:
            fields.append("full_name")
        if profile.professional_summary:
            fields.append("professional_summary")
        if profile.skills:
            fields.append("skills")
        if profile.years_of_experience is not None:
            fields.append("years_of_experience")
        if profile.work_experience:
            fields.append("work_experience")
        if profile.education:
            fields.append("education")
        if profile.languages:
            fields.append("languages")
        if profile.location:
            fields.append("location")

        return fields

    async def _compute_confidence(
        self,
        text: str,
        profile: CandidateProfile,
    ) -> float:
        """
        Computes extraction confidence score based on field completeness.

        Uses a weighted heuristic rather than a second LLM call to avoid
        unnecessary token consumption. Each field contributes to the score
        proportionally to its importance for a complete candidate profile.
        """
        weights: dict[str, float] = {
            "full_name": 0.15,
            "email": 0.10,
            "phone": 0.05,
            "location": 0.05,
            "professional_summary": 0.10,
            "skills": 0.20,
            "years_of_experience": 0.05,
            "work_experience": 0.20,
            "education": 0.05,
            "languages": 0.05,
        }

        score = 0.0

        if profile.full_name:
            score += weights["full_name"]
        if profile.email:
            score += weights["email"]
        if profile.phone:
            score += weights["phone"]
        if profile.location:
            score += weights["location"]
        if profile.professional_summary:
            score += weights["professional_summary"]
        if profile.skills:
            # Partial credit: more skills = higher contribution
            skill_ratio = min(len(profile.skills) / 5.0, 1.0)
            score += weights["skills"] * skill_ratio
        if profile.years_of_experience is not None:
            score += weights["years_of_experience"]
        if profile.work_experience:
            exp_ratio = min(len(profile.work_experience) / 2.0, 1.0)
            score += weights["work_experience"] * exp_ratio
        if profile.education:
            score += weights["education"]
        if profile.languages:
            score += weights["languages"]

        # Clamp to [0.0, 1.0]
        return round(min(max(score, 0.0), 1.0), 2)
