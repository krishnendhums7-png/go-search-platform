"""Index Kerala Government Order embeddings into Qdrant."""

import asyncio
import io
import sys
from pathlib import Path

from fastapi import UploadFile
from qdrant_client import QdrantClient
from sqlalchemy import select

# Make the project root importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.identifier_extraction import (
    IdentifierExtractionResult,
)
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.storage.mock_storage import MockStorageService
from app.storage.relational.models import (
    GovernmentOrderModel,
)
from app.storage.relational.session import SessionFactory
from app.storage.vector.qdrant_client import (
    QdrantVectorStore,
)


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "government_orders"


def resolve_existing_document_id(
    result: IdentifierExtractionResult,
) -> str:
    """Resolve the existing PostgreSQL document ID.

    The Module 7 database already contains the Government Order
    metadata. This function uses extracted GO numbers to locate
    the existing document ID rather than creating a new UUID.

    Args:
        result: Identifier extraction result for the PDF.

    Returns:
        Existing PostgreSQL document ID as a string.

    Raises:
        ValueError: If the document cannot be resolved uniquely.
    """
    go_numbers = [
        identifier.value.strip()
        for identifier in result.go_numbers
        if identifier.value.strip()
    ]

    if not go_numbers:
        raise ValueError(
            "No Government Order number was extracted."
        )

    with SessionFactory() as session:
        statement = select(
            GovernmentOrderModel
        ).where(
            GovernmentOrderModel.go_number.in_(
                go_numbers
            )
        )

        records = list(
            session.scalars(statement).all()
        )

    if not records:
        raise ValueError(
            "No matching Government Order metadata "
            "was found in PostgreSQL."
        )

    document_ids = {
        str(record.document_id)
        for record in records
    }

    if len(document_ids) != 1:
        raise ValueError(
            "Extracted Government Orders resolve to "
            "multiple PostgreSQL document IDs."
        )

    return next(iter(document_ids))


async def process_and_index(
    document_service: DocumentService,
    embedding_service: EmbeddingService,
    vector_store: QdrantVectorStore,
    pdf_path: Path,
) -> int:
    """Process one PDF and index its page embeddings.

    Args:
        document_service: Document intake and extraction service.
        embedding_service: Multilingual embedding service.
        vector_store: Qdrant vector storage service.
        pdf_path: Government Order PDF.

    Returns:
        Number of page embeddings indexed.
    """
    with pdf_path.open("rb") as file:
        upload = UploadFile(
            filename=pdf_path.name,
            file=io.BytesIO(file.read()),
            headers={
                "content-type": "application/pdf",
            },
        )

        # Temporary document used only for processing.
        #
        # IMPORTANT:
        # We do NOT use this generated UUID for Qdrant.
        temporary_document = (
            await document_service.upload(
                upload
            )
        )

    temporary_document_id = (
        temporary_document.id
    )

    # Module 4:
    # Extract native PDF text or OCR text.
    text_result = document_service.extract_text(
        temporary_document_id
    )

    pages = [
        (
            page.page_number,
            page.text,
        )
        for page in text_result.pages
        if page.text
        and page.text.strip()
    ]

    if not pages:
        raise ValueError(
            f"No text extracted from "
            f"'{pdf_path.name}'."
        )

    # Module 5:
    # Extract Government Order identifiers.
    extraction_result = (
        document_service.extract_identifiers(
            temporary_document_id
        )
    )

    # Resolve the EXISTING PostgreSQL document ID.
    existing_document_id = (
        resolve_existing_document_id(
            extraction_result
        )
    )

    print(
        f"  PostgreSQL document ID: "
        f"{existing_document_id}"
    )

    # Module 6:
    # Generate multilingual embeddings using the
    # existing PostgreSQL document identity.
    embedding_result = (
        embedding_service.embed_documents(
            document_id=existing_document_id,
            pages=pages,
        )
    )

    # Store vectors in Qdrant.
    vector_store.upsert(
        embedding_result.chunks
    )

    return len(
        embedding_result.chunks
    )


async def main() -> None:
    """Run the complete embedding indexing pipeline."""
    print("=" * 70)
    print("KERALA GO - MODULE 6")
    print("MULTILINGUAL EMBEDDING INDEXING")
    print("=" * 70)

    pdf_files = sorted(
        RAW_DATA_DIR.glob("*.pdf")
    )

    print(
        f"PDF files: {len(pdf_files)}"
    )

    print(
        f"Qdrant: "
        f"{QDRANT_HOST}:{QDRANT_PORT}"
    )

    print(
        f"Collection: "
        f"{COLLECTION_NAME}"
    )

    print()

    if not pdf_files:
        print(
            f"ERROR: No PDF files found in "
            f"{RAW_DATA_DIR}"
        )
        return

    # ------------------------------------------------------------------
    # Load embedding model
    # ------------------------------------------------------------------

    print(
        "Loading multilingual-e5-large..."
    )

    embedding_service = (
        EmbeddingService()
    )

    print(
        "Model loaded successfully."
    )

    print()

    # ------------------------------------------------------------------
    # Connect to Qdrant
    # ------------------------------------------------------------------

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
    )

    # ------------------------------------------------------------------
    # Document processing service
    # ------------------------------------------------------------------

    storage = MockStorageService()

    document_service = (
        DocumentService(
            storage_service=storage
        )
    )

    # ------------------------------------------------------------------
    # Process PDFs
    # ------------------------------------------------------------------

    successful_files = 0
    failed_files = 0
    total_embeddings = 0

    for pdf_path in pdf_files:
        print("-" * 70)
        print(
            f"Processing: "
            f"{pdf_path.name}"
        )

        try:
            embedding_count = (
                await process_and_index(
                    document_service=(
                        document_service
                    ),
                    embedding_service=(
                        embedding_service
                    ),
                    vector_store=(
                        vector_store
                    ),
                    pdf_path=pdf_path,
                )
            )

            successful_files += 1
            total_embeddings += (
                embedding_count
            )

            print(
                f"SUCCESS: "
                f"{embedding_count} page "
                f"embeddings indexed"
            )

        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as exc:
            failed_files += 1

            print(
                f"ERROR: "
                f"{pdf_path.name}"
            )

            print(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------

    print()
    print("=" * 70)
    print("MODULE 6 INDEXING SUMMARY")
    print("=" * 70)

    print(
        f"Successful PDFs : "
        f"{successful_files}"
    )

    print(
        f"Failed PDFs     : "
        f"{failed_files}"
    )

    print(
        f"Total embeddings: "
        f"{total_embeddings}"
    )

    # ------------------------------------------------------------------
    # Verify Qdrant
    # ------------------------------------------------------------------

    if successful_files > 0:
        collection = (
            qdrant_client.get_collection(
                collection_name=(
                    COLLECTION_NAME
                )
            )
        )

        print()
        print(
            "Qdrant collection:"
        )

        print(
            f"  Name   : "
            f"{COLLECTION_NAME}"
        )

        print(
            f"  Vectors: "
            f"{collection.points_count}"
        )

    else:
        print()
        print(
            "Qdrant collection was not "
            "created because no documents "
            "were successfully indexed."
        )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())