"""
Tests for recursive Government Order status verification.
"""

from datetime import date
from uuid import UUID, uuid4

from app.models.status_verification import (
    GovernmentOrderStatus,
)
from app.services.status_verification_service import (
    StatusVerificationService,
)


class FakeGovernmentOrder:
    """Represent a minimal Government Order for testing."""

    def __init__(
        self,
        go_number: str,
        document_id: UUID | None = None,
    ) -> None:
        """Initialize a fake Government Order."""

        self.id = uuid4()
        self.document_id = (
            document_id or uuid4()
        )
        self.go_number = go_number
        self.issue_date = date.today()
        self.department = "Test Department"


class FakeRelationship:
    """Represent a minimal Government Order relationship."""

    def __init__(
        self,
        source_go_id: UUID,
        target_go_id: UUID,
        relationship_type: str,
    ) -> None:
        """Initialize a fake relationship."""

        self.id = uuid4()
        self.source_go_id = source_go_id
        self.target_go_id = target_go_id
        self.relationship_type = (
            relationship_type
        )
        self.matched_phrase = (
            "test relationship"
        )
        self.page_number = 1


class FakeMetadataService:
    """In-memory metadata service for status tests."""

    def __init__(self) -> None:
        """Initialize the fake metadata service."""

        self.orders: dict[
            UUID,
            FakeGovernmentOrder,
        ] = {}

        self.relationships: list[
            FakeRelationship
        ] = []

    def add_order(
        self,
        order: FakeGovernmentOrder,
    ) -> None:
        """Add a Government Order."""

        self.orders[order.id] = order

    def add_relationship(
        self,
        relationship: FakeRelationship,
    ) -> None:
        """Add a Government Order relationship."""

        self.relationships.append(
            relationship
        )

    def find_by_go_number(
        self,
        go_number: str,
    ):
        """Find an order by GO number."""

        for order in self.orders.values():
            if order.go_number == go_number:
                return order

        return None

    def get_by_id(
        self,
        government_order_id: UUID,
    ):
        """Get an order by ID."""

        return self.orders.get(
            government_order_id
        )

    def get_incoming_relationships(
        self,
        government_order_id: UUID,
    ) -> list[FakeRelationship]:
        """Get relationships pointing to an order."""

        return [
            relationship
            for relationship in self.relationships
            if relationship.target_go_id
            == government_order_id
        ]


def test_active_go() -> None:
    """An order without status-changing successors is ACTIVE."""

    metadata = FakeMetadataService()

    order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2026/TEST"
    )

    metadata.add_order(order)

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.ACTIVE
    )

    assert result.cycle_detected is False


def test_amended_go() -> None:
    """An order amended by an active successor is AMENDED."""

    metadata = FakeMetadataService()

    old_order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2025/TEST"
    )

    new_order = FakeGovernmentOrder(
        "G.O.(P) No. 2/2026/TEST"
    )

    metadata.add_order(old_order)
    metadata.add_order(new_order)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=new_order.id,
            target_go_id=old_order.id,
            relationship_type="AMENDS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        old_order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.AMENDED
    )


def test_superseded_go_is_amended() -> None:
    """A superseded order is reported as AMENDED."""

    metadata = FakeMetadataService()

    old_order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2025/TEST"
    )

    new_order = FakeGovernmentOrder(
        "G.O.(P) No. 2/2026/TEST"
    )

    metadata.add_order(old_order)
    metadata.add_order(new_order)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=new_order.id,
            target_go_id=old_order.id,
            relationship_type="SUPERSEDES",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        old_order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.AMENDED
    )


def test_canceled_go() -> None:
    """An order canceled by an active successor is CANCELED."""

    metadata = FakeMetadataService()

    old_order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2025/TEST"
    )

    cancel_order = FakeGovernmentOrder(
        "G.O.(P) No. 2/2026/TEST"
    )

    metadata.add_order(old_order)
    metadata.add_order(cancel_order)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=cancel_order.id,
            target_go_id=old_order.id,
            relationship_type="CANCELS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        old_order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.CANCELED
    )


def test_recursive_status_chain() -> None:
    """
    Verify a multi-level relationship chain.

    GO-3 amends GO-2.
    GO-2 amends GO-1.

    GO-1 must be AMENDED.
    """

    metadata = FakeMetadataService()

    go1 = FakeGovernmentOrder(
        "G.O.(P) No. 1/2024/TEST"
    )

    go2 = FakeGovernmentOrder(
        "G.O.(P) No. 2/2025/TEST"
    )

    go3 = FakeGovernmentOrder(
        "G.O.(P) No. 3/2026/TEST"
    )

    metadata.add_order(go1)
    metadata.add_order(go2)
    metadata.add_order(go3)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=go2.id,
            target_go_id=go1.id,
            relationship_type="AMENDS",
        )
    )

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=go3.id,
            target_go_id=go2.id,
            relationship_type="AMENDS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        go1.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.AMENDED
    )

    assert (
        len(result.traversed_go_numbers)
        == 3
    )


def test_recursive_cancellation_chain() -> None:
    """
    Verify that a canceled successor does not remain an
    effective amendment/cancellation source.
    """

    metadata = FakeMetadataService()

    old_order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2024/TEST"
    )

    middle_order = FakeGovernmentOrder(
        "G.O.(P) No. 2/2025/TEST"
    )

    cancel_order = FakeGovernmentOrder(
        "G.O.(P) No. 3/2026/TEST"
    )

    metadata.add_order(old_order)
    metadata.add_order(middle_order)
    metadata.add_order(cancel_order)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=middle_order.id,
            target_go_id=old_order.id,
            relationship_type="AMENDS",
        )
    )

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=cancel_order.id,
            target_go_id=middle_order.id,
            relationship_type="CANCELS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        old_order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.AMENDED
    )


def test_read_as_does_not_change_status() -> None:
    """READ_AS relationships do not change GO legal status."""

    metadata = FakeMetadataService()

    order = FakeGovernmentOrder(
        "G.O.(P) No. 1/2026/TEST"
    )

    other_order = FakeGovernmentOrder(
        "G.O.(P) No. 2/2026/TEST"
    )

    metadata.add_order(order)
    metadata.add_order(other_order)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=other_order.id,
            target_go_id=order.id,
            relationship_type="READ_AS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        order.id
    )

    assert (
        result.status
        == GovernmentOrderStatus.ACTIVE
    )


def test_relationship_loop_is_detected() -> None:
    """Corrupt cyclic relationships are detected safely."""

    metadata = FakeMetadataService()

    go_a = FakeGovernmentOrder(
        "G.O.(P) No. 1/2025/TEST"
    )

    go_b = FakeGovernmentOrder(
        "G.O.(P) No. 2/2026/TEST"
    )

    metadata.add_order(go_a)
    metadata.add_order(go_b)

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=go_b.id,
            target_go_id=go_a.id,
            relationship_type="AMENDS",
        )
    )

    metadata.add_relationship(
        FakeRelationship(
            source_go_id=go_a.id,
            target_go_id=go_b.id,
            relationship_type="AMENDS",
        )
    )

    service = StatusVerificationService(
        metadata
    )

    result = service.verify(
        go_a.id
    )

    assert result.cycle_detected is True

    assert len(
        result.traversed_go_numbers
    ) <= 2


def test_verify_by_go_number() -> None:
    """Verify an order using its Government Order number."""

    metadata = FakeMetadataService()

    order = FakeGovernmentOrder(
        "G.O.(P) No. 10/2026/TEST"
    )

    metadata.add_order(order)

    service = StatusVerificationService(
        metadata
    )

    result = service.verify_by_go_number(
        "G.O.(P) No. 10/2026/TEST"
    )

    assert (
        result.go_number
        == "G.O.(P) No. 10/2026/TEST"
    )

    assert (
        result.status
        == GovernmentOrderStatus.ACTIVE
    )


def test_missing_go_is_rejected() -> None:
    """Missing Government Orders must raise ValueError."""

    metadata = FakeMetadataService()

    service = StatusVerificationService(
        metadata
    )

    try:
        service.verify_by_go_number(
            "G.O.(P) No. 999/2099/UNKNOWN"
        )

        assert False

    except ValueError as error:
        assert (
            str(error)
            == "Government Order was not found."
        )