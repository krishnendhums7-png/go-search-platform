"""
Search API for Kerala Government Orders.
"""

from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from qdrant_client import QdrantClient

from app.agents.hybrid_search_agent import HybridSearchAgent
from app.agents.intent_agent import IntentAgent
from app.agents.orchestrator import GOOrchestrator
from app.agents.status_agent import StatusAgent
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.metadata_service import MetadataService
from app.services.status_verification_service import (
    StatusVerificationService,
)
from app.storage.relational.session import SessionFactory
from app.storage.vector.qdrant_client import QdrantVectorStore


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


class SearchRequest(BaseModel):
    """Request body for Government Order search."""

    query: str = Field(
        ...,
        min_length=1,
        description="Government Order search query.",
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results.",
    )


def build_orchestrator(
    session: Any,
) -> GOOrchestrator:
    """
    Build the real Kerala GO multi-agent orchestrator.

    The orchestrator uses the existing Modules 7, 8, 9,
    and 10 implementation.
    """

    embedding_service = EmbeddingService()

    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )

    hybrid_search_service = HybridSearchService(
        session=session,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    metadata_service = MetadataService(
        session=session,
    )

    status_service = StatusVerificationService(
        metadata_service=metadata_service,
    )

    intent_agent = IntentAgent()

    hybrid_search_agent = HybridSearchAgent(
        hybrid_search_service=hybrid_search_service,
    )

    status_agent = StatusAgent(
        status_service=status_service,
    )

    return GOOrchestrator(
        intent_agent=intent_agent,
        hybrid_search_agent=hybrid_search_agent,
        status_agent=status_agent,
    )


@router.post("")
def search_government_orders(
    request: SearchRequest,
) -> dict[str, Any]:
    """
    Perform direct hybrid Government Order search.

    This endpoint uses PostgreSQL metadata and Qdrant
    multilingual semantic retrieval.
    """

    try:
        with SessionFactory() as session:
            embedding_service = EmbeddingService()

            qdrant_client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=(
                    settings.QDRANT_COLLECTION_NAME
                ),
            )

            search_service = HybridSearchService(
                session=session,
                embedding_service=embedding_service,
                vector_store=vector_store,
            )

            response = search_service.search(
                query=request.query,
                limit=request.limit,
            )

            return response.model_dump(
                mode="json"
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/orchestrated")
def orchestrated_search(
    request: SearchRequest,
) -> dict[str, Any]:
    """
    Execute the complete multi-agent Government Order workflow.

    Workflow:

        Intent Agent
            ↓
        Hybrid Search Agent
            ↓
        Status Agent
            ↓
        Deterministic final aggregation
    """

    try:
        with SessionFactory() as session:
            orchestrator = build_orchestrator(
                session=session,
            )

            state = orchestrator.run(
                query=request.query,
            )

            return {
                "query": request.query,
                "intent": state.get(
                    "intent"
                ),
                "extracted_go_number": state.get(
                    "extracted_go_number"
                ),
                "search_results": state.get(
                    "search_results",
                    [],
                ),
                "status_results": state.get(
                    "status_results",
                    [],
                ),
                "final_results": state.get(
                    "final_results",
                    [],
                ),
                "workflow_completed": state.get(
                    "workflow_completed",
                    False,
                ),
                "errors": state.get(
                    "errors",
                    [],
                ),
            }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc