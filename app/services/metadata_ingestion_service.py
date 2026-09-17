"""Persist extracted Government Order metadata into PostgreSQL."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.identifier_extraction import IdentifierExtractionResult
from app.services.metadata_service import MetadataService


class MetadataIngestionService:
    """Convert identifier extraction results into relational records."""

    def __init__(self, session: Session) -> None:
        """Initialize the metadata ingestion service.

        Args:
            session: PostgreSQL SQLAlchemy session.
        """
        self._metadata_service = MetadataService(session)

    def store_extraction_result(
        self,
        result: IdentifierExtractionResult,
    ) -> list[UUID]:
        """Store Government Order identifiers from an extraction result.

        Args:
            result: Module 5 identifier extraction result.

        Returns:
            UUIDs of created Government Order records.
        """
        document_id = UUID(str(result.document_id))

        government_orders: list[UUID] = []

        for identifier in result.go_numbers:
            existing = self._metadata_service.find_by_go_number(
                identifier.value,
            )

            if existing is not None:
                government_orders.append(existing.id)
                continue

            government_order = (
                self._metadata_service.create_government_order(
                    document_id=document_id,
                    go_number=identifier.value,
                )
            )

            government_orders.append(government_order.id)

        self._metadata_service.commit()

        return government_orders