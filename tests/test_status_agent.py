"""
Tests for Module 10 Agent 3: Status Agent.
"""

from unittest.mock import Mock

from app.agents.status_agent import StatusAgent
from app.models.agent_state import AgentState
from app.models.status_verification import (
    GovernmentOrderStatus,
    StatusVerificationResult,
)


def create_status_result(
    go_number: str,
    status: GovernmentOrderStatus,
) -> StatusVerificationResult:
    """Create a deterministic status verification result."""

    return StatusVerificationResult(
        document_id=(
            "e10c021b-7039-443d-8744-765f50ea932a"
        ),
        go_number=go_number,
        status=status,
        traversed_go_numbers=[
            go_number
        ],
        relationships_checked=1,
        cycle_detected=False,
    )


def test_status_agent_returns_active_status() -> None:
    """Agent should return ACTIVE status."""

    service = Mock()

    service.verify_by_go_number.return_value = (
        create_status_result(
            "G.O.(Rt) No. 24/2026/ITD",
            GovernmentOrderStatus.ACTIVE,
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "24/2026/ITD",
        "search_results": [
            {
                "go_number": (
                    "G.O.(Rt) No. 24/2026/ITD"
                )
            }
        ],
    }

    result = agent.run(state)

    assert result["status_completed"] is True

    assert len(
        result["status_results"]
    ) == 1

    assert (
        result["status_results"][0]["status"]
        == "ACTIVE"
    )


def test_status_agent_returns_amended_status() -> None:
    """Agent should return AMENDED status."""

    service = Mock()

    service.verify_by_go_number.return_value = (
        create_status_result(
            "G.O.(Rt) No. 114/2025/ITD",
            GovernmentOrderStatus.AMENDED,
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "114/2025/ITD",
        "search_results": [
            {
                "go_number": (
                    "G.O.(Rt) No. 114/2025/ITD"
                )
            }
        ],
    }

    result = agent.run(state)

    assert result["status_completed"] is True

    assert (
        result["status_results"][0]["status"]
        == "AMENDED"
    )


def test_status_agent_returns_canceled_status() -> None:
    """Agent should return CANCELED status."""

    service = Mock()

    service.verify_by_go_number.return_value = (
        create_status_result(
            "G.O.(P) No. 10/2025/FIN",
            GovernmentOrderStatus.CANCELED,
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "10/2025/FIN",
        "search_results": [
            {
                "go_number": (
                    "G.O.(P) No. 10/2025/FIN"
                )
            }
        ],
    }

    result = agent.run(state)

    assert (
        result["status_results"][0]["status"]
        == "CANCELED"
    )


def test_empty_search_results_are_handled() -> None:
    """Agent should handle an empty search result."""

    service = Mock()

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "unknown GO",
        "search_results": [],
    }

    result = agent.run(state)

    assert result["status_completed"] is True

    assert result["status_results"] == []

    service.verify_by_go_number.assert_not_called()


def test_duplicate_go_numbers_are_verified_once() -> None:
    """Duplicate GO numbers should be verified only once."""

    service = Mock()

    service.verify_by_go_number.return_value = (
        create_status_result(
            "G.O.(Rt) No. 114/2025/ITD",
            GovernmentOrderStatus.AMENDED,
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "114/2025/ITD",
        "search_results": [
            {
                "go_number": (
                    "G.O.(Rt) No. 114/2025/ITD"
                )
            },
            {
                "go_number": (
                    "G.O.(Rt) No. 114/2025/ITD"
                )
            },
        ],
    }

    result = agent.run(state)

    assert result["status_completed"] is True

    assert len(
        result["status_results"]
    ) == 1

    service.verify_by_go_number.assert_called_once_with(
        "G.O.(Rt) No. 114/2025/ITD"
    )


def test_status_service_error_is_captured() -> None:
    """Status service errors should be stored in state."""

    service = Mock()

    service.verify_by_go_number.side_effect = (
        ValueError(
            "Government Order was not found."
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "unknown GO",
        "search_results": [
            {
                "go_number": (
                    "G.O.(Rt) No. 999/2099/XYZ"
                )
            }
        ],
    }

    result = agent.run(state)

    assert result["status_completed"] is False

    assert result["status_results"] == []

    assert any(
        "Government Order was not found."
        in error
        for error in result["errors"]
    )


def test_existing_errors_are_preserved() -> None:
    """Previous agent errors should remain in state."""

    service = Mock()

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "Government Order",
        "search_results": [],
        "errors": [
            "Search agent error."
        ],
    }

    result = agent.run(state)

    assert result["errors"] == [
        "Search agent error."
    ]


def test_traversal_information_is_preserved() -> None:
    """Status agent should preserve DFS traversal information."""

    service = Mock()

    service.verify_by_go_number.return_value = (
        StatusVerificationResult(
            document_id=(
                "e10c021b-7039-443d-8744-765f50ea932a"
            ),
            go_number=(
                "G.O.(Rt) No. 114/2025/ITD"
            ),
            status=(
                GovernmentOrderStatus.AMENDED
            ),
            traversed_go_numbers=[
                "G.O.(Rt) No. 114/2025/ITD",
                "G.O.(Rt) No. 24/2026/ITD",
            ],
            relationships_checked=1,
            cycle_detected=False,
        )
    )

    agent = StatusAgent(
        status_service=service
    )

    state: AgentState = {
        "query": "114/2025/ITD",
        "search_results": [
            {
                "go_number": (
                    "G.O.(Rt) No. 114/2025/ITD"
                )
            }
        ],
    }

    result = agent.run(state)

    status_result = result[
        "status_results"
    ][0]

    assert status_result[
        "traversed_go_numbers"
    ] == [
        "G.O.(Rt) No. 114/2025/ITD",
        "G.O.(Rt) No. 24/2026/ITD",
    ]

    assert (
        status_result["relationships_checked"]
        == 1
    )

    assert (
        status_result["cycle_detected"]
        is False
    )