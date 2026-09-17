"""Repository for Government Order graph relationships."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.relational.models import GORelationshipModel


class RelationshipRepository:
    """Provide graph relationship persistence operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def get_outgoing(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Retrieve outgoing graph edges.

        Args:
            government_order_id: Source Government Order ID.

        Returns:
            Outgoing relationship edges.
        """
        statement = select(GORelationshipModel).where(
            GORelationshipModel.source_go_id == government_order_id,
        )

        return list(self._session.scalars(statement).all())

    def get_incoming(
        self,
        government_order_id: UUID,
    ) -> list[GORelationshipModel]:
        """Retrieve incoming graph edges.

        Args:
            government_order_id: Target Government Order ID.

        Returns:
            Incoming relationship edges.
        """
        statement = select(GORelationshipModel).where(
            GORelationshipModel.target_go_id == government_order_id,
        )

        return list(self._session.scalars(statement).all())