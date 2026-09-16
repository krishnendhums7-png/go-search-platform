"""Tests for multilingual semantic search."""

import pytest

from app.models.embedding import SearchResult
from app.services.semantic_search_service import (
    SemanticSearchService,
)


class FakeEmbeddingService:
    """Fake embedding service for unit testing."""

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """Return a deterministic query vector."""
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    """Fake Qdrant vector store for unit testing."""

    def search(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[SearchResult]:
        """Return deterministic search results."""
        assert query_vector == [0.1, 0.2, 0.3]

        return [
            SearchResult(
                document_id="test-document",
                page_number=1,
                chunk_id="test-document_1",
                text="Government Order test text.",
                score=0.91,
            )
        ][:limit]


def create_service() -> SemanticSearchService:
    """Create a semantic search service with test dependencies."""
    return SemanticSearchService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )


def test_search_returns_results() -> None:
    """Test that semantic search returns ranked results."""
    service = create_service()

    results = service.search(
        query="pension Government Order",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].document_id == "test-document"
    assert results[0].page_number == 1
    assert results[0].text == "Government Order test text."
    assert results[0].score == 0.91


def test_search_rejects_empty_query() -> None:
    """Test that an empty query is rejected."""
    service = create_service()

    with pytest.raises(ValueError):
        service.search("")


def test_search_rejects_invalid_limit() -> None:
    """Test that an invalid result limit is rejected."""
    service = create_service()

    with pytest.raises(ValueError):
        service.search(
            query="pension",
            limit=0,
        )
