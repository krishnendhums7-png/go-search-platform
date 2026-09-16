"""Unit tests for multilingual embedding indexing."""

import numpy as np

from app.services.embedding_service import EmbeddingService


class FakeEmbeddingModel:
    """Provide deterministic embeddings for unit tests."""

    def encode(
        self,
        texts: list[str] | str,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        """Return deterministic vectors.

        Args:
            texts: Input text or texts.
            normalize_embeddings: Whether to normalize vectors.

        Returns:
            Test vectors.
        """
        if isinstance(texts, str):
            return np.array([0.1, 0.2, 0.3])

        return np.array([[0.1, 0.2, 0.3] for _ in texts])


def test_embed_documents() -> None:
    """Test document embedding."""
    service = EmbeddingService(model=FakeEmbeddingModel())

    result = service.embed_documents(
        document_id="go-001",
        pages=[
            (1, "Government order regarding education."),
            (2, "വിദ്യാഭ്യാസവുമായി ബന്ധപ്പെട്ട സർക്കാർ ഉത്തരവ്."),
        ],
    )

    assert result.document_id == "go-001"
    assert result.model_name == "intfloat/multilingual-e5-large"
    assert result.vector_dimension == 3
    assert len(result.chunks) == 2
    assert result.chunks[0].chunk_id == "go-001_1"


def test_embed_query() -> None:
    """Test query embedding."""
    service = EmbeddingService(model=FakeEmbeddingModel())

    vector = service.embed_query(
        "വിദ്യാഭ്യാസ സർക്കാർ ഉത്തരവ്"
    )

    assert vector == [0.1, 0.2, 0.3]