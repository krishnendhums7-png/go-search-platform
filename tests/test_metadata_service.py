"""Tests for Government Order metadata storage."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.identifier_extraction import (
    ExtractedRelationship,
    RelationshipType,
)
from app.services.metadata_service import MetadataService
from app.storage.relational.models import Base


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Create an isolated in-memory database session."""
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def test_create_government_order(
    session: Session,
) -> None:
    """Test Government Order metadata creation."""
    service = MetadataService(session)

    document_id = uuid4()

    government_order = service.create_government_order(
        document_id=document_id,
        go_number="G.O.(P) No.15/2026/FIN",
        department="Finance Department",
    )

    assert government_order.document_id == document_id
    assert government_order.go_number == "G.O.(P) No.15/2026/FIN"
    assert government_order.department == "Finance Department"


def test_find_government_order(
    session: Session,
) -> None:
    """Test Government Order lookup by GO number."""
    service = MetadataService(session)

    service.create_government_order(
        document_id=uuid4(),
        go_number="G.O.(P) No.15/2026/FIN",
    )

    session.commit()

    result = service.find_by_go_number(
        "G.O.(P) No.15/2026/FIN",
    )

    assert result is not None
    assert result.go_number == "G.O.(P) No.15/2026/FIN"


def test_create_directed_relationship(
    session: Session,
) -> None:
    """Test directed relationship creation."""
    service = MetadataService(session)

    source = service.create_government_order(
        document_id=uuid4(),
        go_number="G.O.(P) No.20/2026/FIN",
    )

    target = service.create_government_order(
        document_id=uuid4(),
        go_number="G.O.(P) No.15/2026/FIN",
    )

    relationship = ExtractedRelationship(
        relationship_type=RelationshipType.AMENDS,
        matched_phrase="amends",
        page_number=1,
    )

    result = service.add_relationship(
        source_go_id=source.id,
        target_go_id=target.id,
        relationship=relationship,
    )

    assert result.source_go_id == source.id
    assert result.target_go_id == target.id
    assert result.relationship_type == "AMENDS"


def test_self_relationship_rejected(
    session: Session,
) -> None:
    """Test that self-referencing graph edges are rejected."""
    service = MetadataService(session)

    government_order = service.create_government_order(
        document_id=uuid4(),
        go_number="G.O.(P) No.20/2026/FIN",
    )

    relationship = ExtractedRelationship(
        relationship_type=RelationshipType.CANCELS,
        matched_phrase="cancels",
        page_number=1,
    )

    with pytest.raises(ValueError):
        service.add_relationship(
            source_go_id=government_order.id,
            target_go_id=government_order.id,
            relationship=relationship,
        )