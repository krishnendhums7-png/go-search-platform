"""Repository for Government Order graph relationships."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.relational.models import GORelationshipModel


class RelationshipRepository:
    """Provide graph relationship persistence operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository."""
        self._session = session

    def get_outgoing(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Retrieve outgoing graph edges."""
        statement = select(
            GORelationshipModel
        ).where(
            GORelationshipModel.source_go_id
            == government_order_id,
        )

        return list(
            self._session.scalars(statement).all()
        )

    def get_incoming(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Retrieve incoming graph edges."""
        statement = select(
            GORelationshipModel
        ).where(
            GORelationshipModel.target_go_id
            == government_order_id,
        )

        return list(
            self._session.scalars(statement).all()
        )

    def relationship_exists(
        self,
        source_go_id: UUID,
        target_go_id: UUID,
        relationship_type: str,
    ) -> bool:
        """Check whether a graph edge already exists."""

        statement = select(
            GORelationshipModel.id
        ).where(
            GORelationshipModel.source_go_id
            == source_go_id,
            GORelationshipModel.target_go_id
            == target_go_id,
            GORelationshipModel.relationship_type
            == relationship_type,
        )

        return self._session.scalar(statement) is not None

    def add_relationship(
        self,
        source_go_id: UUID,
        target_go_id: UUID,
        relationship_type: str,
        matched_phrase: str,
        page_number: int | None = None,
    ) -> GORelationshipModel:
        """Persist a directed Government Order relationship."""

        if source_go_id == target_go_id:
            raise ValueError(
                "A Government Order cannot have "
                "a self relationship."
            )

        relationship = GORelationshipModel(
            source_go_id=source_go_id,
            target_go_id=target_go_id,
            relationship_type=relationship_type,
            matched_phrase=matched_phrase,
            page_number=page_number,
        )

        self._session.add(relationship)
        self._session.flush()

        return relationship