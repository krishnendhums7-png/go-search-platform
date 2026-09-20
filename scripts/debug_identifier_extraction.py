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


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def select_pdf() -> Path | None:
    """Display available PDFs and let the user select one."""

    pdf_files = sorted(RAW_DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {RAW_DATA_DIR}")
        return None

    print("=" * 70)
    print("AVAILABLE GOVERNMENT ORDERS")
    print("=" * 70)

    for index, pdf_path in enumerate(pdf_files, start=1):
        print(f"{index}. {pdf_path.name}")

    print()

    while True:
        choice = input(
            "Enter PDF number to debug: "
        ).strip()

        try:
            selected_index = int(choice)
        except ValueError:
            print("Please enter a valid number.")
            continue

        if 1 <= selected_index <= len(pdf_files):
            return pdf_files[selected_index - 1]

        print(
            f"Please enter a number between 1 and "
            f"{len(pdf_files)}."
        )


def main() -> None:
    """Extract and display identifiers from a selected PDF."""

    pdf_path = select_pdf()

    if pdf_path is None:
        return

    pages: list[ExtractedPage] = []

    with fitz.open(pdf_path) as document:
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

    print()
    print("=" * 70)
    print("IDENTIFIER EXTRACTION DEBUG")
    print("=" * 70)

    print(f"\nPDF: {pdf_path.name}")
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

    print("\nREFERENCES:")
    for reference in result.references:
        print(
            f"  {reference.ordinal}"
            f". {reference.go_number}"
            f" | page={reference.page_number}"
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