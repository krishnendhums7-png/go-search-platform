"""
Run the Kerala Government Orders multi-agent orchestrator.

This script connects the real:

    PostgreSQL
    Qdrant
    multilingual embedding model
    Agent 1 - Intent Parser
    Agent 2 - Hybrid Searcher
    Agent 3 - Status Verifier
    Agent 0 - LangGraph Orchestrator

No legal text is generated, paraphrased, or modified.
"""

import sys
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient


# Make the project root importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.hybrid_search_agent import HybridSearchAgent
from app.agents.intent_agent import IntentAgent
from app.agents.orchestrator import GOOrchestrator
from app.agents.status_agent import StatusAgent
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import (
    HybridSearchService,
)
from app.services.metadata_service import MetadataService
from app.services.status_verification_service import (
    StatusVerificationService,
)
from app.storage.relational.session import SessionFactory
from app.storage.vector.qdrant_client import QdrantVectorStore


# ============================================================================
# Configuration
# ============================================================================

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "government_orders"


# ============================================================================
# Orchestrator Construction
# ============================================================================


def build_orchestrator(
    session: Any,
) -> GOOrchestrator:
    """
    Build the real multi-agent orchestrator.

    The orchestrator uses the existing services from
    Modules 7, 8, and 9.

    Agent architecture:

        Agent 0 - LangGraph Orchestrator
            |
            +-- Agent 1 - Intent Parser
            |
            +-- Agent 2 - Hybrid Searcher
            |
            +-- Agent 3 - Status Verifier

    Args:
        session:
            Active PostgreSQL session.

    Returns:
        Configured GOOrchestrator.
    """

    # ------------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------------

    embedding_service = EmbeddingService()

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
    )

    # ------------------------------------------------------------------------
    # Module 8 - Hybrid Search
    # ------------------------------------------------------------------------

    hybrid_search_service = HybridSearchService(
        session=session,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    # ------------------------------------------------------------------------
    # Module 7 - Metadata / Relationships
    #
    # MetadataService is not a separate agent anymore.
    # It is used internally by the status verification layer.
    # ------------------------------------------------------------------------

    metadata_service = MetadataService(
        session=session,
    )

    # ------------------------------------------------------------------------
    # Module 9 - Recursive Status Verification
    # ------------------------------------------------------------------------

    status_service = StatusVerificationService(
        metadata_service=metadata_service,
    )

    # ------------------------------------------------------------------------
    # Module 10 - Agents
    # ------------------------------------------------------------------------

    # Agent 1 - Intent Parser
    intent_agent = IntentAgent()

    # Agent 2 - Hybrid Searcher
    hybrid_search_agent = HybridSearchAgent(
        hybrid_search_service=hybrid_search_service,
    )

    # Agent 3 - Status Verifier
    status_agent = StatusAgent(
        status_service=status_service,
    )

    # ------------------------------------------------------------------------
    # Agent 0 - LangGraph Orchestrator
    # ------------------------------------------------------------------------

    return GOOrchestrator(
        intent_agent=intent_agent,
        hybrid_search_agent=hybrid_search_agent,
        status_agent=status_agent,
    )


# ============================================================================
# Output Helpers
# ============================================================================


def print_pipeline_status(
    state: dict[str, Any],
) -> None:
    """
    Print the execution status of the multi-agent pipeline.

    Args:
        state:
            State returned by the LangGraph orchestrator.
    """

    print()
    print("=" * 70)
    print("PIPELINE STATUS")
    print("=" * 70)

    print(
        f"Intent completed:   "
        f"{state.get('intent_completed')}"
    )

    print(
        f"Search completed:   "
        f"{state.get('search_completed')}"
    )

    print(
        f"Status completed:   "
        f"{state.get('status_completed')}"
    )

    print(
        f"Workflow completed: "
        f"{state.get('workflow_completed')}"
    )

    print(
        f"Next agent:         "
        f"{state.get('next_agent')}"
    )


def print_errors(
    state: dict[str, Any],
) -> None:
    """
    Print workflow errors.

    Args:
        state:
            State returned by the LangGraph orchestrator.
    """

    errors = state.get(
        "errors",
        [],
    )

    if not errors:
        return

    print()
    print("-" * 70)
    print("ERRORS")
    print("-" * 70)

    for error in errors:
        print(f"  - {error}")


# ============================================================================
# Search Results
# ============================================================================


def print_search_results(
    state: dict[str, Any],
) -> None:
    """
    Print hybrid search results.

    Retrieved legal text is printed exactly as returned by
    the hybrid search service.

    Args:
        state:
            State returned by the LangGraph orchestrator.
    """

    print()
    print("-" * 70)
    print("HYBRID SEARCH RESULTS")
    print("-" * 70)

    search_results = state.get(
        "search_results",
        [],
    )

    if not search_results:
        print("No search results.")
        return

    for index, result in enumerate(
        search_results,
        start=1,
    ):
        print()
        print(f"[{index}]")

        print(
            f"GO Number: "
            f"{result.get('go_number')}"
        )

        print(
            f"Document ID: "
            f"{result.get('document_id')}"
        )

        print(
            f"Page: "
            f"{result.get('page_number')}"
        )

        print(
            f"Issue Date: "
            f"{result.get('issue_date')}"
        )

        print(
            f"Department: "
            f"{result.get('department')}"
        )

        print(
            f"Semantic Score: "
            f"{result.get('semantic_score')}"
        )

        print(
            f"Metadata Match: "
            f"{result.get('metadata_match')}"
        )

        print(
            f"Combined Score: "
            f"{result.get('combined_score')}"
        )

        print("Retrieved Text:")

        print(
            result.get(
                "text",
                "",
            )[:1000]
        )


# ============================================================================
# Status Results
# ============================================================================


def print_status_results(
    state: dict[str, Any],
) -> None:
    """
    Print recursive Government Order status results.

    Args:
        state:
            State returned by the LangGraph orchestrator.
    """

    print()
    print("-" * 70)
    print("STATUS VERIFICATION")
    print("-" * 70)

    status_results = state.get(
        "status_results",
        [],
    )

    if not status_results:
        print("No status results.")
        return

    for status in status_results:
        print()

        print(
            f"GO Number: "
            f"{status.get('go_number')}"
        )

        print(
            f"Status: "
            f"{status.get('status')}"
        )

        print(
            f"Relationships Checked: "
            f"{status.get('relationships_checked')}"
        )

        print(
            f"Cycle Detected: "
            f"{status.get('cycle_detected')}"
        )

        traversal = status.get(
            "traversal",
            [],
        )

        if traversal:
            print(
                "Traversal: "
                f"{' -> '.join(traversal)}"
            )


# ============================================================================
# Final Deterministic Results
# ============================================================================


def print_final_results(
    state: dict[str, Any],
) -> None:
    """
    Print final deterministic results produced by Agent 0.

    No FinalAgent is used. Agent 0 performs the final
    deterministic aggregation directly.

    Args:
        state:
            State returned by the LangGraph orchestrator.
    """

    print()
    print("-" * 70)
    print("FINAL DETERMINISTIC RESULTS")
    print("-" * 70)

    final_results = state.get(
        "final_results",
        [],
    )

    if not final_results:
        print("No final results.")
        return

    for index, result in enumerate(
        final_results,
        start=1,
    ):
        print()
        print(f"[{index}]")

        print(
            f"GO Number: "
            f"{result.get('go_number')}"
        )

        print(
            f"Document ID: "
            f"{result.get('document_id')}"
        )

        print(
            f"Issue Date: "
            f"{result.get('issue_date')}"
        )

        print(
            f"Department: "
            f"{result.get('department')}"
        )

        print(
            f"Status: "
            f"{result.get('status')}"
        )

        print(
            f"Page: "
            f"{result.get('page_number')}"
        )

        print(
            f"Semantic Score: "
            f"{result.get('semantic_score')}"
        )

        print(
            f"Combined Score: "
            f"{result.get('combined_score')}"
        )

        print(
            f"Relationships Checked: "
            f"{result.get('relationships_checked')}"
        )

        print(
            f"Cycle Detected: "
            f"{result.get('cycle_detected')}"
        )

        traversal = result.get(
            "status_traversal",
            [],
        )

        if traversal:
            print(
                "Status Traversal: "
                f"{' -> '.join(traversal)}"
            )

        print("Retrieved Legal Text:")

        print(
            result.get(
                "text",
                "",
            )[:1000]
        )


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """
    Run the real multi-agent Government Order search.
    """

    query = (
        "Which government order discusses Public WiFi?"
    )

    print("=" * 70)
    print("KERALA GO - MODULE 10")
    print("REAL MULTI-AGENT ORCHESTRATION")
    print("=" * 70)

    print()
    print(f"Query: {query}")

    session = SessionFactory()

    try:
        orchestrator = build_orchestrator(
            session=session,
        )

        state = orchestrator.run(
            query=query,
        )

        print_pipeline_status(
            state
        )

        print_errors(
            state
        )

        print_search_results(
            state
        )

        print_status_results(
            state
        )

        print_final_results(
            state
        )

        print()
        print("=" * 70)

    finally:
        session.close()


if __name__ == "__main__":
    main()