"""
Recursive Government Order status verification service.

This module performs deterministic status verification using
the Government Order relationship graph stored in PostgreSQL.

No LLM or generative model is used.
"""

from dataclasses import dataclass
from uuid import UUID

from app.models.identifier_extraction import (
    RelationshipType,
)
from app.models.status_verification import (
    GovernmentOrderStatus,
    StatusVerificationResult,
)
from app.services.metadata_service import MetadataService
from app.storage.relational.models import (
    GORelationshipModel,
    GovernmentOrderModel,
)


@dataclass
class _TraversalState:
    """
    Maintain state for one Government Order during DFS traversal.
    """

    government_order_id: UUID
    government_order: GovernmentOrderModel
    expanded: bool = False


class StatusVerificationService:
    """
    Verify Government Order status using relationship-graph traversal.

    The relationship graph is represented as:

        source_go_id
              |
              | AMENDS / SUPERSEDES / CANCELS
              v
        target_go_id

    The source Government Order is the order that performs
    the legal action on the target Government Order.

    Example:

        GO-2 --AMENDS--> GO-1

    means GO-2 amends GO-1.

    A stack-based DFS is used instead of Python recursion.
    This avoids dependence on the Python recursion limit and
    allows explicit cycle detection.
    """

    def __init__(
        self,
        metadata_service: MetadataService,
    ) -> None:
        """
        Initialize the status verification service.

        Args:
            metadata_service:
                Service used to access Government Order metadata
                and relationships.
        """

        self._metadata_service = metadata_service

    # ==================================================================
    # Public API
    # ==================================================================

    def verify_by_go_number(
        self,
        go_number: str,
    ) -> StatusVerificationResult:
        """
        Verify Government Order status using its GO number.

        Args:
            go_number:
                Canonical Government Order number.

        Returns:
            StatusVerificationResult.

        Raises:
            ValueError:
                If the Government Order does not exist.
        """

        cleaned_go_number = go_number.strip()

        if not cleaned_go_number:
            raise ValueError(
                "Government Order number cannot be empty."
            )

        government_order = (
            self._metadata_service.find_by_go_number(
                cleaned_go_number
            )
        )

        if government_order is None:
            raise ValueError(
                "Government Order was not found."
            )

        return self.verify(
            government_order.id
        )

    def verify(
        self,
        government_order_id: UUID,
    ) -> StatusVerificationResult:
        """
        Verify Government Order status using stack-based DFS.

        The traversal starts from the requested Government Order
        and follows incoming legal relationships to newer
        Government Orders.

        Args:
            government_order_id:
                Database ID of the Government Order.

        Returns:
            StatusVerificationResult.

        Raises:
            ValueError:
                If the Government Order does not exist.
        """

        root = self._metadata_service.get_by_id(
            government_order_id
        )

        if root is None:
            raise ValueError(
                "Government Order was not found."
            )

        # --------------------------------------------------------------
        # Status calculated for each visited Government Order.
        # --------------------------------------------------------------

        statuses: dict[
            UUID,
            GovernmentOrderStatus,
        ] = {}

        # --------------------------------------------------------------
        # Nodes already visited.
        # --------------------------------------------------------------

        visited: set[UUID] = set()

        # --------------------------------------------------------------
        # Nodes currently on the DFS path.
        #
        # Used for cycle detection.
        # --------------------------------------------------------------

        active_path: set[UUID] = set()

        # --------------------------------------------------------------
        # Government Orders encountered during traversal.
        # --------------------------------------------------------------

        traversed_go_numbers: list[str] = []

        # --------------------------------------------------------------
        # Diagnostics.
        # --------------------------------------------------------------

        cycle_detected = False
        relationships_checked = 0

        # --------------------------------------------------------------
        # Explicit stack for DFS.
        #
        # expanded=False:
        #     First visit to node.
        #
        # expanded=True:
        #     All relevant children have been processed.
        # --------------------------------------------------------------

        stack: list[_TraversalState] = [
            _TraversalState(
                government_order_id=root.id,
                government_order=root,
            )
        ]

        while stack:

            current_state = stack[-1]

            current_id = (
                current_state.government_order_id
            )

            current_go = (
                current_state.government_order
            )

            # ==========================================================
            # FIRST VISIT
            # ==========================================================

            if not current_state.expanded:

                # ------------------------------------------------------
                # Cycle protection.
                # ------------------------------------------------------

                if current_id in active_path:
                    cycle_detected = True

                    stack.pop()

                    continue

                # ------------------------------------------------------
                # Already completely processed.
                # ------------------------------------------------------

                if current_id in visited:
                    stack.pop()

                    continue

                # ------------------------------------------------------
                # Mark current node as visited and active.
                # ------------------------------------------------------

                visited.add(current_id)

                active_path.add(current_id)

                traversed_go_numbers.append(
                    current_go.go_number
                )

                current_state.expanded = True

                # ------------------------------------------------------
                # Get relationships where the current GO is the target.
                #
                # Example:
                #
                # GO-2 --AMENDS--> GO-1
                #
                # When verifying GO-1, GO-2 is an incoming relationship.
                # ------------------------------------------------------

                relationships = (
                    self._metadata_service
                    .get_incoming_relationships(
                        current_id
                    )
                )

                # ------------------------------------------------------
                # Only relationships that can change legal status
                # participate in status verification.
                #
                # READ_AS does not change status.
                # ------------------------------------------------------

                status_relationships = [
                    relationship
                    for relationship in relationships
                    if self._is_status_relationship(
                        relationship
                    )
                ]

                relationships_checked += len(
                    status_relationships
                )

                # ------------------------------------------------------
                # Find newer Government Orders connected to this GO.
                # ------------------------------------------------------

                children: list[
                    GovernmentOrderModel
                ] = []

                for relationship in status_relationships:

                    source_go = (
                        self._metadata_service.get_by_id(
                            relationship.source_go_id
                        )
                    )

                    if source_go is None:
                        continue

                    # --------------------------------------------------
                    # Prevent a self-loop.
                    # --------------------------------------------------

                    if source_go.id == current_id:
                        cycle_detected = True

                        continue

                    # --------------------------------------------------
                    # Detect a graph cycle.
                    # --------------------------------------------------

                    if source_go.id in active_path:
                        cycle_detected = True

                        continue

                    # --------------------------------------------------
                    # Do not process an already visited node again.
                    # --------------------------------------------------

                    if source_go.id in visited:
                        continue

                    children.append(
                        source_go
                    )

                # ------------------------------------------------------
                # Sort deterministically.
                # ------------------------------------------------------

                children.sort(
                    key=lambda order: (
                        order.go_number
                    ),
                    reverse=True,
                )

                # ------------------------------------------------------
                # Push children onto the DFS stack.
                # ------------------------------------------------------

                for child in children:

                    stack.append(
                        _TraversalState(
                            government_order_id=child.id,
                            government_order=child,
                        )
                    )

                continue

            # ==========================================================
            # POST-ORDER PROCESSING
            # ==========================================================
            #
            # All reachable newer Government Orders have now been
            # traversed.
            # ==========================================================

            status = self._calculate_status(
                current_go_id=current_id,
            )

            statuses[current_id] = status

            # ----------------------------------------------------------
            # Current node is no longer on the active DFS path.
            # ----------------------------------------------------------

            active_path.discard(current_id)

            stack.pop()

        # ==============================================================
        # Root status
        # ==============================================================

        root_status = statuses.get(
            root.id,
            GovernmentOrderStatus.ACTIVE,
        )

        return StatusVerificationResult(
            document_id=str(
                root.document_id
            ),
            go_number=root.go_number,
            status=root_status,
            traversed_go_numbers=(
                traversed_go_numbers
            ),
            relationships_checked=(
                relationships_checked
            ),
            cycle_detected=cycle_detected,
        )

    # ==================================================================
    # Relationship classification
    # ==================================================================

    @staticmethod
    def _is_status_relationship(
        relationship: GORelationshipModel,
    ) -> bool:
        """
        Determine whether a relationship can change legal status.

        Status-changing relationships:

            AMENDS
            SUPERSEDES
            CANCELS

        READ_AS is intentionally excluded because it does not
        cancel or amend the referenced Government Order.

        Args:
            relationship:
                Government Order relationship.

        Returns:
            True when the relationship affects legal status.
        """

        relationship_type = (
            relationship.relationship_type
        )

        return relationship_type in {
            RelationshipType.AMENDS.value,
            RelationshipType.SUPERSEDES.value,
            RelationshipType.CANCELS.value,
        }

    # ==================================================================
    # Status calculation
    # ==================================================================

    def _calculate_status(
        self,
        current_go_id: UUID,
    ) -> GovernmentOrderStatus:
        """
        Calculate the legal status of a Government Order.

        Rules:

            CANCELS
                -> CANCELED

            AMENDS
                -> AMENDED

            SUPERSEDES
                -> AMENDED

            READ_AS
                -> no status change

        Important:

        A legal relationship is not removed merely because the
        source Government Order later receives its own status.

        Example:

            GO-3 --CANCELS--> GO-2
            GO-2 --AMENDS---> GO-1

        GO-2 is CANCELED, but the explicit relationship

            GO-2 --AMENDS--> GO-1

        still establishes that GO-1 was amended.

        Therefore status is determined from the explicit
        relationship graph rather than requiring the source
        Government Order to have ACTIVE status.
        """

        relationships = (
            self._metadata_service
            .get_incoming_relationships(
                current_go_id
            )
        )

        # --------------------------------------------------------------
        # Cancellation takes precedence.
        # --------------------------------------------------------------

        for relationship in relationships:

            if (
                relationship.relationship_type
                == RelationshipType.CANCELS.value
            ):
                return GovernmentOrderStatus.CANCELED

        # --------------------------------------------------------------
        # Amendment and supersession.
        #
        # Both mean the current GO has been changed/replaced by
        # another Government Order.
        # --------------------------------------------------------------

        for relationship in relationships:

            if (
                relationship.relationship_type
                in {
                    RelationshipType.AMENDS.value,
                    RelationshipType.SUPERSEDES.value,
                }
            ):
                return GovernmentOrderStatus.AMENDED

        # --------------------------------------------------------------
        # No status-changing relationship.
        # --------------------------------------------------------------

        return GovernmentOrderStatus.ACTIVE