"""Persist extracted Government Order relationships."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.identifier_extraction import (
    ExtractedRelationship,
    ExtractedReference,
)
from app.storage.relational.models import (
    GORelationshipModel,
)
from app.storage.relational.relationship_repository import (
    RelationshipRepository,
)


class RelationshipIngestionService:
    """Resolve and persist Government Order relationships."""

    def __init__(self, session: Session) -> None:
        """Initialize the relationship ingestion service."""
        self._session = session
        self._repository = RelationshipRepository(
            session
        )

    def store_relationship(
        self,
        source_go_id: UUID,
        relationship: ExtractedRelationship,
        references: list[ExtractedReference],
        go_id_by_number: dict[str, UUID],
    ) -> list[GORelationshipModel]:
        """Resolve relationship references and persist graph edges.

        Args:
            source_go_id: Explicit source Government Order ID.
            relationship: Extracted legal relationship.
            references: Numbered Government Order references.
            go_id_by_number: Mapping from GO number to database ID.

        Returns:
            Persisted relationship records.

        Notes:
            No target is guessed. A relationship is created only
            when its ordinal resolves to an extracted reference
            and that referenced GO exists in the relational store.
        """

        references_by_ordinal = {
            reference.ordinal: reference
            for reference in references
        }

        persisted: list[
            GORelationshipModel
        ] = []

        for ordinal in relationship.reference_ordinals:
            reference = references_by_ordinal.get(
                ordinal
            )

            if reference is None:
                continue

            target_go_id = go_id_by_number.get(
                reference.go_number
            )

            if target_go_id is None:
                continue

            relationship_type = (
                relationship.relationship_type.value
            )

            if self._repository.relationship_exists(
                source_go_id=source_go_id,
                target_go_id=target_go_id,
                relationship_type=relationship_type,
            ):
                continue

            relation = (
                self._repository.add_relationship(
                    source_go_id=source_go_id,
                    target_go_id=target_go_id,
                    relationship_type=relationship_type,
                    matched_phrase=(
                        relationship.matched_phrase
                    ),
                    page_number=(
                        relationship.page_number
                    ),
                )
            )

            persisted.append(relation)

        self._session.flush()

        return persisted