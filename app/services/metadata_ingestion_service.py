"""Persist extracted Government Order metadata into PostgreSQL."""

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
        self._metadata_service = MetadataService(session)
        self._relationship_service = (
            RelationshipIngestionService(session)
        )

    def store_extraction_result(
        self,
        result: IdentifierExtractionResult,
    ) -> list[UUID]:
        """Store Government Order metadata and relationships.

        Metadata and relationships are persisted only when their
        identifiers can be resolved deterministically.
        """

        document_id = UUID(
            str(result.document_id)
        )

        issue_date = self._extract_unambiguous_date(
            result
        )

        department = (
            self._extract_unambiguous_department(
                result
            )
        )

        government_order_ids: list[UUID] = []

        # -----------------------------------------------------
        # Store Government Orders
        # -----------------------------------------------------

        for identifier in result.go_numbers:
            existing = (
                self._metadata_service.find_by_go_number(
                    identifier.value
                )
            )

            if existing is not None:
                government_order_ids.append(
                    existing.id
                )
                continue

            government_order = (
                self._metadata_service.create_government_order(
                    document_id=document_id,
                    go_number=identifier.value,
                    issue_date=issue_date,
                    department=department,
                )
            )

            government_order_ids.append(
                government_order.id
            )

        # -----------------------------------------------------
        # Build GO number → database ID mapping
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Resolve source Government Order
        # -----------------------------------------------------

        source_go_id = self._resolve_source_go_id(
            result=result,
            go_id_by_number=go_id_by_number,
        )

        # -----------------------------------------------------
        # Persist relationships
        # -----------------------------------------------------

        if source_go_id is not None:
            for relationship in result.relationships:
                self._relationship_service.store_relationship(
                    source_go_id=source_go_id,
                    relationship=relationship,
                    references=result.references,
                    go_id_by_number=go_id_by_number,
                )

        # -----------------------------------------------------
        # Commit everything
        # -----------------------------------------------------

        self._metadata_service.commit()

        return government_order_ids

    @staticmethod
    def _resolve_source_go_id(
        result: IdentifierExtractionResult,
        go_id_by_number: dict[str, UUID],
    ) -> UUID | None:
        """Resolve the source GO deterministically.

        The source GO is considered the first GO number appearing
        in the document when it is not one of the numbered
        references.

        A source is not inferred when every extracted GO is a
        numbered reference.
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
        """Extract a date only when exactly one date was detected."""

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
        """Extract a department only when exactly one was detected."""

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
        """Parse common Government Order date formats."""

        cleaned = value.strip()

        formats = (
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%y",
            "%d/%m/%y",
            "%d-%m-%y",
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