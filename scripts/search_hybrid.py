"""Run hybrid Government Order search."""

import sys
from pathlib import Path


# ---------------------------------------------------------
# Make the project root importable
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from qdrant_client import QdrantClient

from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import (
    HybridSearchService,
)
from app.storage.relational.session import SessionFactory
from app.storage.vector.qdrant_client import QdrantVectorStore


QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "government_orders"


def main() -> None:
    """Run real hybrid searches."""

    print("=" * 70)
    print("KERALA GO - MODULE 8")
    print("HYBRID SEARCH")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load embedding model
    # ---------------------------------------------------------

    print("Loading multilingual-e5-large...")

    embedding_service = EmbeddingService()

    print("Model loaded successfully.")
    print()

    # ---------------------------------------------------------
    # Connect to Qdrant
    # ---------------------------------------------------------

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
    )

    collection = qdrant_client.get_collection(
        collection_name=COLLECTION_NAME,
    )

    print(
        f"Qdrant collection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Vectors available: "
        f"{collection.points_count}"
    )

    print()

    # ---------------------------------------------------------
    # PostgreSQL + Hybrid Search
    # ---------------------------------------------------------

    with SessionFactory() as session:

        search_service = HybridSearchService(
            session=session,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        queries = [
            "G.O.(Rt) No. 24/2026/ITD",
            "G.O.(Rt) No. 114/2025/ITD",
            "Government Order about Finance",
            "Government Order about information technology",
        ]

        # -----------------------------------------------------
        # Execute searches
        # -----------------------------------------------------

        for query in queries:

            print("=" * 70)
            print(f"QUERY: {query}")
            print("=" * 70)

            response = search_service.search(
                query=query,
                limit=5,
            )

            if not response.results:
                print("No results found.")
                print()
                continue

            for rank, result in enumerate(
                response.results,
                start=1,
            ):
                print(
                    f"\n[{rank}] "
                    f"Combined score: "
                    f"{result.combined_score:.4f}"
                )

                print(
                    f"GO number: "
                    f"{result.go_number}"
                )

                print(
                    f"Document: "
                    f"{result.document_id}"
                )

                print(
                    f"Page: "
                    f"{result.page_number}"
                )

                print(
                    f"Semantic score: "
                    f"{result.semantic_score:.4f}"
                )

                print(
                    f"Metadata match: "
                    f"{result.metadata_match}"
                )

                if result.issue_date:
                    print(
                        f"Issue date: "
                        f"{result.issue_date}"
                    )

                if result.department:
                    print(
                        f"Department: "
                        f"{result.department}"
                    )

                print("Text:")
                print(
                    result.text[:1000]
                )

                print()


if __name__ == "__main__":
    main()