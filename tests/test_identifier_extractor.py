"""
Tests for Module 5 identifier extraction.
"""

from app.models.text_extraction import (
    ExtractedPage,
)
from app.models.text_extraction import (
    TextExtractionResult,
)
from app.models.identifier_extraction import (
    RelationshipType,
)
from app.services.identifier_extractor import (
    IdentifierExtractor,
)


def create_text_result(
    text: str,
) -> TextExtractionResult:
    """Create a test text extraction result."""

    return TextExtractionResult(
        document_id="test-document",
        source_type="NATIVE",
        page_count=1,
        pages=[
            ExtractedPage(
                page_number=1,
                text=text,
            )
        ],
        raw_text_object_keys=[],
    )


def test_extract_go_number() -> None:
    """GO number should be extracted."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "G.O.(P) No. 45/2024/Fin"
    )

    result = extractor.extract(
        text_result
    )

    assert len(result.go_numbers) == 1

    assert (
        result.go_numbers[0].value
        == "G.O.(P) No. 45/2024/Fin"
    )


def test_extract_date() -> None:
    """Issue date should be extracted."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "Dated: 15.08.2024"
    )

    result = extractor.extract(
        text_result
    )

    assert len(result.issue_dates) == 1

    assert (
        result.issue_dates[0].value
        == "15.08.2024"
    )


def test_extract_department() -> None:
    """Known department should be extracted."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "Finance Department Government of Kerala"
    )

    result = extractor.extract(
        text_result
    )

    assert len(result.departments) == 1

    assert (
        result.departments[0].value
        == "Finance Department"
    )


def test_extract_amendment_relationship() -> None:
    """Amendment phrase should be detected."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "This Government Order amends "
        "the earlier order."
    )

    result = extractor.extract(
        text_result
    )

    relationship_types = {
        relationship.relationship_type
        for relationship in result.relationships
    }

    assert (
        RelationshipType.AMENDS
        in relationship_types
    )


def test_extract_supersedes_relationship() -> None:
    """Supersession phrase should be detected."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "This order is issued in "
        "supersession of the previous order."
    )

    result = extractor.extract(
        text_result
    )

    relationship_types = {
        relationship.relationship_type
        for relationship in result.relationships
    }

    assert (
        RelationshipType.SUPERSEDES
        in relationship_types
    )


def test_extract_cancellation_relationship() -> None:
    """Cancellation phrase should be detected."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "The earlier Government Order "
        "stands cancelled."
    )

    result = extractor.extract(
        text_result
    )

    relationship_types = {
        relationship.relationship_type
        for relationship in result.relationships
    }

    assert (
        RelationshipType.CANCELS
        in relationship_types
    )


def test_extract_read_as_relationship() -> None:
    """Read-as phrase should be detected."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "The following provision shall "
        "be read as follows."
    )

    result = extractor.extract(
        text_result
    )

    relationship_types = {
        relationship.relationship_type
        for relationship in result.relationships
    }

    assert (
        RelationshipType.READ_AS
        in relationship_types
    )


def test_extract_malayalam_relationship() -> None:
    """Malayalam relationship phrase should be detected."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "ഈ ഉത്തരവ് ഭേദഗതി ചെയ്യുന്നു"
    )

    result = extractor.extract(
        text_result
    )

    relationship_types = {
        relationship.relationship_type
        for relationship in result.relationships
    }

    assert (
        RelationshipType.AMENDS
        in relationship_types
    )