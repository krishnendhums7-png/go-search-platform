
"""Index Kerala Government Order embeddings into Qdrant."""

import asyncio
import io
import sys
from pathlib import Path

from fastapi import UploadFile
from qdrant_client import QdrantClient

# Make the project root importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.storage.mock_storage import MockStorageService
from app.storage.vector.qdrant_client import QdrantVectorStore


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "government_orders"


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
        pdf_path: Path to the Government Order PDF.

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

        # Module 2: upload and validate the PDF.
        document = await document_service.upload(upload)

    # The Document model uses `id`, not `document_id`.
    document_id = document.id

    # Module 4: extract native PDF text or OCR text.
    text_result = document_service.extract_text(
        document_id
    )

    # Keep page boundaries intact.
    #
    # This is intentional for the current POC:
    # one page = one retrieval unit.
    pages = [
        (page.page_number, page.text)
        for page in text_result.pages
        if page.text and page.text.strip()
    ]

    if not pages:
        raise ValueError(
            f"No text extracted from '{pdf_path.name}'."
        )

    # Module 6: generate multilingual embeddings.
    embedding_result = embedding_service.embed_documents(
        document_id=str(document_id),
        pages=pages,
    )

    # Module 6: store vectors in Qdrant.
    vector_store.upsert(
        embedding_result.chunks
    )

    return len(embedding_result.chunks)


async def main() -> None:
    """Run the complete Module 6 indexing pipeline."""
    print("=" * 70)
    print("KERALA GO - MODULE 6")
    print("MULTILINGUAL EMBEDDING INDEXING")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Find Government Order PDFs
    # ------------------------------------------------------------------

    pdf_files = sorted(
        RAW_DATA_DIR.glob("*.pdf")
    )

    print(f"PDF files: {len(pdf_files)}")
    print(
        f"Qdrant: {QDRANT_HOST}:{QDRANT_PORT}"
    )
    print(
        f"Collection: {COLLECTION_NAME}"
    )
    print()

    if not pdf_files:
        print(
            f"ERROR: No PDF files found in "
            f"{RAW_DATA_DIR}"
        )
        return

    # ------------------------------------------------------------------
    # Load multilingual embedding model
    # ------------------------------------------------------------------

    print(
        "Loading multilingual-e5-large..."
    )

    embedding_service = EmbeddingService()

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
    # Use existing Module 2/4 storage architecture
    # ------------------------------------------------------------------

    storage = MockStorageService()

    document_service = DocumentService(
        storage_service=storage
    )

    # ------------------------------------------------------------------
    # Process all PDFs
    # ------------------------------------------------------------------

    successful_files = 0
    failed_files = 0
    total_embeddings = 0

    for pdf_path in pdf_files:
        print("-" * 70)
        print(
            f"Processing: {pdf_path.name}"
        )

        try:
            embedding_count = (
                await process_and_index(
                    document_service=document_service,
                    embedding_service=embedding_service,
                    vector_store=vector_store,
                    pdf_path=pdf_path,
                )
            )

            successful_files += 1
            total_embeddings += embedding_count

            print(
                f"SUCCESS: "
                f"{embedding_count} page embeddings indexed"
            )

        except Exception as exc:
            failed_files += 1

            print(
                f"ERROR: {pdf_path.name}"
            )
            print(
                f"{type(exc).__name__}: {exc}"
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
    # Verify Qdrant collection
    # ------------------------------------------------------------------

    if successful_files > 0:
        collection = (
            qdrant_client.get_collection(
                collection_name=COLLECTION_NAME
            )
        )

        print()
        print("Qdrant collection:")
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
            "Qdrant collection was not created "
            "because no documents were successfully "
            "indexed."
        )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
