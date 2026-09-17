"""Service for Government Order metadata and relationship storage."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identifier_extraction import ExtractedRelationship
from app.storage.relational.models import (
    GORelationshipModel,
    GovernmentOrderModel,
)


class MetadataService:
    """Store and retrieve Government Order relational metadata."""

    def __init__(self, session: Session) -> None:
        """Initialize the metadata service.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create_government_order(
        self,
        document_id: UUID,
        go_number: str,
        issue_date: date | None = None,
        department: str | None = None,
    ) -> GovernmentOrderModel:
        """Create a Government Order metadata record.

        Args:
            document_id: Source document UUID.
            go_number: Government Order number.
            issue_date: Government Order issue date.
            department: Issuing department.

        Returns:
            Created GovernmentOrderModel.
        """
        government_order = GovernmentOrderModel(
            document_id=document_id,
            go_number=go_number,
            issue_date=issue_date,
            department=department,
        )

        self._session.add(government_order)
        self._session.flush()

        return government_order

    def find_by_go_number(
        self,
        go_number: str,
    ) -> GovernmentOrderModel | None:
        """Find a Government Order by its number.

        Args:
            go_number: Government Order number.

        Returns:
            Matching GovernmentOrderModel or None.
        """
        statement = select(GovernmentOrderModel).where(
            GovernmentOrderModel.go_number == go_number,
        )

        return self._session.scalar(statement)

    def add_relationship(
        self,
        source_go_id: UUID,
        target_go_id: UUID,
        relationship: ExtractedRelationship,
    ) -> GORelationshipModel:
        """Create a directed Government Order relationship.

        Args:
            source_go_id: Source Government Order identifier.
            target_go_id: Target Government Order identifier.
            relationship: Extracted relationship information.

        Returns:
            Created GORelationshipModel.

        Raises:
            ValueError: If source and target are identical.
        """
        if source_go_id == target_go_id:
            raise ValueError(
                "A Government Order cannot have a self relationship."
            )

        relation = GORelationshipModel(
            source_go_id=source_go_id,
            target_go_id=target_go_id,
            relationship_type=relationship.relationship_type.value,
            matched_phrase=relationship.matched_phrase,
            page_number=relationship.page_number,
        )

        self._session.add(relation)
        self._session.flush()

        return relation

    def get_outgoing_relationships(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Get relationships originating from a Government Order.

        Args:
            government_order_id: Government Order identifier.

        Returns:
            List of outgoing relationships.
        """
        statement = select(GORelationshipModel).where(
            GORelationshipModel.source_go_id == government_order_id,
        )

        return list(self._session.scalars(statement).all())

    def get_incoming_relationships(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Get relationships pointing to a Government Order.

        Args:
            government_order_id: Government Order identifier.

        Returns:
            List of incoming relationships.
        """
        statement = select(GORelationshipModel).where(
            GORelationshipModel.target_go_id == government_order_id,
        )

        return list(self._session.scalars(statement).all())

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()