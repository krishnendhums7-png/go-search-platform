"""Qdrant vector storage for Government Order embeddings."""

from uuid import UUID
from uuid import uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance
from qdrant_client.models import PointStruct
from qdrant_client.models import VectorParams

from app.models.embedding import EmbeddingChunk
from app.models.embedding import SearchResult


QDRANT_NAMESPACE = UUID(
    "00000000-0000-0000-0000-000000000001"
)


def _point_id(chunk_id: str) -> str:
    """Create a deterministic Qdrant point ID."""
    return str(
        uuid5(
            QDRANT_NAMESPACE,
            chunk_id,
        )
    )


class QdrantVectorStore:
    """Store and search Government Order embeddings."""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "government_orders",
    ) -> None:
        """Initialize the Qdrant vector store."""
        self._client = client
        self._collection_name = collection_name

    def create_collection(
        self,
        vector_dimension: int,
    ) -> None:
        """Create the Qdrant collection if it does not exist."""
        collections = (
            self._client
            .get_collections()
            .collections
        )

        names = {
            item.name
            for item in collections
        }

        if self._collection_name not in names:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=vector_dimension,
                    distance=Distance.COSINE,
                ),
            )

    def upsert(
        self,
        chunks: list[EmbeddingChunk],
    ) -> None:
        """Insert or update embedding chunks in Qdrant."""
        if not chunks:
            return

        self.create_collection(
            len(chunks[0].vector)
        )

        points = [
            PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=chunk.vector,
                payload={
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                },
            )
            for chunk in chunks
        ]

        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search Qdrant using vector similarity."""
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            limit=limit,
        )

        return [
            SearchResult(
                document_id=str(
                    point.payload["document_id"]
                ),
                page_number=int(
                    point.payload["page_number"]
                ),
                chunk_id=str(
                    point.payload["chunk_id"]
                ),
                text=str(
                    point.payload["text"]
                ),
                score=float(point.score),
            )
            for point in response.points
        ]