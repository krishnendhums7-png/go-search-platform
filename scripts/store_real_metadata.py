"""Store Module 5 metadata from real Kerala Government Orders."""

import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.document_service import DocumentService
from app.services.metadata_ingestion_service import (
    MetadataIngestionService,
)
from app.storage.mock_storage import MockStorageService
from app.storage.relational.session import SessionFactory


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


async def process_documents() -> None:
    """Extract and store metadata from all real Government Orders."""
    storage = MockStorageService()
    document_service = DocumentService(storage)

    pdf_files = sorted(RAW_DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    print("=" * 70)
    print("KERALA GO - MODULE 7")
    print("REAL METADATA → POSTGRESQL")
    print("=" * 70)
    print(f"PDF files: {len(pdf_files)}")
    print()

    success_count = 0
    failed_count = 0
    total_go_numbers = 0

    for pdf_path in pdf_files:
        print("-" * 70)
        print(f"Processing: {pdf_path.name}")

        try:
            with pdf_path.open("rb") as file:
                upload = UploadFile(
                    filename=pdf_path.name,
                    file=BytesIO(file.read()),
                    headers={
                        "content-type": "application/pdf",
                    },
                )

                document = await document_service.upload(upload)

            extraction_result = document_service.extract_identifiers(
                document.id,
            )

            with SessionFactory() as session:
                metadata_service = MetadataIngestionService(
                    session,
                )

                government_order_ids = (
                    metadata_service.store_extraction_result(
                        extraction_result,
                    )
                )

            go_count = len(extraction_result.go_numbers)
            total_go_numbers += go_count
            success_count += 1

            print(f"Document ID: {document.id}")
            print(f"GO numbers extracted: {go_count}")
            print(
                "GO records created/found: "
                f"{len(government_order_ids)}"
            )
            print(
                "Issue dates detected: "
                f"{len(extraction_result.issue_dates)}"
            )
            print(
                "Departments detected: "
                f"{len(extraction_result.departments)}"
            )
            print(
                "Relationships detected: "
                f"{len(extraction_result.relationships)}"
            )

        except (OSError, ValueError, RuntimeError) as exc:
            failed_count += 1
            print(f"FAILED: {exc}")

    print()
    print("=" * 70)
    print("MODULE 7 METADATA INGESTION COMPLETE")
    print("=" * 70)
    print(f"Successful PDFs: {success_count}")
    print(f"Failed PDFs:     {failed_count}")
    print(f"GO references:   {total_go_numbers}")
    print("=" * 70)


def main() -> None:
    """Run the real-data metadata ingestion."""
    asyncio.run(process_documents())


if __name__ == "__main__":
    main()