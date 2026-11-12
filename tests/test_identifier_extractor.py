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
    ExtractionConfidence,
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
        "G.O.(P) No. 45/2024/Fin "
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

    assert (
        result.issue_dates[0].confidence
        == ExtractionConfidence.HIGH
    )

    assert (
        result.issue_dates[0].extraction_method
        == "GO_HEADER_PRIMARY"
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


def test_extract_go_reference() -> None:
    """Numbered Government Order reference should be extracted."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        "1 G.O.(Rt) No. 114/2025/ITD"
    )

    result = extractor.extract(text_result)

    assert len(result.references) == 1
    assert result.references[0].ordinal == 1

    assert (
        result.references[0].go_number
        == "G.O.(Rt) No. 114/2025/ITD"
    )


def test_extract_multiple_go_references() -> None:
    """Multiple numbered GO references should be extracted."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        """
        1 G.O.(Rt) No. 114/2025/ITD
        2 G.O.(Rt) No. 151/2025/ITD
        3 G.O.(Rt) No. 228/2025/ITD
        4 G.O.(Rt) No. 264/2025/ITD
        """
    )

    result = extractor.extract(text_result)

    assert len(result.references) == 4

    assert result.references[0].ordinal == 1
    assert result.references[1].ordinal == 2
    assert result.references[2].ordinal == 3
    assert result.references[3].ordinal == 4


def test_modified_relationship_extracts_ordinals() -> None:
    """Modified GO references should resolve their ordinal numbers."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        """
        G.O.(Rt) No. 24/2026/ITD

        1 G.O.(Rt) No. 114/2025/ITD
        2 G.O.(Rt) No. 151/2025/ITD
        3 G.O.(Rt) No. 228/2025/ITD
        4 G.O.(Rt) No. 264/2025/ITD

        The Government Orders read as 1st, 2nd and 4th
        papers above are hereby modified.
        """
    )

    result = extractor.extract(text_result)

    amends_relationships = [
        relationship
        for relationship in result.relationships
        if relationship.relationship_type
        == RelationshipType.AMENDS
    ]

    assert len(amends_relationships) == 1

    relationship = amends_relationships[0]

    assert relationship.matched_phrase == "hereby modified"

    assert relationship.reference_ordinals == [
        1,
        2,
        4,
    ]


def test_read_as_papers_is_not_relationship() -> None:
    """Ordinary 'read as' paper references are not relationships."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        """
        Read 1 G.O.(Rt) No. 114/2025/ITD
        2 G.O.(Rt) No. 151/2025/ITD

        The Government Orders read as 1st and 2nd
        papers above.
        """
    )

    result = extractor.extract(text_result)

    assert result.relationships == []


def test_primary_go_date_excludes_referenced_dates() -> None:
    """Only the current GO issue date should be returned."""

    extractor = IdentifierExtractor()

    text_result = create_text_result(
        """
        G.O.(Rt)No.24/2026/ITD
        Dated,Thiruvananthapuram, 23-02-2026

        Read 1 G.O (Rt) No. 114/2025/ITD dated 10/06/2025
        2 G.O (Rt) No. 151/2025/ITD dated 02/07/2025
        3 G.O (Rt) No. 228/2025/ITD dated 29/09/2025
        4 G.O (Rt) No. 264/2025/ITD dated 04/12/2025

        Letter No. CB/9/2024-KSITM dated 17-12-2025.
        """
    )

    result = extractor.extract(text_result)

    assert len(result.issue_dates) == 1

    assert (
        result.issue_dates[0].value
        == "23-02-2026"
    )

    assert (
        result.issue_dates[0].confidence
        == ExtractionConfidence.HIGH
    )

    assert (
        result.issue_dates[0].extraction_method
        == "GO_HEADER_PRIMARY"
    )