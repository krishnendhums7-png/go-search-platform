"""Agent 2: Hybrid Government Order search."""

from typing import Any

from app.models.agent_state import AgentState
from app.services.hybrid_search_service import HybridSearchService


class HybridSearchAgent:
    """Execute hybrid Government Order retrieval."""

    def __init__(
        self,
        hybrid_search_service: HybridSearchService,
        result_limit: int = 5,
    ) -> None:
        """Initialize the hybrid search agent.

        Args:
            hybrid_search_service:
                Module 8 hybrid search service.

            result_limit:
                Maximum number of results to retrieve.

        Raises:
            ValueError:
                If result_limit is less than one.
        """

        if result_limit < 1:
            raise ValueError(
                "Result limit must be at least 1."
            )

        self._hybrid_search_service = (
            hybrid_search_service
        )

        self._result_limit = result_limit

    def run(
        self,
        state: AgentState,
    ) -> AgentState:
        """Execute hybrid Government Order search.

        Args:
            state:
                Current multi-agent workflow state.

        Returns:
            Updated state containing search results.

        Raises:
            ValueError:
                If the query is empty.

            TypeError:
                If a search result has an unsupported type.
        """

        query = state.get(
            "query",
            "",
        ).strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------------------
        # Execute Module 8 hybrid search.
        # ----------------------------------------------------------

        response = (
            self._hybrid_search_service.search(
                query=query,
                limit=self._result_limit,
            )
        )

        # ----------------------------------------------------------
        # HybridSearchService returns HybridSearchResponse.
        #
        # The actual result records are stored in:
        #
        #     response.results
        #
        # Keep compatibility with a plain list as well.
        # ----------------------------------------------------------

        if hasattr(
            response,
            "results",
        ):
            results = response.results

        elif isinstance(
            response,
            list,
        ):
            results = response

        else:
            raise TypeError(
                "Hybrid search response must be a "
                "HybridSearchResponse or a list."
            )

        # ----------------------------------------------------------
        # Convert results to dictionaries for AgentState.
        # ----------------------------------------------------------

        search_results: list[
            dict[str, Any]
        ] = []

        for result in results:
            search_results.append(
                self._result_to_dict(
                    result
                )
            )

        return {
            **state,
            "search_results": search_results,
            "search_completed": True,
            "next_agent": "status",
        }

    @staticmethod
    def _result_to_dict(
        result: Any,
    ) -> dict[str, Any]:
        """Convert a search result to a dictionary.

        Args:
            result:
                Hybrid search result returned by Module 8.

        Returns:
            Serializable dictionary representation.

        Raises:
            TypeError:
                If the result type is unsupported.
        """

        if hasattr(
            result,
            "model_dump",
        ):
            return result.model_dump()

        if hasattr(
            result,
            "dict",
        ):
            return result.dict()

        if isinstance(
            result,
            dict,
        ):
            return dict(result)

        raise TypeError(
            "Hybrid search result must be a "
            "dictionary or a Pydantic model."
        )