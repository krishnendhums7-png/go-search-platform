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
    ExtractedIdentifier,
    ExtractedReference,
    ExtractedRelationship,
    IdentifierExtractionResult,
    RelationshipType,
)
from app.models.text_extraction import TextExtractionResult


class IdentifierExtractor:
    """
    Extract identifiers and relationship signals from Government Orders.

    Extraction strategy:

    1. Regex-first extraction.
    2. OCR-tolerant normalization for matching.
    3. RapidFuzz fallback for department matching.
    4. Numbered Government Order reference extraction.
    5. Deterministic relationship signal detection.
    6. Explicit review flags for uncertain values.
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
        (?:No\.?|N[o0]\.? )
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

    REFERENCE_PATTERN = re.compile(
        r"""
        (?P<ordinal>\d{1,2})
        (?:st|nd|rd|th)?
        \s*
        G\.?\s*O\.?
        \s*
        \(?
        (?P<category>P|Rt)
        \)?
        \s*
        (?:No\.?|N[o0]\.? )
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    ORDINAL_PATTERN = re.compile(
        r"""
        (?P<ordinal>\d{1,2})
        (?:st|nd|rd|th)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    RELATIONSHIP_PHRASES = {
        RelationshipType.AMENDS: [
            "modified to the above extent",
            "hereby modified",
            "hereby amended",
            "amendment to",
            "amended by",
            "amends",
            "modifies",
            "ഭേദഗതി ചെയ്യുന്നു",
            "ഭേദഗതി",
        ],
        RelationshipType.SUPERSEDES: [
            "in supersession of",
            "superseded by",
            "supersedes",
            "മാറ്റിസ്ഥാപിക്കുന്നു",
        ],
        RelationshipType.CANCELS: [
            "stands cancelled",
            "cancelled",
            "canceled",
            "cancels",
            "റദ്ദാക്കുന്നു",
            "റദ്ദാക്കി",
        ],
        RelationshipType.READ_AS: [
            "shall be read as",
            "വായിക്കേണ്ടത്",
        ],
    }

    DEPARTMENT_THRESHOLD = 90

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

        # ----------------------------------------------------------
        # Extract page-level identifiers.
        # ----------------------------------------------------------

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

            self._extract_references(
                page.text,
                page.page_number,
                result,
            )

        # ----------------------------------------------------------
        # Extract relationships after all references are known.
        #
        # This allows a relationship on page 4 to refer to a GO
        # reference that was introduced on page 1.
        # ----------------------------------------------------------

        for page in text_result.pages:
            self._extract_relationships(
                page.text,
                page.page_number,
                result,
            )

        self._resolve_relationship_references(result)

        return result

    def _extract_go_numbers(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """Extract Government Order numbers using regex."""

        for match in self.GO_NUMBER_PATTERN.finditer(text):
            category = match.group("category")
            number = match.group("number")
            year = match.group("year")
            department = match.group("department")

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
        """
        Match issuing departments using exact and conservative
        fuzzy matching.

        Fuzzy matching is performed only against phrases having
        the same number of words as the known department name.
        """

        normalized_text = " ".join(text.split())

        if not normalized_text:
            return

        text_lower = normalized_text.lower()

        # ----------------------------------------------------------
        # Exact matching.
        # ----------------------------------------------------------

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

        if len(words) < 2:
            return

        # ----------------------------------------------------------
        # Conservative fuzzy matching.
        # ----------------------------------------------------------

        for department in self.DEPARTMENTS:
            department_words = department.split()
            word_count = len(department_words)

            if department.lower() in text_lower:
                continue

            if len(words) < word_count:
                continue

            windows: list[str] = []

            for index in range(
                len(words) - word_count + 1
            ):
                window = " ".join(
                    words[
                        index:index + word_count
                    ]
                )

                windows.append(window)

            if not windows:
                continue

            match = process.extractOne(
                department,
                windows,
                scorer=fuzz.ratio,
            )

            if match is None:
                continue

            matched_value, score, _ = match

            if score < self.DEPARTMENT_THRESHOLD:
                continue

            self._add_unique_identifier(
                collection=result.departments,
                identifier=ExtractedIdentifier(
                    value=department,
                    confidence=ExtractionConfidence.MEDIUM,
                    extraction_method="FUZZY",
                ),
            )

            result.review_flags.append(
                "Department matched using conservative "
                f"fuzzy matching: {matched_value} -> "
                f"{department} "
                f"(score={score:.1f})"
            )

    def _extract_references(
        self,
        text: str,
        page_number: int,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Extract numbered Government Order references.

        Example:

            1 G.O.(Rt) No. 114/2025/ITD

        becomes:

            ordinal = 1
            go_number = G.O.(Rt) No. 114/2025/ITD
        """

        for match in self.REFERENCE_PATTERN.finditer(text):
            ordinal = int(
                match.group("ordinal")
            )

            category = match.group("category")
            number = match.group("number")
            year = match.group("year")
            department = match.group("department")

            go_number = (
                f"G.O.({category}) "
                f"No. {number}/{year}/{department}"
            )

            reference = ExtractedReference(
                ordinal=ordinal,
                go_number=go_number,
                page_number=page_number,
            )

            if reference not in result.references:
                result.references.append(
                    reference
                )

    def _extract_relationships(
        self,
        text: str,
        page_number: int,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Extract explicit legal relationship signals.

        Multiple overlapping phrases describing the same legal
        action are consolidated into one relationship.

        For example:

            hereby modified
            modified to the above extent

        represent one AMENDS relationship.
        """

        text_lower = text.lower()

        detected: list[
            tuple[
                RelationshipType,
                str,
                list[int],
            ]
        ] = []

        for relationship_type, phrases in (
            self.RELATIONSHIP_PHRASES.items()
        ):
            for phrase in phrases:
                phrase_lower = phrase.lower()

                if phrase_lower not in text_lower:
                    continue

                # READ_AS is handled separately.
                if relationship_type == RelationshipType.READ_AS:
                    continue

                reference_ordinals = (
                    self._extract_context_ordinals(
                        text,
                        phrase,
                    )
                )

                detected.append(
                    (
                        relationship_type,
                        phrase,
                        reference_ordinals,
                    )
                )

        # ----------------------------------------------------------
        # Consolidate overlapping AMENDS phrases.
        #
        # The longest matching phrase is retained because it
        # contains more specific legal context.
        # ----------------------------------------------------------

        for relationship_type in (
            RelationshipType.AMENDS,
            RelationshipType.SUPERSEDES,
            RelationshipType.CANCELS,
        ):
            candidates = [
                item
                for item in detected
                if item[0] == relationship_type
            ]

            if not candidates:
                continue

            candidates.sort(
                key=lambda item: len(item[1]),
                reverse=True,
            )

            selected_type, selected_phrase, ordinals = (
                candidates[0]
            )

            all_ordinals = set(ordinals)

            for _, _, candidate_ordinals in candidates[1:]:
                all_ordinals.update(
                    candidate_ordinals
                )

            relationship = ExtractedRelationship(
                relationship_type=selected_type,
                matched_phrase=selected_phrase,
                page_number=page_number,
                reference_ordinals=sorted(
                    all_ordinals
                ),
            )

            if not any(
                existing.relationship_type
                == relationship.relationship_type
                and existing.page_number
                == relationship.page_number
                for existing in result.relationships
            ):
                result.relationships.append(
                    relationship
                )

        # ----------------------------------------------------------
        # READ-AS provision.
        # ----------------------------------------------------------

        provision_pattern = re.compile(
            r"""
            (?:
                clause
                |
                paragraph
                |
                para
                |
                provision
                |
                the\s+following
            )
            .*?
            shall\s+be\s+read\s+as
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        if provision_pattern.search(text):
            relationship = ExtractedRelationship(
                relationship_type=RelationshipType.READ_AS,
                matched_phrase="shall be read as",
                page_number=page_number,
                reference_ordinals=[],
            )

            if not any(
                existing.relationship_type
                == RelationshipType.READ_AS
                and existing.page_number
                == page_number
                for existing in result.relationships
            ):
                result.relationships.append(
                    relationship
                )

    @staticmethod
    def _extract_context_ordinals(
        text: str,
        phrase: str,
    ) -> list[int]:
        """
        Extract ordinal references from the legal context
        preceding a relationship phrase.

        Example:

            1st, 2nd and 4th papers above are hereby modified

        returns:

            [1, 2, 4]
        """

        phrase_pattern = re.compile(
            re.escape(phrase),
            re.IGNORECASE,
        )

        match = phrase_pattern.search(text)

        if match is None:
            return []

        # Examine the local legal context.
        context_start = max(
            0,
            match.start() - 300,
        )

        context = text[
            context_start:match.end()
        ]

        ordinal_matches = (
            IdentifierExtractor.ORDINAL_PATTERN.findall(
                context
            )
        )

        return [
            int(ordinal)
            for ordinal in ordinal_matches
        ]

    @staticmethod
    def _resolve_relationship_references(
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Validate relationship ordinal references against the
        Government Order reference list.

        The resolver never guesses a target Government Order.
        """

        if not result.references:
            return

        valid_ordinals = {
            reference.ordinal
            for reference in result.references
        }

        for relationship in result.relationships:
            relationship.reference_ordinals = [
                ordinal
                for ordinal in relationship.reference_ordinals
                if ordinal in valid_ordinals
            ]

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
            collection.append(identifier)


identifier_extractor = IdentifierExtractor()