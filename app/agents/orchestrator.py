"""LangGraph Agent 0 orchestrator for Government Order search."""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.hybrid_search_agent import HybridSearchAgent
from app.agents.intent_agent import IntentAgent
from app.agents.status_agent import StatusAgent
from app.models.agent_state import AgentState


class GOOrchestrator:
    """Coordinate Agents 1-3 using a hub-and-spoke workflow."""

    def __init__(
        self,
        intent_agent: IntentAgent,
        hybrid_search_agent: HybridSearchAgent,
        status_agent: StatusAgent,
    ) -> None:
        """Initialize Agent 0 and its worker agents.

        Args:
            intent_agent:
                Agent 1 responsible for intent parsing.

            hybrid_search_agent:
                Agent 2 responsible for hybrid retrieval.

            status_agent:
                Agent 3 responsible for Government Order
                status verification.
        """

        self._intent_agent = intent_agent
        self._hybrid_search_agent = hybrid_search_agent
        self._status_agent = status_agent

        self._graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph hub-and-spoke workflow."""

        graph = StateGraph(AgentState)

        # ----------------------------------------------------------
        # Agent 0 and worker agents
        # ----------------------------------------------------------

        graph.add_node(
            "orchestrator",
            self._orchestrator_node,
        )

        graph.add_node(
            "intent",
            self._intent_node,
        )

        graph.add_node(
            "hybrid_search",
            self._hybrid_search_node,
        )

        graph.add_node(
            "status",
            self._status_node,
        )

        # ----------------------------------------------------------
        # Workflow entry
        # ----------------------------------------------------------

        graph.add_edge(
            START,
            "orchestrator",
        )

        # ----------------------------------------------------------
        # Agent 0 routing
        # ----------------------------------------------------------

        graph.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            {
                "intent": "intent",
                "hybrid_search": "hybrid_search",
                "status": "status",
                "complete": END,
                "error": END,
            },
        )

        # ----------------------------------------------------------
        # Worker agents always return control to Agent 0.
        # ----------------------------------------------------------

        graph.add_edge(
            "intent",
            "orchestrator",
        )

        graph.add_edge(
            "hybrid_search",
            "orchestrator",
        )

        graph.add_edge(
            "status",
            "orchestrator",
        )

        return graph.compile()

    def _orchestrator_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Act as the central hub controlling workflow routing.

        Agent 0 decides which worker should execute next.
        Errors terminate the workflow instead of repeatedly
        calling the failed worker.
        """

        # ----------------------------------------------------------
        # Error handling
        # ----------------------------------------------------------

        if state.get("errors"):
            next_agent = "error"

        # ----------------------------------------------------------
        # Agent 1: Intent Parser
        # ----------------------------------------------------------

        elif not state.get("intent_completed"):
            next_agent = "intent"

        # ----------------------------------------------------------
        # Agent 2: Hybrid Searcher
        # ----------------------------------------------------------

        elif not state.get("search_completed"):
            next_agent = "hybrid_search"

        # ----------------------------------------------------------
        # Agent 3: Status Verifier
        # ----------------------------------------------------------

        elif not state.get("status_completed"):
            next_agent = "status"

        # ----------------------------------------------------------
        # Workflow completed
        # ----------------------------------------------------------

        else:
            next_agent = "complete"

        return {
            **state,
            "next_agent": next_agent,
        }

    def _intent_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Dispatch work to Agent 1."""

        return self._intent_agent.run(
            state
        )

    def _hybrid_search_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Dispatch work to Agent 2."""

        return self._hybrid_search_agent.run(
            state
        )

    def _status_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Dispatch work to Agent 3."""

        return self._status_agent.run(
            state
        )

    @staticmethod
    def _route_from_orchestrator(
        state: AgentState,
    ) -> Literal[
        "intent",
        "hybrid_search",
        "status",
        "complete",
        "error",
    ]:
        """Route execution from Agent 0 to the appropriate worker.

        Args:
            state:
                Current shared workflow state.

        Returns:
            Next workflow node.
        """

        return state.get(
            "next_agent",
            "intent",
        )

    def run(
        self,
        query: str,
    ) -> AgentState:
        """Run the complete multi-agent Government Order workflow.

        Args:
            query:
                User's Government Order search query.

        Returns:
            Final AgentState containing retrieval, status,
            errors, and deterministic final results.

        Raises:
            ValueError:
                If the query is empty.
        """

        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------------------
        # Initial shared state
        # ----------------------------------------------------------

        initial_state: AgentState = {
            "query": query,
            "intent_completed": False,
            "search_completed": False,
            "status_completed": False,
            "workflow_completed": False,
            "search_results": [],
            "status_results": [],
            "final_results": [],
            "errors": [],
        }

        # ----------------------------------------------------------
        # Execute LangGraph workflow
        # ----------------------------------------------------------

        result = self._graph.invoke(
            initial_state
        )

        # ----------------------------------------------------------
        # Deterministic final aggregation
        # ----------------------------------------------------------

        final_results = (
            self._build_final_results(
                result
            )
        )

        workflow_completed = not bool(
            result.get("errors")
        )

        return {
            **result,
            "final_results": final_results,
            "workflow_completed": workflow_completed,
        }

    @staticmethod
    def _build_final_results(
        state: AgentState,
    ) -> list[dict[str, object]]:
        """Combine retrieval and status information deterministically.

        Retrieved legal text is preserved exactly as returned by
        the hybrid search service. No text generation,
        paraphrasing, or modification is performed here.

        Args:
            state:
                Final workflow state.

        Returns:
            Deterministic final result records.
        """

        # ----------------------------------------------------------
        # Index status results by Government Order number.
        # ----------------------------------------------------------

        status_by_go = {
            result["go_number"]: result
            for result in state.get(
                "status_results",
                [],
            )
            if result.get("go_number")
        }

        final_results: list[
            dict[str, object]
        ] = []

        # ----------------------------------------------------------
        # Attach status information to each search result.
        # ----------------------------------------------------------

        for search_result in state.get(
            "search_results",
            [],
        ):
            go_number = search_result.get(
                "go_number"
            )

            status_result = status_by_go.get(
                go_number,
                {},
            )

            final_results.append(
                {
                    **search_result,
                    "status": status_result.get(
                        "status"
                    ),
                    "status_traversal": (
                        status_result.get(
                            "traversal",
                            [],
                        )
                    ),
                    "relationships_checked": (
                        status_result.get(
                            "relationships_checked",
                            0,
                        )
                    ),
                    "cycle_detected": (
                        status_result.get(
                            "cycle_detected",
                            False,
                        )
                    ),
                }
            )

        return final_results