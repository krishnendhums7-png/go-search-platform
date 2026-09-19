"""
Repository for Government Order metadata search.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.relational.models import (
    GovernmentOrderModel,
)


class GovernmentOrderRepository:
    """Provide Government Order metadata queries."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository."""
        self._session = session

    def search_by_go_number(
        self,
        go_number: str,
    ) -> GovernmentOrderModel | None:
        """Find a Government Order by exact GO number."""

        statement = select(
            GovernmentOrderModel
        ).where(
            GovernmentOrderModel.go_number == go_number
        )

        return self._session.scalar(statement)

    def search_by_go_number_contains(
        self,
        value: str,
    ) -> list[GovernmentOrderModel]:
        """Find Government Orders containing a GO number fragment."""

        statement = select(
            GovernmentOrderModel
        ).where(
            GovernmentOrderModel.go_number.ilike(
                f"%{value}%"
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def get_by_id(
        self,
        government_order_id: UUID,
    ) -> GovernmentOrderModel | None:
        """Retrieve a Government Order by its database ID."""

        return self._session.get(
            GovernmentOrderModel,
            government_order_id,
        )

    def get_by_document_id(
        self,
        document_id: UUID,
    ) -> list[GovernmentOrderModel]:
        """Retrieve all GO records belonging to a document."""

        statement = select(
            GovernmentOrderModel
        ).where(
            GovernmentOrderModel.document_id
            == document_id
        )

        return list(
            self._session.scalars(statement).all()
        )