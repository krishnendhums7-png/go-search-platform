"""
Tests for Module 8 hybrid Government Order search.
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.models.embedding import SearchResult
from app.models.hybrid_search import (
    HybridSearchResponse,
)
from app.services.hybrid_search_service import (
    HybridSearchService,
)


@dataclass
class FakeGovernmentOrder:
    """Represent a fake Government Order metadata record."""

    document_id: object
    go_number: str
    issue_date: object = None
    department: str | None = None


class FakeRepository:
    """Fake repository for isolated hybrid-search tests."""

    def __init__(
        self,
        records: list[FakeGovernmentOrder],
    ) -> None:
        """Initialize the fake repository."""

        self.records = records

    def search_by_go_number(
        self,
        go_number: str,
    ) -> FakeGovernmentOrder | None:
        """Find a Government Order by exact number."""

        for record in self.records:
            if record.go_number == go_number:
                return record

        return None

    def get_by_document_id(
        self,
        document_id: object,
    ) -> list[FakeGovernmentOrder]:
        """Return records belonging to a document."""

        return [
            record
            for record in self.records
            if record.document_id == document_id
        ]


class FakeEmbeddingService:
    """Fake multilingual embedding service."""

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """Return a deterministic fake query vector."""

        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    """Fake Qdrant vector store."""

    def __init__(
        self,
        results: list[SearchResult],
    ) -> None:
        """Initialize the fake vector store."""

        self.results = results
        self.received_query_vector = None
        self.received_limit = None

    def search(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[SearchResult]:
        """Return predefined semantic results."""

        self.received_query_vector = query_vector
        self.received_limit = limit

        return self.results[:limit]


def create_service(
    records: list[FakeGovernmentOrder],
    semantic_results: list[SearchResult],
) -> HybridSearchService:
    """Create a hybrid search service with fake dependencies."""

    service = HybridSearchService.__new__(
        HybridSearchService
    )

    service._repository = FakeRepository(
        records
    )

    service._embedding_service = (
        FakeEmbeddingService()
    )

    service._vector_store = FakeVectorStore(
        semantic_results
    )

    return service


def create_search_result(
    document_id: str,
    chunk_id: str,
    text: str,
    score: float = 0.80,
    page_number: int = 1,
) -> SearchResult:
    """Create a deterministic semantic search result."""

    return SearchResult(
        document_id=document_id,
        chunk_id=chunk_id,
        page_number=page_number,
        text=text,
        score=score,
    )


def test_exact_go_number_search() -> None:
    """Exact GO-number queries should match PostgreSQL metadata."""

    document_id = uuid4()

    go = FakeGovernmentOrder(
        document_id=document_id,
        go_number="G.O.(Rt) No. 114/2025/ITD",
        issue_date="2025-06-10",
        department="Electronics & Information Technology Department",
    )

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-1",
        text=(
            "G.O.(Rt) No. 114/2025/ITD "
            "dated 10/06/2025"
        ),
    )

    service = create_service(
        records=[go],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "G.O.(Rt) No. 114/2025/ITD"
    )

    assert isinstance(
        response,
        HybridSearchResponse,
    )

    assert len(response.results) == 1

    result = response.results[0]

    assert result.go_number == (
        "G.O.(Rt) No. 114/2025/ITD"
    )

    assert result.metadata_match is True


def test_semantic_english_search() -> None:
    """English semantic queries should return Qdrant results."""

    document_id = uuid4()

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-english",
        text=(
            "Government Order regarding "
            "administrative reforms."
        ),
        score=0.84,
    )

    service = create_service(
        records=[],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "Government Order about administrative reforms"
    )

    assert len(response.results) == 1

    result = response.results[0]

    assert result.text == (
        "Government Order regarding "
        "administrative reforms."
    )

    assert result.semantic_score == 0.84


def test_semantic_malayalam_search() -> None:
    """Malayalam semantic queries should return Qdrant results."""

    document_id = uuid4()

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-malayalam",
        text="സർക്കാർ ഉത്തരവ് സംബന്ധിച്ച വിവരങ്ങൾ.",
        score=0.82,
    )

    service = create_service(
        records=[],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "സർക്കാർ ഉത്തരവ്"
    )

    assert len(response.results) == 1

    assert response.results[0].text == (
        "സർക്കാർ ഉത്തരവ് സംബന്ധിച്ച വിവരങ്ങൾ."
    )


def test_metadata_match_adds_score() -> None:
    """Direct metadata matches should receive the ranking boost."""

    document_id = uuid4()

    go = FakeGovernmentOrder(
        document_id=document_id,
        go_number="G.O.(P) No. 27/2026/FIN",
    )

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-score",
        text="G.O.(P) No. 27/2026/FIN",
        score=0.80,
    )

    service = create_service(
        records=[go],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "G.O.(P) No. 27/2026/FIN"
    )

    result = response.results[0]

    assert result.metadata_match is True

    assert result.semantic_score == 0.80

    assert result.combined_score == pytest.approx(
        1.00
    )


def test_metadata_enrichment() -> None:
    """Semantic results should be enriched with PostgreSQL metadata."""

    document_id = uuid4()

    go = FakeGovernmentOrder(
        document_id=document_id,
        go_number="G.O.(P) No. 27/2026/FIN",
        issue_date="2026-02-20",
        department="Finance Department",
    )

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-metadata",
        text=(
            "G.O.(P) No. 27/2026/FIN "
            "Dated 20-02-2026"
        ),
    )

    service = create_service(
        records=[go],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "Government Order about finance"
    )

    result = response.results[0]

    assert result.go_number == (
        "G.O.(P) No. 27/2026/FIN"
    )

    assert result.issue_date == "2026-02-20"

    assert result.department == (
        "Finance Department"
    )


def test_multiple_go_records_in_one_document() -> None:
    """
    Metadata selection should use the GO number present
    in the retrieved text instead of blindly selecting
    the first database record.
    """

    document_id = uuid4()

    go_one = FakeGovernmentOrder(
        document_id=document_id,
        go_number="G.O.(Rt) No. 114/2025/ITD",
        issue_date="2025-06-10",
        department="IT Department",
    )

    go_two = FakeGovernmentOrder(
        document_id=document_id,
        go_number="G.O.(Rt) No. 264/2025/ITD",
        issue_date="2025-12-04",
        department="IT Department",
    )

    semantic_result = create_search_result(
        document_id=str(document_id),
        chunk_id="chunk-multiple",
        text=(
            "G.O. (Rt) No.264/2025/ITD "
            "dated.04-12-2025"
        ),
    )

    service = create_service(
        records=[go_one, go_two],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "Government Order about IT"
    )

    result = response.results[0]

    assert result.go_number == (
        "G.O.(Rt) No. 264/2025/ITD"
    )

    assert result.issue_date == "2025-12-04"


def test_duplicate_chunks_are_removed() -> None:
    """Duplicate Qdrant chunks should appear only once."""

    document_id = str(uuid4())

    first = create_search_result(
        document_id=document_id,
        chunk_id="duplicate-chunk",
        text="Government Order text",
        score=0.90,
    )

    second = create_search_result(
        document_id=document_id,
        chunk_id="duplicate-chunk",
        text="Government Order text",
        score=0.80,
    )

    service = create_service(
        records=[],
        semantic_results=[
            first,
            second,
        ],
    )

    response = service.search(
        "Government Order"
    )

    chunk_ids = [
        result.chunk_id
        for result in response.results
    ]

    assert chunk_ids.count(
        "duplicate-chunk"
    ) == 1


def test_result_limit_is_respected() -> None:
    """The final response should respect the requested limit."""

    document_id = str(uuid4())

    semantic_results = [
        create_search_result(
            document_id=document_id,
            chunk_id=f"chunk-{index}",
            text=f"Government Order {index}",
            score=0.90 - index * 0.01,
        )
        for index in range(5)
    ]

    service = create_service(
        records=[],
        semantic_results=semantic_results,
    )

    response = service.search(
        "Government Orders",
        limit=2,
    )

    assert len(response.results) == 2


def test_empty_query_is_rejected() -> None:
    """An empty search query should raise ValueError."""

    service = create_service(
        records=[],
        semantic_results=[],
    )

    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        service.search("   ")


def test_invalid_limit_is_rejected() -> None:
    """A search limit below one should raise ValueError."""

    service = create_service(
        records=[],
        semantic_results=[],
    )

    with pytest.raises(
        ValueError,
        match="Search limit must be at least 1",
    ):
        service.search(
            "Government Order",
            limit=0,
        )


def test_invalid_document_id_does_not_crash() -> None:
    """
    Invalid semantic document IDs should not cause the
    hybrid search service to fail.
    """

    semantic_result = create_search_result(
        document_id="not-a-valid-uuid",
        chunk_id="chunk-invalid-id",
        text="Government Order text",
    )

    service = create_service(
        records=[],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "Government Order"
    )

    assert len(response.results) == 1

    result = response.results[0]

    assert result.document_id == (
        "not-a-valid-uuid"
    )

    assert result.go_number is None


def test_retrieval_only_preserves_original_text() -> None:
    """
    Hybrid search must return the retrieved text unchanged.

    The service must not generate or paraphrase legal text.
    """

    original_text = (
        "G.O.(P)No.27/2026/FIN "
        "Dated,Thiruvananthapuram, 20-02-2026"
    )

    semantic_result = create_search_result(
        document_id=str(uuid4()),
        chunk_id="chunk-original",
        text=original_text,
        score=0.85,
    )

    service = create_service(
        records=[],
        semantic_results=[semantic_result],
    )

    response = service.search(
        "Finance Government Order"
    )

    assert response.results[0].text == (
        original_text
    )