"""Shared state used by the multi-agent Government Order workflow."""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Represent the state passed between Agent 0 and Agents 1-3."""

    query: str

    # Agent 1
    intent: str
    extracted_go_number: str | None
    intent_completed: bool

    # Agent 2
    search_results: list[dict[str, Any]]
    search_completed: bool

    # Agent 3
    status_results: list[dict[str, Any]]
    status_completed: bool

    # Agent 0 routing
    next_agent: str
    workflow_completed: bool

    # Final structured output
    final_results: list[dict[str, Any]]

    errors: list[str]