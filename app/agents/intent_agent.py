"""Intent parsing agent for Government Order queries."""

import re

from app.models.agent_state import AgentState


class IntentAgent:
    """Classify Government Order queries deterministically."""

    GO_NUMBER_PATTERN = re.compile(
        r"""
        G\.?\s*O\.?
        \s*
        (?:\(\s*(?:Rt|P|Ms)\s*\)\s*)?
        No\.?
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z&]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def run(self, state: AgentState) -> AgentState:
        """Parse the query intent and extract a Government Order number."""

        query = state.get("query", "").strip()

        if not query:
            raise ValueError("Query cannot be empty.")

        go_match = self.GO_NUMBER_PATTERN.search(query)

        if go_match:
            go_number = (
                f"{go_match.group('number')}/"
                f"{go_match.group('year')}/"
                f"{go_match.group('department').upper()}"
            )

            intent = self._classify_go_query(query)

            return {
                **state,
                "intent": intent,
                "extracted_go_number": go_number,
                "intent_completed": True,
                "next_agent": "search",
            }

        return {
            **state,
            "intent": "semantic_search",
            "extracted_go_number": None,
            "intent_completed": True,
            "next_agent": "search",
        }

    @staticmethod
    def _classify_go_query(query: str) -> str:
        """Classify a query containing a Government Order number."""

        normalized = query.lower()

        if any(
            keyword in normalized
            for keyword in (
                "status",
                "active",
                "amended",
                "cancelled",
                "canceled",
            )
        ):
            return "status_lookup"

        if any(
            keyword in normalized
            for keyword in (
                "amend",
                "amended",
                "modify",
                "modified",
                "cancel",
                "cancelled",
                "canceled",
                "supersede",
                "superseded",
            )
        ):
            return "relationship_lookup"

        return "exact_go_lookup"