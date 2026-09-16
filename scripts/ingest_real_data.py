"""Process real Kerala Government Order PDFs through Modules 2–5."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.storage.mock_storage import MockStorageService


RAW_DATA_DIR = Path("data/raw")
OUTPUT_FILE = Path("data/processed/real_go_results.json")


async def process_pdf(
    document_service: DocumentService,
    pdf_path: Path,
) -> dict:
    """Process one Government Order through the ingestion pipeline.

    Args:
        document_service: Document service instance.
        pdf_path: Source PDF path.

    Returns:
        Extracted document information.
    """
    print(f"\n{'=' * 70}")
    print(f"Processing: {pdf_path.name}")
    print("=" * 70)

    with pdf_path.open("rb") as file:
        upload = UploadFile(
            filename=pdf_path.name,
            file=file,
            headers={"content-type": "application/pdf"},
        )

        document = await document_service.upload(upload)

    classification = document_service.classify(document.id)

    print(f"Document ID: {document.id}")
    print(f"PDF type: {classification.pdf_type}")
    print(f"Pages: {classification.page_count}")
    print(f"Pages with text: {classification.pages_with_text}")
    print(f"Processing path: {classification.processing_path}")

    text_result = document_service.extract_text(document.id)

    total_characters = sum(
        len(page.text)
        for page in text_result.pages
    )

    print(f"Extracted characters: {total_characters}")

    identifiers = document_service.extract_identifiers(
        document.id
    )

    print(f"GO numbers: {len(identifiers.go_numbers)}")
    print(f"Issue dates: {len(identifiers.issue_dates)}")
    print(f"Departments: {len(identifiers.departments)}")
    print(f"Relationships: {len(identifiers.relationships)}")

    for item in identifiers.go_numbers:
        print(f"  GO: {item.value}")

    return {
        "document_id": str(document.id),
        "filename": pdf_path.name,
        "pdf_type": str(classification.pdf_type),
        "processing_path": str(
            classification.processing_path
        ),
        "page_count": text_result.page_count,
        "pages_with_text": classification.pages_with_text,
        "pages": [
            {
                "page_number": page.page_number,
                "text": page.text,
            }
            for page in text_result.pages
        ],
        "go_numbers": [
            item.model_dump()
            for item in identifiers.go_numbers
        ],
        "issue_dates": [
            item.model_dump()
            for item in identifiers.issue_dates
        ],
        "departments": [
            item.model_dump()
            for item in identifiers.departments
        ],
        "relationships": [
            item.model_dump()
            for item in identifiers.relationships
        ],
        "review_flags": identifiers.review_flags,
    }


async def main() -> None:
    """Process all real Government Order PDFs."""
    pdf_files = sorted(
        RAW_DATA_DIR.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            "No PDF files found in data/raw."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    storage = MockStorageService()

    document_service = DocumentService(
        storage_service=storage
    )

    results = []

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_path in pdf_files:
        try:
            result = await process_pdf(
                document_service,
                pdf_path,
            )
            results.append(result)

        except Exception as exc:
            print(
                f"ERROR processing "
                f"{pdf_path.name}: {exc}"
            )

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("REAL DATA PROCESSING COMPLETE")
    print("=" * 70)
    print(
        f"Successfully processed: "
        f"{len(results)}/{len(pdf_files)}"
    )
    print(f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())