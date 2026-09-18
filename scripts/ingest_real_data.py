"""Process real Kerala Government Order PDFs through Modules 2–5."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.storage.mock_storage import MockStorageService


RAW_DATA_DIR = Path("data/raw")
OUTPUT_FILE = Path(
    "data/processed/real_go_results.json"
)


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

    # ---------------------------------------------------------
    # Module 2: Upload PDF
    # ---------------------------------------------------------

    with pdf_path.open("rb") as file:
        upload = UploadFile(
            filename=pdf_path.name,
            file=file,
            headers={
                "content-type": "application/pdf"
            },
        )

        document = await document_service.upload(
            upload
        )

    # ---------------------------------------------------------
    # Module 3: PDF Classification
    # ---------------------------------------------------------

    classification = document_service.classify(
        document.id
    )

    print(f"Document ID: {document.id}")
    print(f"PDF type: {classification.pdf_type}")
    print(f"Pages: {classification.page_count}")
    print(
        "Pages with text: "
        f"{classification.pages_with_text}"
    )
    print(
        "Processing path: "
        f"{classification.processing_path}"
    )

    # ---------------------------------------------------------
    # Module 4: Text Extraction / OCR
    # ---------------------------------------------------------

    text_result = document_service.extract_text(
        document.id
    )

    total_characters = sum(
        len(page.text)
        for page in text_result.pages
    )

    print(
        f"Extracted characters: "
        f"{total_characters}"
    )

    # ---------------------------------------------------------
    # Module 5: Identifier & Relationship Extraction
    # ---------------------------------------------------------

    identifiers = document_service.extract_identifiers(
        document.id
    )

    print(
        f"GO numbers: "
        f"{len(identifiers.go_numbers)}"
    )

    print(
        f"Issue dates: "
        f"{len(identifiers.issue_dates)}"
    )

    print(
        f"Departments: "
        f"{len(identifiers.departments)}"
    )

    print(
        f"GO references: "
        f"{len(identifiers.references)}"
    )

    print(
        f"Relationships: "
        f"{len(identifiers.relationships)}"
    )

    # ---------------------------------------------------------
    # Display extracted GO numbers
    # ---------------------------------------------------------

    for item in identifiers.go_numbers:
        print(
            f"  GO: {item.value}"
        )

    # ---------------------------------------------------------
    # Display extracted references
    # ---------------------------------------------------------

    for reference in identifiers.references:
        print(
            "  Reference "
            f"{reference.ordinal}: "
            f"{reference.go_number}"
        )

    # ---------------------------------------------------------
    # Display extracted relationships
    # ---------------------------------------------------------

    for relationship in identifiers.relationships:
        print(
            "  Relationship: "
            f"{relationship.relationship_type.value}"
        )

        print(
            "    Phrase: "
            f"{relationship.matched_phrase}"
        )

        print(
            "    Page: "
            f"{relationship.page_number}"
        )

        print(
            "    Reference ordinals: "
            f"{relationship.reference_ordinals}"
        )

    # ---------------------------------------------------------
    # Convert result into JSON-serializable structure
    # ---------------------------------------------------------

    return {
        "document_id": str(
            document.id
        ),
        "filename": pdf_path.name,
        "pdf_type": str(
            classification.pdf_type
        ),
        "processing_path": str(
            classification.processing_path
        ),
        "page_count": text_result.page_count,
        "pages_with_text": (
            classification.pages_with_text
        ),

        # -----------------------------------------------------
        # Page-wise extracted text
        # -----------------------------------------------------

        "pages": [
            {
                "page_number": page.page_number,
                "text": page.text,
            }
            for page in text_result.pages
        ],

        # -----------------------------------------------------
        # Module 5: GO numbers
        # -----------------------------------------------------

        "go_numbers": [
            item.model_dump()
            for item in identifiers.go_numbers
        ],

        # -----------------------------------------------------
        # Module 5: Issue dates
        # -----------------------------------------------------

        "issue_dates": [
            item.model_dump()
            for item in identifiers.issue_dates
        ],

        # -----------------------------------------------------
        # Module 5: Departments
        # -----------------------------------------------------

        "departments": [
            item.model_dump()
            for item in identifiers.departments
        ],

        # -----------------------------------------------------
        # Module 5: Numbered GO references
        #
        # Example:
        #
        # 1 -> G.O.(Rt) No. 114/2025/ITD
        # 2 -> G.O.(Rt) No. 151/2025/ITD
        #
        # -----------------------------------------------------

        "references": [
            item.model_dump()
            for item in identifiers.references
        ],

        # -----------------------------------------------------
        # Module 5: Legal relationships
        #
        # Example:
        #
        # AMENDS
        # reference_ordinals: [1, 2, 4]
        #
        # -----------------------------------------------------

        "relationships": [
            item.model_dump()
            for item in identifiers.relationships
        ],

        # -----------------------------------------------------
        # Manual review flags
        # -----------------------------------------------------

        "review_flags": identifiers.review_flags,
    }


async def main() -> None:
    """Process all real Government Order PDFs."""

    # ---------------------------------------------------------
    # Locate PDFs
    # ---------------------------------------------------------

    pdf_files = sorted(
        RAW_DATA_DIR.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            "No PDF files found in data/raw."
        )

    # ---------------------------------------------------------
    # Create output directory
    # ---------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Module 2 storage
    #
    # MockStorageService is used for the current local
    # ingestion/testing pipeline.
    # ---------------------------------------------------------

    storage = MockStorageService()

    document_service = DocumentService(
        storage_service=storage
    )

    results: list[dict] = []

    print(
        f"Found {len(pdf_files)} PDF files."
    )

    # ---------------------------------------------------------
    # Process each PDF
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Save complete results
    # ---------------------------------------------------------

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "REAL DATA PROCESSING COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Successfully processed: "
        f"{len(results)}/{len(pdf_files)}"
    )

    print(
        f"Results saved to: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    asyncio.run(main())