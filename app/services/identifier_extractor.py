"""
Identifier and relationship extraction service.

This module performs deterministic extraction only.
It does not use an LLM.
"""

import re

from rapidfuzz import fuzz
from rapidfuzz import process

from app.models.identifier_extraction import (
    ExtractionConfidence,
)
from app.models.identifier_extraction import (
    ExtractedIdentifier,
)
from app.models.identifier_extraction import (
    ExtractedRelationship,
)
from app.models.identifier_extraction import (
    IdentifierExtractionResult,
)
from app.models.identifier_extraction import (
    RelationshipType,
)
from app.models.text_extraction import (
    TextExtractionResult,
)


class IdentifierExtractor:
    """
    Extract identifiers and relationship signals from Government Orders.

    Extraction strategy:

    1. Regex-first extraction.
    2. OCR-tolerant normalization for matching.
    3. RapidFuzz fallback for department matching.
    4. Explicit review flags for uncertain values.
    """

    DEPARTMENTS = [
        "Finance Department",
        "General Administration Department",
        "Home Department",
        "Revenue Department",
        "Health and Family Welfare Department",
        "Local Self Government Department",
        "Education Department",
        "Industries Department",
        "Agriculture Department",
        "Transport Department",
        "Water Resources Department",
    ]

    GO_NUMBER_PATTERN = re.compile(
        r"""
        G\.?\s*O\.?
        \s*
        \(?
        (?P<category>P|Rt)
        \)?
        \s*
        (?:No\.?|N[o0]\.?)
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    DATE_PATTERN = re.compile(
        r"""
        (?:
            \d{1,2}[./-]\d{1,2}[./-]\d{4}
            |
            \d{4}[./-]\d{1,2}[./-]\d{1,2}
        )
        """,
        re.VERBOSE,
    )

    RELATIONSHIP_PHRASES = {
        RelationshipType.AMENDS: [
            "amends",
            "amended by",
            "amendment to",
            "ഭേദഗതി",
            "ഭേദഗതി ചെയ്യുന്നു",
        ],
        RelationshipType.SUPERSEDES: [
            "supersedes",
            "in supersession of",
            "superseded by",
            "മാറ്റിസ്ഥാപിക്കുന്നു",
        ],
        RelationshipType.CANCELS: [
            "cancels",
            "cancelled",
            "canceled",
            "stands cancelled",
            "റദ്ദാക്കുന്നു",
            "റദ്ദാക്കി",
        ],
        RelationshipType.READ_AS: [
            "read as",
            "shall be read as",
            "വായിക്കേണ്ടത്",
        ],
    }

    DEPARTMENT_THRESHOLD = 75

    def extract(
        self,
        text_result: TextExtractionResult,
    ) -> IdentifierExtractionResult:
        """
        Extract identifiers and relationship signals.

        Args:
            text_result: Raw page-wise text from Module 4.

        Returns:
            Structured extraction result.
        """

        result = IdentifierExtractionResult(
            document_id=text_result.document_id
        )

        for page in text_result.pages:
            self._extract_go_numbers(
                page.text,
                result,
            )

            self._extract_dates(
                page.text,
                result,
            )

            self._extract_departments(
                page.text,
                result,
            )

            self._extract_relationships(
                page.text,
                page.page_number,
                result,
            )

        return result

    def _extract_go_numbers(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """Extract GO numbers using OCR-tolerant regex."""

        for match in self.GO_NUMBER_PATTERN.finditer(text):
            category = match.group(
                "category"
            )

            number = match.group(
                "number"
            )

            year = match.group(
                "year"
            )

            department = match.group(
                "department"
            )

            normalized_value = (
                f"G.O.({category}) "
                f"No. {number}/{year}/{department}"
            )

            self._add_unique_identifier(
                collection=result.go_numbers,
                identifier=ExtractedIdentifier(
                    value=normalized_value,
                    confidence=ExtractionConfidence.HIGH,
                    extraction_method="REGEX",
                ),
            )

    def _extract_dates(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """Extract date-like values."""

        for match in self.DATE_PATTERN.finditer(text):
            value = match.group(0)

            self._add_unique_identifier(
                collection=result.issue_dates,
                identifier=ExtractedIdentifier(
                    value=value,
                    confidence=ExtractionConfidence.MEDIUM,
                    extraction_method="REGEX",
                ),
            )

    def _extract_departments(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """Match issuing departments using exact and fuzzy matching."""

        normalized_text = " ".join(
            text.split()
        )

        text_lower = normalized_text.lower()

        for department in self.DEPARTMENTS:
            if department.lower() in text_lower:
                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=department,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method="EXACT",
                    ),
                )

        words = normalized_text.split()

        if not words:
            return

        for department in self.DEPARTMENTS:
            match = process.extractOne(
                department,
                words,
                scorer=fuzz.partial_ratio,
            )

            if match is None:
                continue

            matched_value, score, _ = match

            if score >= 95:
                continue

            if score >= self.DEPARTMENT_THRESHOLD:
                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=department,
                        confidence=ExtractionConfidence.MEDIUM,
                        extraction_method="FUZZY",
                    ),
                )

                result.review_flags.append(
                    "Department matched using fuzzy "
                    f"matching: {matched_value} -> "
                    f"{department}"
                )

    def _extract_relationships(
        self,
        text: str,
        page_number: int,
        result: IdentifierExtractionResult,
    ) -> None:
        """Extract amendment and status relationship phrases."""

        text_lower = text.lower()

        for relationship_type, phrases in (
            self.RELATIONSHIP_PHRASES.items()
        ):
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    relationship = ExtractedRelationship(
                        relationship_type=relationship_type,
                        matched_phrase=phrase,
                        page_number=page_number,
                    )

                    if relationship not in result.relationships:
                        result.relationships.append(
                            relationship
                        )

    @staticmethod
    def _add_unique_identifier(
        collection: list[ExtractedIdentifier],
        identifier: ExtractedIdentifier,
    ) -> None:
        """Add an identifier if its value is not already present."""

        existing_values = {
            item.value
            for item in collection
        }

        if identifier.value not in existing_values:
            collection.append(
                identifier
            )


identifier_extractor = IdentifierExtractor()