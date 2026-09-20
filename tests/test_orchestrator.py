from app.agents.hybrid_search_agent import HybridSearchAgent
from app.agents.intent_agent import IntentAgent
from app.agents.orchestrator import GOOrchestrator
from app.agents.status_agent import StatusAgent


class FakeHybridSearchService:
    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        return [
            {
                "go_number": "114/2025/ITD",
                "document_id": "doc-1",
                "page_number": 1,
                "text": "Original Government Order text.",
                "score": 0.95,
            }
        ]


class FakeStatusService:
    def verify_by_go_number(
        self,
        go_number: str,
    ) -> dict:
        return {
            "go_number": go_number,
            "status": "AMENDED",
            "relationships_checked": 1,
            "cycle_detected": False,
            "traversal": [
                "114/2025/ITD",
                "24/2026/ITD",
            ],
        }


def test_orchestrator_runs_all_agents() -> None:
    """Test Agent 0 coordination of Agents 1-3."""

    intent_agent = IntentAgent()

    hybrid_search_agent = HybridSearchAgent(
        FakeHybridSearchService()
    )

    status_agent = StatusAgent(
        FakeStatusService()
    )

    orchestrator = GOOrchestrator(
        intent_agent=intent_agent,
        hybrid_search_agent=hybrid_search_agent,
        status_agent=status_agent,
    )

    result = orchestrator.run(
        "What is the status of "
        "G.O.(Rt) No. 114/2025/ITD?"
    )

    assert result["intent_completed"] is True
    assert result["search_completed"] is True
    assert result["status_completed"] is True
    assert result["workflow_completed"] is True

    assert result["intent"] == "status_lookup"
    assert result["extracted_go_number"] == "114/2025/ITD"

    assert len(result["search_results"]) == 1
    assert len(result["status_results"]) == 1

    assert result["status_results"][0]["status"] == "AMENDED"

    assert len(result["final_results"]) == 1
    assert result["final_results"][0]["go_number"] == (
        "114/2025/ITD"
    )
    assert result["final_results"][0]["status"] == "AMENDED"


def test_orchestrator_rejects_empty_query() -> None:
    """Test validation of an empty query."""

    intent_agent = IntentAgent()

    hybrid_search_agent = HybridSearchAgent(
        FakeHybridSearchService()
    )

    status_agent = StatusAgent(
        FakeStatusService()
    )

    orchestrator = GOOrchestrator(
        intent_agent=intent_agent,
        hybrid_search_agent=hybrid_search_agent,
        status_agent=status_agent,
    )

    try:
        orchestrator.run("")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Query cannot be empty."