"""Agent 3: Government Order status verification."""

from typing import Any

from app.models.agent_state import AgentState
from app.services.status_verification_service import (
    StatusVerificationService,
)


class StatusAgent:
    """Verify Government Order status using relationship traversal."""

    def __init__(
        self,
        status_service: StatusVerificationService,
    ) -> None:
        """Initialize the status verification agent.

        Args:
            status_service:
                Service used for recursive Government Order
                status verification.
        """

        self._status_service = status_service

    def run(
        self,
        state: AgentState,
    ) -> AgentState:
        """Verify the status of relevant Government Orders.

        If Agent 1 extracted a specific Government Order number,
        only that Government Order is verified.

        If no specific Government Order was extracted, the
        Government Orders returned by hybrid search are verified.

        Args:
            state:
                Current multi-agent workflow state.

        Returns:
            Updated state containing status results and errors.
        """

        search_results = state.get(
            "search_results",
            [],
        )

        extracted_go_number = state.get(
            "extracted_go_number",
        )

        errors = list(
            state.get(
                "errors",
                [],
            )
        )

        status_results: list[
            dict[str, Any]
        ] = []

        # ----------------------------------------------------------
        # Determine target Government Orders.
        # ----------------------------------------------------------

        go_numbers: list[str] = []
        seen: set[str] = set()

        # ----------------------------------------------------------
        # Explicit GO query.
        #
        # Example:
        # "What is the status of G.O.(Rt) No. 114/2025/ITD?"
        #
        # Only the explicitly requested GO is verified.
        # ----------------------------------------------------------

        if extracted_go_number:
            go_numbers.append(
                extracted_go_number
            )
            seen.add(
                extracted_go_number
            )

        # ----------------------------------------------------------
        # Semantic / general query.
        #
        # Example:
        # "Which GO discusses tourism?"
        #
        # Verify the GOs returned by hybrid search.
        # ----------------------------------------------------------

        else:
            for search_result in search_results:
                go_number = search_result.get(
                    "go_number"
                )

                if (
                    go_number
                    and go_number not in seen
                ):
                    go_numbers.append(
                        go_number
                    )
                    seen.add(
                        go_number
                    )

        # ----------------------------------------------------------
        # Nothing to verify.
        # ----------------------------------------------------------

        if not go_numbers:
            return {
                **state,
                "status_results": [],
                "status_completed": True,
                "next_agent": "complete",
                "errors": errors,
            }

        # ----------------------------------------------------------
        # Verify each target Government Order.
        # ----------------------------------------------------------

        status_completed = True

        for go_number in go_numbers:
            try:
                result = (
                    self._status_service
                    .verify_by_go_number(
                        go_number
                    )
                )

                if result is None:
                    errors.append(
                        "Government Order was not found: "
                        f"{go_number}"
                    )

                    status_completed = False
                    continue

                result_dict = (
                    self._result_to_dict(
                        result
                    )
                )

                status = result_dict.get(
                    "status"
                )

                # Convert enum to its string value.
                if hasattr(
                    status,
                    "value",
                ):
                    result_dict["status"] = (
                        status.value
                    )

                status_results.append(
                    result_dict
                )

            except Exception as exc:
                errors.append(
                    str(exc)
                )

                status_completed = False

        # ----------------------------------------------------------
        # Determine next workflow node.
        # ----------------------------------------------------------

        if status_completed:
            next_agent = "complete"
        else:
            next_agent = "error"

        return {
            **state,
            "status_results": status_results,
            "status_completed": status_completed,
            "next_agent": next_agent,
            "errors": errors,
        }

    @staticmethod
    def _result_to_dict(
        result: Any,
    ) -> dict[str, Any]:
        """Convert a status result into a dictionary.

        Args:
            result:
                Status result returned by Module 9.

        Returns:
            Serializable status result.

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
            "Status result must be a "
            "dictionary or a Pydantic model."
        )