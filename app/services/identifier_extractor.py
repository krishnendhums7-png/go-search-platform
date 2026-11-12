"""
Identifier and relationship extraction service.

This module performs deterministic extraction only.

It does not use an LLM.
"""

import re
from datetime import date

from rapidfuzz import fuzz

from app.models.identifier_extraction import (
    ExtractionConfidence,
    ExtractedIdentifier,
    ExtractedReference,
    ExtractedRelationship,
    IdentifierExtractionResult,
    RelationshipType,
)
from app.models.text_extraction import TextExtractionResult
from app.services.department_service import department_service


class IdentifierExtractor:
    """
    Extract identifiers and relationship signals from Government Orders.

    Extraction strategy:

    1. Regex-first extraction.
    2. OCR-tolerant normalization for matching.
    3. Department registry resolution.
    4. RapidFuzz fallback for department matching.
    5. Numbered Government Order reference extraction.
    6. Deterministic relationship signal detection.
    7. Explicit review flags for uncertain values.
    """

    # ------------------------------------------------------------------
    # Malayalam Government Order category mapping
    # ------------------------------------------------------------------

    MALAYALAM_CATEGORY_MAP = {
        "അച്ചടി": "P",
        "സാധാ": "Rt",
        "കൈ": "Ms",
        "കൈ?": "Ms",
    }

    # ------------------------------------------------------------------
    # English Government Order number
    # ------------------------------------------------------------------

    ENGLISH_GO_NUMBER_PATTERN = re.compile(
        r"""
        G\.?\s*O\.?
        \s*
        \(?
        (?P<category>P|Rt|Ms)
        \)?
        \s*
        (?:No\.?|N[o0]\.?)
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z][A-Za-z&.-]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Malayalam Government Order number
    # ------------------------------------------------------------------

    MALAYALAM_GO_NUMBER_PATTERN = re.compile(
        r"""
        സ
        \s*\.\s*
        ഉ
        \s*\.
        \s*
        \(?
        (?P<category>അച്ചടി|സാധാ|കൈ)\??
        \)?
        \s*
        നം
        \s*\.
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[^\s,;:]+)
        """,
        re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # OCR-tolerant Malayalam Government Order fallback
    # ------------------------------------------------------------------

    MALAYALAM_GO_NUMBER_FALLBACK_PATTERN = re.compile(
        r"""
        സ\.?\s*ഉ\.?
        \s*
        \(?
        (?P<category>അച്ചടി|സാധാ|കൈ)\??
        \)?
        \s*
        നം\.?
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[^\s,;:]+)
        """,
        re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Numeric dates
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Government Order header date
    #
    # Examples:
    #
    # Dated, Thiruvananthapuram, 8 th March, 2026
    # Dated, Thiruvananthapuram, 8th March, 2026
    # Dated 8 March 2026
    # Dated: 8 March 2026
    # ------------------------------------------------------------------

    GO_HEADER_DATE_PATTERN = re.compile(
        r"""
        \bdated\b
        [,\s:]*
        (?:[A-Za-z .'-]+,\s*)?
        (?P<day>\d{1,2})
        \s*(?:st|nd|rd|th)?
        \s+
        (?P<month>
            January|February|March|April|May|June|
            July|August|September|October|November|December
        )
        \s*,?\s*
        (?P<year>\d{4})
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Numeric Government Order header date.
    #
    # Examples:
    #
    # Dated,Thiruvananthapuram, 23-02-2026
    # Dated: 23/02/2026
    # Dated 23.02.2026
    # ------------------------------------------------------------------

    GO_HEADER_NUMERIC_DATE_PATTERN = re.compile(
        r"""
        \bdated\b
        [,\s:]*
        (?:[A-Za-z .'-]+,\s*)?
        (?P<day>\d{1,2})
        [./-]
        (?P<month>\d{1,2})
        [./-]
        (?P<year>\d{4})
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # Maximum distance between the main GO number and its header date.
    #
    # This prevents dates belonging to later referenced GOs from being
    # treated as the primary GO's issue date.
    GO_HEADER_SEARCH_WINDOW = 500

    # ------------------------------------------------------------------
    # English numbered Government Order references
    # ------------------------------------------------------------------

    ENGLISH_REFERENCE_PATTERN = re.compile(
        r"""
        (?P<ordinal>\d{1,2})
        (?:st|nd|rd|th)?
        \s*
        G\.?\s*O\.?
        \s*
        \(?
        (?P<category>P|Rt|Ms)
        \)?
        \s*
        (?:No\.?|N[o0]\.?)
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z][A-Za-z&.-]*)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Malayalam numbered Government Order references
    # ------------------------------------------------------------------

    MALAYALAM_REFERENCE_PATTERN = re.compile(
        r"""
        (?P<ordinal>\d{1,2})
        (?:st|nd|rd|th)?
        \s*
        സ\.?\s*ഉ\.?
        \s*
        \(?
        (?P<category>അച്ചടി|സാധാ|കൈ)\??
        \)?
        \s*
        നം\.?
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[^\s,;:]+)
        """,
        re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Ordinal pattern
    # ------------------------------------------------------------------

    ORDINAL_PATTERN = re.compile(
        r"""
        (?P<ordinal>\d{1,2})
        (?:st|nd|rd|th)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Legal relationship phrases
    # ------------------------------------------------------------------

    RELATIONSHIP_PHRASES = {
        RelationshipType.AMENDS: [
            # English
            "modified to the above extent",
            "hereby modified",
            "hereby amended",
            "amendment to",
            "amended by",
            "amends",
            "modifies",

            # Malayalam
            "ഭേദഗതി ചെയ്യുന്നു",
            "ഭേദഗതി ചെയ്തിരിക്കുന്നു",
            "ഭേദഗതി ചെയ്യുന്നതിന്",
            "ഭേദഗതി",
        ],
        RelationshipType.SUPERSEDES: [
            # English
            "in supersession of",
            "superseded by",
            "supersedes",

            # Malayalam
            "പകരം",
            "പൂർണ്ണമായി റദ്ദാക്കി",
            "പിൻവലിച്ച്",
        ],
        RelationshipType.CANCELS: [
            # English
            "stands cancelled",
            "cancelled",
            "canceled",
            "cancels",

            # Malayalam
            "റദ്ദാക്കുന്നു",
            "റദ്ദാക്കിയിരിക്കുന്നു",
            "റദ്ദാക്കി",
        ],
        RelationshipType.READ_AS: [
            # English
            "shall be read as",

            # Malayalam
            "വായിക്കേണ്ടതാണ്",
            "വായിക്കേണ്ടത്",
        ],
    }

    DEPARTMENT_THRESHOLD = 90

    # ==================================================================
    # Public extraction method
    # ==================================================================

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

            self._extract_references(
                page.text,
                page.page_number,
                result,
            )

        # ----------------------------------------------------------
        # Extract the issuing department from the first page header.
        # ----------------------------------------------------------

        if text_result.pages:
            self._extract_departments(
                text_result.pages[0].text,
                result,
            )

        # ----------------------------------------------------------
        # Identify the issue date associated with the primary GO.
        # ----------------------------------------------------------

        self._identify_primary_go_header_date(
            text_result=text_result,
            result=result,
        )

        # ----------------------------------------------------------
        # Extract relationships after all references are known.
        # ----------------------------------------------------------

        for page in text_result.pages:
            self._extract_relationships(
                page.text,
                page.page_number,
                result,
            )

        self._resolve_relationship_references(result)

        return result

    # ==================================================================
    # Government Order number extraction
    # ==================================================================

    def _extract_go_numbers(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """Extract English and Malayalam Government Order numbers."""

        # ----------------------------------------------------------
        # English GO numbers.
        # ----------------------------------------------------------

        for match in self.ENGLISH_GO_NUMBER_PATTERN.finditer(text):
            category = self._normalize_english_category(
                match.group("category")
            )

            number = match.group("number")
            year = match.group("year")

            department = self._clean_department(
                match.group("department")
            )

            normalized_value = self._format_go_number(
                category=category,
                number=number,
                year=year,
                department=department,
            )

            self._add_unique_identifier(
                collection=result.go_numbers,
                identifier=ExtractedIdentifier(
                    value=normalized_value,
                    confidence=ExtractionConfidence.HIGH,
                    extraction_method="REGEX",
                ),
            )

        # ----------------------------------------------------------
        # Malayalam GO numbers.
        # ----------------------------------------------------------

        malayalam_matches = list(
            self.MALAYALAM_GO_NUMBER_PATTERN.finditer(text)
        )

        if not malayalam_matches:
            malayalam_matches = list(
                self.MALAYALAM_GO_NUMBER_FALLBACK_PATTERN.finditer(
                    text
                )
            )

        for match in malayalam_matches:
            category = self._normalize_malayalam_category(
                match.group("category")
            )

            number = match.group("number")
            year = match.group("year")

            department = self._clean_department(
                match.group("department")
            )

            normalized_value = self._format_go_number(
                category=category,
                number=number,
                year=year,
                department=department,
            )

            self._add_unique_identifier(
                collection=result.go_numbers,
                identifier=ExtractedIdentifier(
                    value=normalized_value,
                    confidence=ExtractionConfidence.HIGH,
                    extraction_method="REGEX_MALAYALAM",
                ),
            )

    # ==================================================================
    # Date extraction
    # ==================================================================

    def _extract_dates(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Extract Government Order header dates.

        Only dates explicitly associated with a ``Dated`` header are
        considered issue-date candidates.

        Generic numeric dates appearing elsewhere in the document
        are not added to ``issue_dates`` because they may belong to
        referenced GOs, letters, financial years, or other content.
        """

        # ----------------------------------------------------------
        # Government Order header dates with textual months.
        # ----------------------------------------------------------

        for match in self.GO_HEADER_DATE_PATTERN.finditer(text):
            day = int(match.group("day"))
            month = match.group("month")
            year = int(match.group("year"))

            value = (
                f"{day:02d} "
                f"{month} "
                f"{year}"
            )

            self._add_unique_identifier(
                collection=result.issue_dates,
                identifier=ExtractedIdentifier(
                    value=value,
                    confidence=ExtractionConfidence.HIGH,
                    extraction_method="GO_HEADER",
                ),
            )

        # ----------------------------------------------------------
        # Government Order header dates with numeric months.
        # ----------------------------------------------------------

        for match in self.GO_HEADER_NUMERIC_DATE_PATTERN.finditer(
            text
        ):
            day = int(match.group("day"))
            month = int(match.group("month"))
            year = int(match.group("year"))

            if not self._is_valid_date_parts(
                day=day,
                month=month,
                year=year,
            ):
                continue

            matched_date = match.group(0)

            separator_match = re.search(
                r"\d{1,2}([./-])\d{1,2}([./-])\d{4}",
                matched_date,
            )

            if separator_match is not None:
                first_separator = separator_match.group(1)
                second_separator = separator_match.group(2)
            else:
                first_separator = "-"
                second_separator = "-"

            value = (
                f"{day:02d}"
                f"{first_separator}"
                f"{month:02d}"
                f"{second_separator}"
                f"{year}"
            )

            self._add_unique_identifier(
                collection=result.issue_dates,
                identifier=ExtractedIdentifier(
                    value=value,
                    confidence=ExtractionConfidence.HIGH,
                    extraction_method="GO_HEADER",
                ),
            )

    # ==================================================================
    # Primary GO header date
    # ==================================================================

    def _identify_primary_go_header_date(
        self,
        text_result: TextExtractionResult,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Identify the issue date belonging to the primary Government Order.

        The primary Government Order is the first GO number detected
        in document order.

        Only a bounded region after that GO number is inspected.
        This prevents dates belonging to referenced Government Orders
        from being selected as the primary GO's issue date.

        Both textual and numeric header-date formats are supported.

        No date is guessed when the primary header cannot be resolved.
        """

        for page in text_result.pages:
            # ------------------------------------------------------
            # Find the first English GO number on this page.
            # ------------------------------------------------------

            english_match = (
                self.ENGLISH_GO_NUMBER_PATTERN.search(
                    page.text
                )
            )

            # ------------------------------------------------------
            # Find the first Malayalam GO number on this page.
            # ------------------------------------------------------

            malayalam_match = (
                self.MALAYALAM_GO_NUMBER_PATTERN.search(
                    page.text
                )
            )

            if malayalam_match is None:
                malayalam_match = (
                    self.MALAYALAM_GO_NUMBER_FALLBACK_PATTERN.search(
                        page.text
                    )
                )

            # ------------------------------------------------------
            # Select whichever GO number occurs first.
            # ------------------------------------------------------

            candidates = [
                match
                for match in (
                    english_match,
                    malayalam_match,
                )
                if match is not None
            ]

            if not candidates:
                continue

            go_match = min(
                candidates,
                key=lambda match: match.start(),
            )

            # ------------------------------------------------------
            # Search only near the GO header.
            # ------------------------------------------------------

            header_end = min(
                len(page.text),
                go_match.end()
                + self.GO_HEADER_SEARCH_WINDOW,
            )

            header_text = page.text[
                go_match.end():header_end
            ]

            # ------------------------------------------------------
            # First try the textual-month header format.
            # ------------------------------------------------------

            date_match = (
                self.GO_HEADER_DATE_PATTERN.search(
                    header_text
                )
            )

            if date_match is not None:
                day = int(
                    date_match.group("day")
                )

                month = date_match.group("month")

                year = int(
                    date_match.group("year")
                )

                primary_value = (
                    f"{day:02d} "
                    f"{month} "
                    f"{year}"
                )

            else:
                # --------------------------------------------------
                # Then try the numeric header format.
                # --------------------------------------------------

                numeric_date_match = (
                    self.GO_HEADER_NUMERIC_DATE_PATTERN.search(
                        header_text
                    )
                )

                if numeric_date_match is None:
                    continue

                day = int(
                    numeric_date_match.group("day")
                )

                month = int(
                    numeric_date_match.group("month")
                )

                year = int(
                    numeric_date_match.group("year")
                )

                if not self._is_valid_date_parts(
                    day=day,
                    month=month,
                    year=year,
                ):
                    continue

                matched_date = numeric_date_match.group(0)

                separator_match = re.search(
                    r"\d{1,2}([./-])\d{1,2}([./-])\d{4}",
                    matched_date,
                )

                if separator_match is not None:
                    first_separator = separator_match.group(1)
                    second_separator = separator_match.group(2)
                else:
                    first_separator = "-"
                    second_separator = "-"

                primary_value = (
                    f"{day:02d}"
                    f"{first_separator}"
                    f"{month:02d}"
                    f"{second_separator}"
                    f"{year}"
                )

            # ------------------------------------------------------
            # Keep ONLY the primary issue date.
            # ------------------------------------------------------

            normalized_primary = (
                self._normalize_date_value(
                    primary_value
                )
            )

            matching_dates = [
                identifier
                for identifier in result.issue_dates
                if self._normalize_date_value(
                    identifier.value
                ) == normalized_primary
            ]

            result.issue_dates = matching_dates

            if result.issue_dates:
                result.issue_dates[0].confidence = (
                    ExtractionConfidence.HIGH
                )

                result.issue_dates[0].extraction_method = (
                    "GO_HEADER_PRIMARY"
                )

            else:
                result.issue_dates.append(
                    ExtractedIdentifier(
                        value=primary_value,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method="GO_HEADER_PRIMARY",
                    )
                )

            return

    # ==================================================================
    # Department extraction
    # ==================================================================

    def _extract_departments(
        self,
        text: str,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Extract the issuing department.

        Detection priority:

        1. Department code from the primary GO number.
        2. Known department names or aliases from the first-page header.
        3. Conservative fuzzy matching against the department registry.
        4. Preserve unknown department codes rather than guessing.

        Department definitions are maintained outside this extractor
        in ``data/config/departments.json``.
        """

        normalized_text = " ".join(text.split())

        if not normalized_text:
            return

        # ----------------------------------------------------------
        # 1. Try the primary English GO number.
        # ----------------------------------------------------------

        english_match = (
            self.ENGLISH_GO_NUMBER_PATTERN.search(
                normalized_text
            )
        )

        if english_match is not None:
            department_code = self._clean_department(
                english_match.group("department")
            )

            if department_code:
                canonical_department = (
                    department_service.resolve(
                        department_code
                    )
                )

                if canonical_department is not None:
                    department_value = canonical_department
                    extraction_method = (
                        "GO_NUMBER_RESOLVED"
                    )
                else:
                    # Do not guess unknown department codes.
                    department_value = department_code
                    extraction_method = (
                        "GO_NUMBER_UNKNOWN"
                    )

                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=department_value,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method=extraction_method,
                    ),
                )

                return

        # ----------------------------------------------------------
        # 2. Try the Malayalam GO number.
        # ----------------------------------------------------------

        malayalam_match = (
            self.MALAYALAM_GO_NUMBER_PATTERN.search(
                normalized_text
            )
        )

        if malayalam_match is None:
            malayalam_match = (
                self.MALAYALAM_GO_NUMBER_FALLBACK_PATTERN.search(
                    normalized_text
                )
            )

        if malayalam_match is not None:
            department_code = self._clean_department(
                malayalam_match.group("department")
            )

            if department_code:
                canonical_department = (
                    department_service.resolve(
                        department_code
                    )
                )

                if canonical_department is not None:
                    department_value = canonical_department
                    extraction_method = (
                        "GO_NUMBER_MALAYALAM_RESOLVED"
                    )
                else:
                    department_value = department_code
                    extraction_method = (
                        "GO_NUMBER_MALAYALAM_UNKNOWN"
                    )

                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=department_value,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method=extraction_method,
                    ),
                )

                return

        # ----------------------------------------------------------
        # 3. Search the first-page header using the registry.
        # ----------------------------------------------------------

        header_text = normalized_text[:1500]
        header_lower = header_text.lower()

        for department in department_service.departments:
            canonical_name = department["name"]

            candidates = [
                canonical_name,
                *department.get("aliases", []),
            ]

            for candidate in candidates:
                candidate_normalized = (
                    " ".join(candidate.split()).lower()
                )

                if candidate_normalized not in header_lower:
                    continue

                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=canonical_name,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method=(
                            "HEADER_REGISTRY"
                        ),
                    ),
                )

                return

        # ----------------------------------------------------------
        # 4. OCR-tolerant Electronics and IT detection.
        # ----------------------------------------------------------

        itd_pattern = re.compile(
            r"""
            electronics
            \s*(?:&|and)\s*
            information
            \s+technology
            \s*(?:\(c\))?
            \s*department
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        if itd_pattern.search(header_text):
            department = department_service.resolve(
                "ITD"
            )

            if department is not None:
                self._add_unique_identifier(
                    collection=result.departments,
                    identifier=ExtractedIdentifier(
                        value=department,
                        confidence=ExtractionConfidence.HIGH,
                        extraction_method="HEADER_ITD",
                    ),
                )

                return

        # ----------------------------------------------------------
        # 5. Conservative fuzzy matching.
        # ----------------------------------------------------------

        words = normalized_text.split()

        if len(words) < 2:
            return

        best_department: str | None = None
        best_score = 0.0
        best_matched_value = ""

        for department in department_service.departments:
            canonical_name = department["name"]

            candidates = [
                canonical_name,
                *department.get("aliases", []),
            ]

            for candidate in candidates:
                candidate_words = candidate.split()
                word_count = len(candidate_words)

                if len(words) < word_count:
                    continue

                for index in range(
                    len(words) - word_count + 1
                ):
                    window = " ".join(
                        words[
                            index:index + word_count
                        ]
                    )

                    score = fuzz.ratio(
                        candidate.lower(),
                        window.lower(),
                    )

                    if score > best_score:
                        best_score = score
                        best_department = canonical_name
                        best_matched_value = window

        if (
            best_department is None
            or best_score < self.DEPARTMENT_THRESHOLD
        ):
            return

        self._add_unique_identifier(
            collection=result.departments,
            identifier=ExtractedIdentifier(
                value=best_department,
                confidence=ExtractionConfidence.MEDIUM,
                extraction_method="FUZZY_REGISTRY",
            ),
        )

        result.review_flags.append(
            "Department matched using conservative "
            f"fuzzy matching: {best_matched_value} -> "
            f"{best_department} "
            f"(score={best_score:.1f})"
        )

    # ==================================================================
    # Reference extraction
    # ==================================================================

    def _extract_references(
        self,
        text: str,
        page_number: int,
        result: IdentifierExtractionResult,
    ) -> None:
        """
        Extract numbered Government Order references.

        Supports both English and Malayalam GO notation.
        """

        # ----------------------------------------------------------
        # English references.
        # ----------------------------------------------------------

        for match in self.ENGLISH_REFERENCE_PATTERN.finditer(text):
            self._add_reference(
                match=match,
                page_number=page_number,
                result=result,
                category=self._normalize_english_category(
                    match.group("category")
                ),
            )

        # ----------------------------------------------------------
        # Malayalam references.
        # ----------------------------------------------------------

        for match in self.MALAYALAM_REFERENCE_PATTERN.finditer(text):
            self._add_reference(
                match=match,
                page_number=page_number,
                result=result,
                category=self._normalize_malayalam_category(
                    match.group("category")
                ),
            )

    @staticmethod
    def _add_reference(
        match: re.Match[str],
        page_number: int,
        result: IdentifierExtractionResult,
        category: str,
    ) -> None:
        """Convert a regex match into an extracted reference."""

        ordinal = int(
            match.group("ordinal")
        )

        number = match.group("number")
        year = match.group("year")

        department = IdentifierExtractor._clean_department(
            match.group("department")
        )

        go_number = IdentifierExtractor._format_go_number(
            category=category,
            number=number,
            year=year,
            department=department,
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

    # ==================================================================
    # Relationship extraction
    # ==================================================================

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
        # Consolidate overlapping relationship phrases.
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

    # ==================================================================
    # Relationship ordinal extraction
    # ==================================================================

    @staticmethod
    def _extract_context_ordinals(
        text: str,
        phrase: str,
    ) -> list[int]:
        """
        Extract ordinal references from the legal context
        preceding a relationship phrase.
        """

        phrase_pattern = re.compile(
            re.escape(phrase),
            re.IGNORECASE,
        )

        match = phrase_pattern.search(text)

        if match is None:
            return []

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

    # ==================================================================
    # Relationship reference validation
    # ==================================================================

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

    # ==================================================================
    # Date validation helpers
    # ==================================================================

    @staticmethod
    def _is_valid_date_parts(
        day: int,
        month: int,
        year: int,
    ) -> bool:
        """Validate numeric date components."""

        if not 1900 <= year <= 2100:
            return False

        if not 1 <= month <= 12:
            return False

        if not 1 <= day <= 31:
            return False

        try:
            date(
                year=year,
                month=month,
                day=day,
            )
        except ValueError:
            return False

        return True

    @classmethod
    def _is_valid_generic_date(
        cls,
        value: str,
    ) -> bool:
        """
        Validate a generic numeric date extracted from OCR text.

        Supports:

            DD-MM-YYYY
            DD/MM/YYYY
            DD.MM.YYYY
            YYYY-MM-DD
            YYYY/MM/DD
            YYYY.MM.DD
        """

        parts = re.split(
            r"[./-]",
            value,
        )

        if len(parts) != 3:
            return False

        try:
            first, second, third = (
                int(part)
                for part in parts
            )
        except ValueError:
            return False

        if len(parts[0]) == 4:
            year = first
            month = second
            day = third
        else:
            day = first
            month = second
            year = third

        return cls._is_valid_date_parts(
            day=day,
            month=month,
            year=year,
        )

    # ==================================================================
    # Normalization helpers
    # ==================================================================

    @staticmethod
    def _normalize_english_category(
        category: str,
    ) -> str:
        """Normalize an English Government Order category."""

        cleaned = category.strip().lower()

        if cleaned == "p":
            return "P"

        if cleaned == "rt":
            return "Rt"

        if cleaned == "ms":
            return "Ms"

        return category.strip()

    @classmethod
    def _normalize_malayalam_category(
        cls,
        category: str,
    ) -> str:
        """Normalize a Malayalam Government Order category."""

        cleaned = category.strip()

        return cls.MALAYALAM_CATEGORY_MAP.get(
            cleaned,
            cleaned,
        )

    @staticmethod
    def _clean_department(
        department: str,
    ) -> str:
        """Normalize OCR whitespace and punctuation."""

        return department.strip(
            " .,:;()[]{}?"
        )

    @staticmethod
    def _format_go_number(
        category: str,
        number: str,
        year: str,
        department: str,
    ) -> str:
        """Create the canonical Government Order number."""

        return (
            f"G.O.({category}) "
            f"No. {number}/{year}/{department}"
        )

    @staticmethod
    def _normalize_date_value(
        value: str,
    ) -> str:
        """Normalize date separators for comparison."""

        return value.replace(
            "/",
            "-",
        ).replace(
            ".",
            "-",
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