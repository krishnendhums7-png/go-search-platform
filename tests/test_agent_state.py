from app.models.agent_state import AgentState


def test_agent_state_supports_module_10_fields() -> None:
    """Test the shared state used by the multi-agent workflow."""

    state: AgentState = {
        "query": "G.O.(Rt) No. 114/2025/ITD",

        # Agent 1
        "intent": "status_lookup",
        "extracted_go_number": "114/2025/ITD",
        "intent_completed": True,

        # Agent 2
        "search_results": [],
        "search_completed": True,

        # Agent 3
        "status_results": [],
        "status_completed": True,

        # Agent 0
        "next_agent": "complete",
        "workflow_completed": True,

        # Final output
        "final_results": [],
        "errors": [],
    }

    assert state["query"] == "G.O.(Rt) No. 114/2025/ITD"
    assert state["intent"] == "status_lookup"
    assert state["extracted_go_number"] == "114/2025/ITD"

    assert state["intent_completed"] is True
    assert state["search_completed"] is True
    assert state["status_completed"] is True

    assert state["next_agent"] == "complete"
    assert state["workflow_completed"] is True


def test_agent_state_allows_empty_workflow_state() -> None:
    """Test that AgentState supports partial state initialization."""

    state: AgentState = {
        "query": "Which order contains travelling rules?",
    }

    assert state["query"] == (
        "Which order contains travelling rules?"
    )