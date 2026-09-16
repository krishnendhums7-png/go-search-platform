"""Generate multilingual embeddings using multilingual-e5-large."""

from sentence_transformers import SentenceTransformer

from app.models.embedding import EmbeddingChunk, EmbeddingResult


MODEL_NAME = "intfloat/multilingual-e5-large"


class EmbeddingService:
    """Generate multilingual semantic representations."""

    def __init__(
        self,
        model: SentenceTransformer | None = None,
    ) -> None:
        """Initialize the embedding model.

        Args:
            model: Optional model instance for testing.
        """
        self._model = model or SentenceTransformer(MODEL_NAME)

    def embed_documents(
        self,
        document_id: str,
        pages: list[tuple[int, str]],
    ) -> EmbeddingResult:
        """Generate embeddings for extracted document pages.

        Args:
            document_id: Government Order document identifier.
            pages: Page number and extracted text pairs.

        Returns:
            EmbeddingResult containing document vectors.
        """
        texts = [f"passage: {text}" for _, text in pages]

        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
        )

        chunks = [
            EmbeddingChunk(
                document_id=document_id,
                page_number=page_number,
                chunk_id=f"{document_id}_{page_number}",
                text=text,
                vector=vector.tolist(),
            )
            for (page_number, text), vector in zip(pages, vectors)
        ]

        return EmbeddingResult(
            document_id=document_id,
            model_name=MODEL_NAME,
            vector_dimension=len(chunks[0].vector) if chunks else 0,
            chunks=chunks,
        )

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a citizen search query.

        Args:
            query: Malayalam, English, or code-mixed query.

        Returns:
            Normalized query vector.
        """
        vector = self._model.encode(
            f"query: {query}",
            normalize_embeddings=True,
        )

        return vector.tolist()