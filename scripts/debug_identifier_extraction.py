"""
Debug Government Order identifier extraction.
"""

import sys
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.text_extraction import (
    ExtractedPage,
    TextExtractionResult,
)
from app.services.identifier_extractor import (
    IdentifierExtractor,
)


PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "G.O.(P) No.4_2026_P&ARD_16_08_03_2026.pdf"
)


def main() -> None:
    """Extract and display identifiers from the test PDF."""

    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        return

    pages: list[ExtractedPage] = []

    with fitz.open(PDF_PATH) as document:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=page.get_text(),
                )
            )

        page_count = len(pages)

    text_result = TextExtractionResult(
        document_id="debug-document",
        source_type="debug",
        page_count=page_count,
        pages=pages,
        raw_text_object_keys=[],
    )

    extractor = IdentifierExtractor()

    result = extractor.extract(text_result)

    print("=" * 70)
    print("IDENTIFIER EXTRACTION DEBUG")
    print("=" * 70)

    print(f"\nPDF: {PDF_PATH.name}")
    print(f"Pages: {page_count}")

    print("\nGO NUMBERS:")
    for identifier in result.go_numbers:
        print(
            f"  {identifier.value}"
            f" | confidence={identifier.confidence}"
            f" | method={identifier.extraction_method}"
        )

    print("\nDATES:")
    for identifier in result.issue_dates:
        print(
            f"  {identifier.value}"
            f" | confidence={identifier.confidence}"
            f" | method={identifier.extraction_method}"
        )

    print("\nDEPARTMENTS:")
    for identifier in result.departments:
        print(
            f"  {identifier.value}"
            f" | confidence={identifier.confidence}"
            f" | method={identifier.extraction_method}"
        )

    print("\nRELATIONSHIPS:")
    for relationship in result.relationships:
        print(
            f"  {relationship.relationship_type}"
            f" | phrase={relationship.matched_phrase}"
            f" | page={relationship.page_number}"
            f" | references="
            f"{relationship.reference_ordinals}"
        )

    print("\nREVIEW FLAGS:")
    for flag in result.review_flags:
        print(f"  {flag}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()