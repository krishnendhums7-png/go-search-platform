"""Tests for Government Order relationship ingestion."""

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.identifier_extraction import (
    ExtractedReference,
    ExtractedRelationship,
    RelationshipType,
)
from app.services.relationship_ingestion_service import (
    RelationshipIngestionService,
)
from app.storage.relational.models import Base


def create_session():
    """Create an in-memory SQLite test session."""

    engine = create_engine(
        "sqlite:///:memory:",
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return session_factory()


def test_relationship_resolves_selected_ordinals():
    """Only referenced ordinals become graph edges."""

    session = create_session()

    try:
        source_go_id = uuid4()
        target_one_id = uuid4()
        target_two_id = uuid4()
        target_three_id = uuid4()
        target_four_id = uuid4()

        references = [
            ExtractedReference(
                ordinal=1,
                go_number=(
                    "G.O.(Rt) No. 114/2025/ITD"
                ),
                page_number=1,
            ),
            ExtractedReference(
                ordinal=2,
                go_number=(
                    "G.O.(Rt) No. 151/2025/ITD"
                ),
                page_number=1,
            ),
            ExtractedReference(
                ordinal=3,
                go_number=(
                    "G.O.(Rt) No. 228/2025/ITD"
                ),
                page_number=1,
            ),
            ExtractedReference(
                ordinal=4,
                go_number=(
                    "G.O.(Rt) No. 264/2025/ITD"
                ),
                page_number=1,
            ),
        ]

        go_id_by_number = {
            references[0].go_number: target_one_id,
            references[1].go_number: target_two_id,
            references[2].go_number: target_three_id,
            references[3].go_number: target_four_id,
        }

        relationship = ExtractedRelationship(
            relationship_type=(
                RelationshipType.AMENDS
            ),
            matched_phrase=(
                "modified to the above extent"
            ),
            page_number=4,
            reference_ordinals=[1, 2, 4],
        )

        service = RelationshipIngestionService(
            session
        )

        persisted = service.store_relationship(
            source_go_id=source_go_id,
            relationship=relationship,
            references=references,
            go_id_by_number=go_id_by_number,
        )

        assert len(persisted) == 3

        target_ids = {
            item.target_go_id
            for item in persisted
        }

        assert target_one_id in target_ids
        assert target_two_id in target_ids
        assert target_four_id in target_ids

        assert target_three_id not in target_ids

    finally:
        session.close()


def test_missing_target_is_not_guessed():
    """Missing target records do not create graph edges."""

    session = create_session()

    try:
        source_go_id = uuid4()
        target_go_id = uuid4()

        reference = ExtractedReference(
            ordinal=1,
            go_number=(
                "G.O.(Rt) No. 114/2025/ITD"
            ),
            page_number=1,
        )

        relationship = ExtractedRelationship(
            relationship_type=(
                RelationshipType.AMENDS
            ),
            matched_phrase="hereby modified",
            page_number=4,
            reference_ordinals=[1],
        )

        service = RelationshipIngestionService(
            session
        )

        persisted = service.store_relationship(
            source_go_id=source_go_id,
            relationship=relationship,
            references=[reference],
            go_id_by_number={},
        )

        assert persisted == []

    finally:
        session.close()


def test_duplicate_relationship_is_not_created():
    """The same relationship is not inserted twice."""

    session = create_session()

    try:
        source_go_id = uuid4()
        target_go_id = uuid4()

        reference = ExtractedReference(
            ordinal=1,
            go_number=(
                "G.O.(Rt) No. 114/2025/ITD"
            ),
            page_number=1,
        )

        relationship = ExtractedRelationship(
            relationship_type=(
                RelationshipType.AMENDS
            ),
            matched_phrase="hereby modified",
            page_number=4,
            reference_ordinals=[1],
        )

        service = RelationshipIngestionService(
            session
        )

        go_id_by_number = {
            reference.go_number: target_go_id
        }

        first = service.store_relationship(
            source_go_id=source_go_id,
            relationship=relationship,
            references=[reference],
            go_id_by_number=go_id_by_number,
        )

        second = service.store_relationship(
            source_go_id=source_go_id,
            relationship=relationship,
            references=[reference],
            go_id_by_number=go_id_by_number,
        )

        assert len(first) == 1
        assert len(second) == 0

    finally:
        session.close()