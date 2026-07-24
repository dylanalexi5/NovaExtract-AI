"""
Microsoft Presidio implementation of PIIAnonymizer interface.

Responsibilities:
- Detect PII entities (PERSON, EMAIL_ADDRESS, PHONE_NUMBER, etc.) in text.
- Mask detected entities with safe, typed placeholders (e.g. <PERSON>, <EMAIL_ADDRESS>).
- Run 100% locally with zero external network data transmission.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.domain.exceptions import PIIAnonymizationError
from app.domain.interfaces import PIIAnonymizer

logger = logging.getLogger(__name__)


class PresidioPIIAnonymizer(PIIAnonymizer):
    """
    PII Sanitizer powered by Microsoft Presidio.

    Language Strategy:
    Uses spaCy model (default: en_core_web_lg) as the NLP engine backend.
    Pattern-based recognizers (emails, phone numbers, credit cards, IP addresses)
    are language-agnostic. The NER backend identifies PERSON and LOCATION entities.

    Configurable confidence score threshold controls detection sensitivity vs recall balance.
    """

    DEFAULT_ENTITIES: ClassVar[list[str]] = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "IBAN_CODE",
        "IP_ADDRESS",
        "LOCATION",
        "URL",
    ]

    DEFAULT_SCORE_THRESHOLD: ClassVar[float] = 0.35

    def __init__(
        self,
        spacy_model: str = "en_core_web_lg",
        entities: list[str] | None = None,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> None:
        """
        Initializes Presidio engines with specified spaCy model configuration.

        Args:
            spacy_model: spaCy model name to load.
            entities: Target PII entity types to detect.
            score_threshold: Minimum detection confidence threshold (0.0 to 1.0).

        Raises:
            PIIAnonymizationError: If spaCy model or Presidio engine fails to initialize.
        """
        self._entities = entities or self.DEFAULT_ENTITIES
        self._score_threshold = score_threshold
        self._analysis_language = "en"

        try:
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": spacy_model}],
            }
            nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()

            self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self._anonymizer = AnonymizerEngine()
        except Exception as exc:
            logger.error("Failed to initialize Presidio: %s", exc)
            raise PIIAnonymizationError(
                f"Failed to initialize Presidio engine. "
                f"Is spaCy model '{spacy_model}' installed? "
                f"Run: python -m spacy download {spacy_model}. "
                f"Detail: {exc}"
            ) from exc

        logger.info(
            "PresidioPIIAnonymizer initialized. Model: %s, Entities: %s, Threshold: %.2f",
            spacy_model,
            self._entities,
            self._score_threshold,
        )

    def anonymize(self, text: str) -> str:
        """
        Detects and replaces sensitive PII entities in text with placeholders.

        Args:
            text: Raw input text.

        Returns:
            Sanitized text with PII entities masked.

        Raises:
            PIIAnonymizationError: If analyzer or anonymizer processing fails.
        """
        if not text or not text.strip():
            return text

        try:
            results = self._analyzer.analyze(
                text=text,
                entities=self._entities,
                language=self._analysis_language,
                score_threshold=self._score_threshold,
            )

            if not results:
                logger.debug("No PII entities detected in input text.")
                return text

            operators = {
                entity_type: OperatorConfig(
                    "replace", {"new_value": f"<{entity_type}>"}
                )
                for entity_type in self._entities
            }

            anonymized_result = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=operators,
            )

            entities_found = len(results)
            entity_types = {r.entity_type for r in results}
            logger.info(
                "PII sanitized: %d entities detected. Types: %s",
                entities_found,
                entity_types,
            )

            return anonymized_result.text

        except PIIAnonymizationError:
            raise
        except Exception as exc:
            logger.error("Error during PII anonymization: %s", exc)
            raise PIIAnonymizationError(
                f"Unexpected error during PII analysis: {exc}"
            ) from exc
