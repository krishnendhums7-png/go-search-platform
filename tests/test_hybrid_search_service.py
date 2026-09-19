"""Tests for hybrid Government Order search."""

from uuid import uuid4

import pytest

from app.models.hybrid_search import (
    HybridSearchResponse,
)
from app.services.hybrid_search_service import (
    HybridSearchService,
)


def test_empty_query_is_rejected():
    """Empty queries should be rejected."""

    service = HybridSearchService.__new__(
        HybridSearchService
    )

    with pytest.raises(ValueError):
        service.search("")


def test_invalid_limit_is_rejected():
    """Invalid result limits should be rejected."""

    service = HybridSearchService.__new__(
        HybridSearchService
    )

    with pytest.raises(ValueError):
        service.search(
            query="pension",
            limit=0,
        )


def test_go_number_pattern_matches():
    """Explicit GO numbers should be recognized."""

    query = (
        "G.O.(Rt) No. 24/2026/ITD"
    )

    matches = list(
        HybridSearchService.GO_NUMBER_PATTERN.finditer(
            query
        )
    )

    assert len(matches) == 1

    match = matches[0]

    assert match.group("category") == "Rt"
    assert match.group("number") == "24"
    assert match.group("year") == "2026"
    assert match.group("department") == "ITD"


def test_go_number_pattern_matches_lowercase():
    """GO number matching should be case insensitive."""

    query = (
        "g.o.(rt) no. 24/2026/itd"
    )

    matches = list(
        HybridSearchService.GO_NUMBER_PATTERN.finditer(
            query
        )
    )

    assert len(matches) == 1


def test_go_number_pattern_does_not_match_invalid_year():
    """Invalid GO year formats should not match."""

    query = (
        "G.O.(Rt) No. 24/26/ITD"
    )

    matches = list(
        HybridSearchService.GO_NUMBER_PATTERN.finditer(
            query
        )
    )

    assert matches == []