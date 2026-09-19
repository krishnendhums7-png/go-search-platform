"""
Persist extracted Government Order metadata into PostgreSQL.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.identifier_extraction import (
    IdentifierExtractionResult,
)
from app.services.metadata_service import MetadataService
from app.services.relationship_ingestion_service import (
    RelationshipIngestionService,
)


class MetadataIngestionService:
    """Convert identifier extraction results into relational records."""

    def __init__(self, session: Session) -> None:
        """Initialize the metadata ingestion service."""

        self._metadata_service = MetadataService(
            session
        )

        self._relationship_service = (
            RelationshipIngestionService(session)
        )

    def store_extraction_result(
        self,
        result: IdentifierExtractionResult,
    ) -> list[UUID]:
        """
        Store Government Order metadata and relationships.

        Existing Government Orders are updated when a new
        high-confidence primary GO header date is available.

        Known legacy GO identifiers are reconciled with their
        current canonical identifiers before creating a new
        record.
        """

        document_id = UUID(
            str(result.document_id)
        )

        issue_date = self._extract_unambiguous_date(
            result
        )

        department = self._extract_unambiguous_department(
            result
        )

        government_order_ids: list[UUID] = []

        # ----------------------------------------------------------
        # Create or update Government Order records.
        # ----------------------------------------------------------

        for identifier in result.go_numbers:
            go_number = identifier.value

            existing = (
                self._metadata_service.find_by_go_number(
                    go_number
                )
            )

            # ------------------------------------------------------
            # Reconcile known legacy identifiers.
            # ------------------------------------------------------

            if existing is None:
                legacy_number = (
                    self._legacy_go_number_alias(
                        go_number
                    )
                )

                if legacy_number is not None:
                    existing = (
                        self._metadata_service.find_by_go_number(
                            legacy_number
                        )
                    )

                    if existing is not None:
                        # Replace the old identifier with the
                        # current canonical identifier.
                        existing.go_number = go_number

                        # Associate the record with the current
                        # source document.
                        existing.document_id = document_id

                        if issue_date is not None:
                            self._metadata_service.update_issue_date(
                                existing.id,
                                issue_date,
                            )

                        if (
                            department is not None
                            and existing.department != department
                        ):
                            existing.department = department

            # ------------------------------------------------------
            # Existing canonical record.
            # ------------------------------------------------------

            if existing is not None:
                if (
                    issue_date is not None
                    and existing.issue_date != issue_date
                ):
                    self._metadata_service.update_issue_date(
                        existing.id,
                        issue_date,
                    )

                if (
                    department is not None
                    and existing.department is None
                ):
                    existing.department = department

                government_order_ids.append(
                    existing.id
                )

                continue

            # ------------------------------------------------------
            # Create a new Government Order record.
            # ------------------------------------------------------

            government_order = (
                self._metadata_service.create_government_order(
                    document_id=document_id,
                    go_number=go_number,
                    issue_date=issue_date,
                    department=department,
                )
            )

            government_order_ids.append(
                government_order.id
            )

        # ----------------------------------------------------------
        # Resolve Government Order IDs by number.
        # ----------------------------------------------------------

        go_id_by_number: dict[str, UUID] = {}

        for identifier in result.go_numbers:
            government_order = (
                self._metadata_service.find_by_go_number(
                    identifier.value
                )
            )

            if government_order is not None:
                go_id_by_number[
                    identifier.value
                ] = government_order.id

        # ----------------------------------------------------------
        # Resolve source Government Order.
        # ----------------------------------------------------------

        source_go_id = (
            self._resolve_source_go_id(
                result=result,
                go_id_by_number=go_id_by_number,
            )
        )

        # ----------------------------------------------------------
        # Store relationships.
        # ----------------------------------------------------------

        if source_go_id is not None:
            for relationship in result.relationships:
                self._relationship_service.store_relationship(
                    source_go_id=source_go_id,
                    relationship=relationship,
                    references=result.references,
                    go_id_by_number=go_id_by_number,
                )

        # ----------------------------------------------------------
        # Commit all metadata and relationships.
        # ----------------------------------------------------------

        self._metadata_service.commit()

        return government_order_ids

    @staticmethod
    def _legacy_go_number_alias(
        go_number: str,
    ) -> str | None:
        """
        Return a known legacy Government Order number alias.

        This handles metadata created before the department
        suffix was extracted correctly.
        """

        aliases = {
            "G.O.(P) No. 4/2026/P&ARD":
                "G.O.(P) No. 4/2026/P",
        }

        return aliases.get(go_number)

    @staticmethod
    def _resolve_source_go_id(
        result: IdentifierExtractionResult,
        go_id_by_number: dict[str, UUID],
    ) -> UUID | None:
        """
        Resolve the source Government Order deterministically.

        The source GO is the GO number that is not one of the
        numbered references.

        No source is inferred when multiple candidates remain.
        """

        referenced_go_numbers = {
            reference.go_number
            for reference in result.references
        }

        source_candidates = [
            identifier.value
            for identifier in result.go_numbers
            if identifier.value
            not in referenced_go_numbers
        ]

        if len(source_candidates) != 1:
            return None

        return go_id_by_number.get(
            source_candidates[0]
        )

    @staticmethod
    def _extract_unambiguous_date(
        result: IdentifierExtractionResult,
    ) -> date | None:
        """
        Extract the Government Order issue date.

        Priority:

        1. GO_HEADER_PRIMARY
        2. Exactly one GO_HEADER
        3. Exactly one generic date

        The primary header date is associated with the first
        Government Order header in the document.
        """

        # ----------------------------------------------------------
        # Priority 1:
        # Primary Government Order header date.
        # ----------------------------------------------------------

        primary_dates = [
            identifier.value
            for identifier in result.issue_dates
            if identifier.extraction_method
            == "GO_HEADER_PRIMARY"
        ]

        if len(primary_dates) == 1:
            return MetadataIngestionService._parse_date(
                primary_dates[0]
            )

        # ----------------------------------------------------------
        # Priority 2:
        # Exactly one GO header date.
        # ----------------------------------------------------------

        header_dates = [
            identifier.value
            for identifier in result.issue_dates
            if identifier.extraction_method
            == "GO_HEADER"
        ]

        if len(header_dates) == 1:
            return MetadataIngestionService._parse_date(
                header_dates[0]
            )

        # ----------------------------------------------------------
        # Priority 3:
        # Existing deterministic fallback.
        # ----------------------------------------------------------

        if len(result.issue_dates) != 1:
            return None

        value = result.issue_dates[0].value

        return MetadataIngestionService._parse_date(
            value
        )

    @staticmethod
    def _extract_unambiguous_department(
        result: IdentifierExtractionResult,
    ) -> str | None:
        """Extract a department only when exactly one is detected."""

        departments = {
            identifier.value.strip()
            for identifier in result.departments
            if identifier.value.strip()
        }

        if len(departments) != 1:
            return None

        return departments.pop()

    @staticmethod
    def _parse_date(
        value: str,
    ) -> date | None:
        """
        Parse common Government Order date formats.

        Supported formats include numeric dates and English
        month-name dates.
        """

        cleaned = value.strip()

        formats = (
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d %B %Y",
            "%d %b %Y",
        )

        for date_format in formats:
            try:
                return datetime.strptime(
                    cleaned,
                    date_format,
                ).date()
            except ValueError:
                continue

        return None