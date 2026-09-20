"""
Models for hybrid Government Order search.
"""

from pydantic import BaseModel, Field


class HybridSearchResult(BaseModel):
    """Represent a result returned by hybrid search."""

    document_id: str

    # Backward-compatible GO number field.
    #
    # For an exact GO query this represents the GO that
    # matched the user's query. Existing agents can continue
    # using this field.
    go_number: str | None = None

    # Actual Government Order represented by the retrieved
    # document/chunk.
    source_go_number: str | None = None

    # Government Order number that matched the user's query.
    matched_go_number: str | None = None

    issue_date: str | None = None
    department: str | None = None

    page_number: int
    chunk_id: str
    text: str

    semantic_score: float = 0.0
    metadata_match: bool = False
    combined_score: float = 0.0

    relationship_type: str | None = None
    matched_phrase: str | None = None


class HybridSearchResponse(BaseModel):
    """Represent the complete hybrid search response."""

    query: str

    results: list[HybridSearchResult] = Field(
        default_factory=list
    )