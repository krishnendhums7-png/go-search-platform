"""
Hybrid search over PostgreSQL metadata and Qdrant vectors.
"""

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.embedding import SearchResult
from app.models.hybrid_search import (
    HybridSearchResponse,
    HybridSearchResult,
)
from app.repositories.government_order_repository import (
    GovernmentOrderRepository,
)
from app.services.embedding_service import EmbeddingService
from app.storage.vector.qdrant_client import QdrantVectorStore


class HybridSearchService:
    """Combine relational and semantic Government Order search."""

    GO_NUMBER_PATTERN = re.compile(
        r"""
        G\.?\s*O\.?
        \s*
        \(?
        (?P<category>P|Rt|Ms)
        \)?
        \s*
        (?:No\.?|N[o0]\.?)
        \s*
        (?P<number>\d+)
        \s*/\s*
        (?P<year>\d{4})
        \s*/\s*
        (?P<department>[A-Za-z&]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
    ) -> None:
        """Initialize the hybrid search service."""

        self._repository = GovernmentOrderRepository(
            session
        )

        self._embedding_service = embedding_service
        self._vector_store = vector_store

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> HybridSearchResponse:
        """
        Perform hybrid metadata and semantic search.

        The search combines:

        1. Exact Government Order metadata lookup.
        2. Multilingual Qdrant semantic retrieval.
        3. Deterministic metadata enrichment.

        No legal text is generated or modified.
        """

        cleaned_query = query.strip()

        if not cleaned_query:
            raise ValueError(
                "Search query cannot be empty."
            )

        if limit < 1:
            raise ValueError(
                "Search limit must be at least 1."
            )

        metadata_results = self._metadata_search(
            cleaned_query
        )

        semantic_results = self._semantic_search(
            cleaned_query,
            limit,
        )

        return self._merge_results(
            query=cleaned_query,
            metadata_results=metadata_results,
            semantic_results=semantic_results,
            limit=limit,
        )

    def _metadata_search(
        self,
        query: str,
    ) -> list:
        """
        Search PostgreSQL using explicit GO numbers.

        Only exact canonical GO numbers are considered
        metadata matches.
        """

        matches = self.GO_NUMBER_PATTERN.finditer(
            query
        )

        results = []

        for match in matches:
            category = match.group(
                "category"
            )

            number = match.group(
                "number"
            )

            year = match.group(
                "year"
            )

            department = match.group(
                "department"
            )

            go_number = (
                f"G.O.({category}) "
                f"No. {number}/{year}/{department}"
            )

            government_order = (
                self._repository.search_by_go_number(
                    go_number
                )
            )

            if government_order is not None:
                results.append(
                    government_order
                )

        return results

    def _semantic_search(
        self,
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        """Search Qdrant using a multilingual embedding."""

        query_vector = (
            self._embedding_service.embed_query(
                query
            )
        )

        return self._vector_store.search(
            query_vector=query_vector,
            limit=limit,
        )

    def _get_document_metadata(
        self,
        document_id: str,
    ) -> list:
        """Retrieve all Government Order metadata for a document."""

        try:
            uuid_document_id = UUID(
                document_id
            )
        except ValueError:
            return []

        return self._repository.get_by_document_id(
            uuid_document_id
        )

    @staticmethod
    def _normalize_go_text(
        value: str,
    ) -> str:
        """
        Normalize Government Order text for OCR-tolerant
        comparison.

        Whitespace is removed and text is lower-cased.
        This allows identifiers with OCR spacing differences
        to be matched without changing the actual identifier.
        """

        return re.sub(
            r"\s+",
            "",
            value,
        ).lower()

    @classmethod
    def _select_metadata(
        cls,
        metadata: list,
        semantic_result: SearchResult,
        direct_metadata: list,
    ):
        """
        Select the most relevant metadata record.

        Priority:

        1. Direct metadata match from the user's GO query.
        2. GO number identified in the retrieved text.
        3. First GO belonging to the document.

        OCR spacing differences are normalized before
        comparing GO numbers.
        """

        # ----------------------------------------------------------
        # Priority 1:
        # Direct metadata match from the user's query.
        # ----------------------------------------------------------

        if direct_metadata:
            return direct_metadata[0]

        # ----------------------------------------------------------
        # Priority 2:
        # Identify the GO number in the retrieved text.
        # ----------------------------------------------------------

        normalized_text = (
            cls._normalize_go_text(
                semantic_result.text
            )
        )

        for government_order in metadata:
            if not government_order.go_number:
                continue

            normalized_go_number = (
                cls._normalize_go_text(
                    government_order.go_number
                )
            )

            if (
                normalized_go_number
                in normalized_text
            ):
                return government_order

        # ----------------------------------------------------------
        # Priority 3:
        # Fallback to the first GO belonging to the document.
        # ----------------------------------------------------------

        return (
            metadata[0]
            if metadata
            else None
        )

    def _merge_results(
        self,
        query: str,
        metadata_results: list,
        semantic_results: list[SearchResult],
        limit: int,
    ) -> HybridSearchResponse:
        """
        Merge PostgreSQL metadata with Qdrant results.

        Semantic text always comes directly from Qdrant.
        PostgreSQL contributes only deterministic metadata.
        """

        metadata_by_document: dict[
            str,
            list,
        ] = {}

        # ----------------------------------------------------------
        # Metadata directly matched by the query.
        # ----------------------------------------------------------

        for government_order in metadata_results:
            document_id = str(
                government_order.document_id
            )

            metadata_by_document.setdefault(
                document_id,
                [],
            ).append(
                government_order
            )

        metadata_document_ids = {
            str(government_order.document_id)
            for government_order in metadata_results
        }

        merged: list[
            HybridSearchResult
        ] = []

        seen_chunks: set[str] = set()

        # ----------------------------------------------------------
        # Process semantic results.
        # ----------------------------------------------------------

        for semantic_result in semantic_results:
            document_id = (
                semantic_result.document_id
            )

            # ------------------------------------------------------
            # Load metadata for the semantic result's document.
            # ------------------------------------------------------

            if (
                document_id
                not in metadata_by_document
            ):
                document_metadata = (
                    self._get_document_metadata(
                        document_id
                    )
                )

                if document_metadata:
                    metadata_by_document[
                        document_id
                    ] = document_metadata

            document_metadata = (
                metadata_by_document.get(
                    document_id,
                    [],
                )
            )

            # ------------------------------------------------------
            # Determine whether this document was directly matched
            # by the user's explicit GO-number query.
            # ------------------------------------------------------

            direct_metadata = (
                metadata_results
                if document_id
                in metadata_document_ids
                else []
            )

            # ------------------------------------------------------
            # Select the correct metadata record.
            # ------------------------------------------------------

            metadata = self._select_metadata(
                metadata=document_metadata,
                semantic_result=semantic_result,
                direct_metadata=direct_metadata,
            )

            metadata_match = (
                document_id
                in metadata_document_ids
            )

            # ------------------------------------------------------
            # Calculate combined ranking score.
            # ------------------------------------------------------

            combined_score = (
                semantic_result.score
            )

            if metadata_match:
                combined_score += 0.20

            # ------------------------------------------------------
            # Build retrieval result.
            #
            # IMPORTANT:
            # text comes directly from Qdrant.
            # No generation or paraphrasing occurs.
            # ------------------------------------------------------

            result = HybridSearchResult(
                document_id=document_id,
                go_number=(
                    metadata.go_number
                    if metadata is not None
                    else None
                ),
                issue_date=(
                    str(metadata.issue_date)
                    if (
                        metadata is not None
                        and metadata.issue_date
                        is not None
                    )
                    else None
                ),
                department=(
                    metadata.department
                    if metadata is not None
                    else None
                ),
                page_number=(
                    semantic_result.page_number
                ),
                chunk_id=(
                    semantic_result.chunk_id
                ),
                text=semantic_result.text,
                semantic_score=(
                    semantic_result.score
                ),
                metadata_match=metadata_match,
                combined_score=combined_score,
            )

            # ------------------------------------------------------
            # Prevent duplicate chunks.
            # ------------------------------------------------------

            if (
                result.chunk_id
                not in seen_chunks
            ):
                merged.append(result)

                seen_chunks.add(
                    result.chunk_id
                )

        # ----------------------------------------------------------
        # Rank results by combined score.
        # ----------------------------------------------------------

        merged.sort(
            key=lambda result: (
                result.combined_score
            ),
            reverse=True,
        )

        # ----------------------------------------------------------
        # Retrieval-only response.
        #
        # Metadata-only records are not converted into
        # artificial legal text.
        # ----------------------------------------------------------

        return HybridSearchResponse(
            query=query,
            results=merged[:limit],
        )