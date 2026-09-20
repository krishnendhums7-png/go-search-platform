from app.agents.intent_agent import IntentAgent


def test_exact_go_intent() -> None:
    agent = IntentAgent()

    state = agent.run(
        {
            "query": "G.O.(Rt) No. 114/2025/ITD"
        }
    )

    assert state["intent"] == "exact_go_lookup"
    assert state["extracted_go_number"] == "114/2025/ITD"
    assert state["intent_completed"] is True


def test_status_intent() -> None:
    agent = IntentAgent()

    state = agent.run(
        {
            "query": (
                "What is the status of "
                "G.O.(Rt) No. 114/2025/ITD?"
            )
        }
    )

    assert state["intent"] == "status_lookup"


def test_semantic_intent() -> None:
    agent = IntentAgent()

    state = agent.run(
        {
            "query": "Which order contains travelling rules?"
        }
    )

    assert state["intent"] == "semantic_search"
    assert state["extracted_go_number"] is None