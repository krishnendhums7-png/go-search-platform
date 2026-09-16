"""Data models for multilingual embedding and vector search."""

from pydantic import BaseModel, Field


class EmbeddingChunk(BaseModel):
    """Represent a Government Order text chunk and its embedding."""

    document_id: str
    page_number: int
    chunk_id: str
    text: str
    vector: list[float] = Field(default_factory=list)


class EmbeddingResult(BaseModel):
    """Represent the embedding result for a Government Order."""

    document_id: str
    model_name: str
    vector_dimension: int
    chunks: list[EmbeddingChunk]


class SearchResult(BaseModel):
    """Represent a semantic search result."""

    document_id: str
    page_number: int
    chunk_id: str
    text: str
    score: float