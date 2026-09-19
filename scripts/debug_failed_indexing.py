"""Debug Government Order identifier extraction."""

import asyncio
import io
import sys
from pathlib import Path

from fastapi import UploadFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.document_service import DocumentService
from app.storage.mock_storage import MockStorageService


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


async def main() -> None:
    """Show extracted identifiers for all PDFs."""
    storage = MockStorageService()

    document_service = DocumentService(
        storage_service=storage
    )

    for pdf_path in sorted(
        RAW_DATA_DIR.glob("*.pdf")
    ):
        print("=" * 80)
        print(pdf_path.name)
        print("=" * 80)

        try:
            with pdf_path.open("rb") as file:
                upload = UploadFile(
                    filename=pdf_path.name,
                    file=io.BytesIO(file.read()),
                    headers={
                        "content-type": "application/pdf"
                    },
                )

                document = (
                    await document_service.upload(
                        upload
                    )
                )

            text_result = (
                document_service.extract_text(
                    document.id
                )
            )

            full_text = "\n".join(
                page.text
                for page in text_result.pages
            )

            result = (
                document_service.extract_identifiers(
                    document.id
                )
            )

            print(
                "Extracted GO numbers:"
            )

            for identifier in result.go_numbers:
                print(
                    f"  - {identifier.value}"
                )

            print(
                f"\nGO count: "
                f"{len(result.go_numbers)}"
            )

            print(
                "\nFirst 1500 characters "
                "of extracted text:"
            )

            print(
                full_text[:1500]
            )

            print()

        except Exception as exc:
            print(
                f"ERROR: "
                f"{type(exc).__name__}: {exc}"
            )

            print()


if __name__ == "__main__":
    asyncio.run(main())