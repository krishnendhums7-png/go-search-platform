"""Search Kerala Government Order embeddings in Qdrant."""

import sys
from pathlib import Path

from qdrant_client import QdrantClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.semantic_search_service import (
    SemanticSearchService,
)
from app.storage.vector.qdrant_client import QdrantVectorStore


def main() -> None:
    """Run interactive semantic search."""
    print("=" * 70)
    print("KERALA GO - MODULE 6")
    print("MULTILINGUAL SEMANTIC SEARCH")
    print("=" * 70)

    print("Loading multilingual-e5-large...")

    embedding_service = EmbeddingService()

    print("Model loaded successfully.")
    print()

    # ---------------------------------------------------------
    # Connect to Qdrant using application configuration
    # ---------------------------------------------------------

    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )

    search_service = SemanticSearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    collection = qdrant_client.get_collection(
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )

    print(
        f"Qdrant collection: "
        f"{settings.QDRANT_COLLECTION_NAME}"
    )

    print(
        f"Vectors available: "
        f"{collection.points_count}"
    )

    print()

    # ---------------------------------------------------------
    # Test multilingual queries
    # ---------------------------------------------------------

    queries = [
        "Government Order about pension",
        "സർക്കാർ ഉത്തരവ് പെൻഷൻ",
        "pension സംബന്ധിച്ച സർക്കാർ ഉത്തരവ്",
        "Government Order regarding Finance Department",
        "G.O. number 15",
    ]

    for query in queries:
        print("=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70)

        results = search_service.search(
            query=query,
            limit=5,
        )

        if not results:
            print("No results found.")
            print()
            continue

        for rank, result in enumerate(
            results,
            start=1,
        ):
            print(
                f"\n[{rank}] "
                f"Score: {result.score:.4f}"
            )

            print(
                f"Document: {result.document_id}"
            )

            print(
                f"Page: {result.page_number}"
            )

            print(
                f"Chunk: {result.chunk_id}"
            )

            print("Text:")
            print(result.text[:1000])
            print()


if __name__ == "__main__":
    main()