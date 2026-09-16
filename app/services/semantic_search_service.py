
"""Semantic search service for Kerala Government Orders."""

from app.models.embedding import SearchResult
from app.services.embedding_service import EmbeddingService
from app.storage.vector.qdrant_client import QdrantVectorStore


class SemanticSearchService:
    """Perform multilingual semantic search over Government Orders."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
    ) -> None:
        """Initialize the semantic search service.

        Args:
            embedding_service: Service used to embed search queries.
            vector_store: Qdrant vector storage service.
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search Government Orders using a multilingual query.

        Args:
            query: English, Malayalam, or code-mixed query.
            limit: Maximum number of results.

        Returns:
            Ranked semantic search results.

        Raises:
            ValueError: If the query is empty or limit is invalid.
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if limit < 1:
            raise ValueError("Search limit must be at least 1.")

        query_vector = self._embedding_service.embed_query(
            query.strip()
        )

        return self._vector_store.search(
            query_vector=query_vector,
            limit=limit,
        )

