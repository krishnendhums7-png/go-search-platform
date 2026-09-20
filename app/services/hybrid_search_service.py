"""
Hybrid search over PostgreSQL metadata and Qdrant vectors.

This service combines deterministic Government Order metadata
lookup with multilingual semantic retrieval.

No legal text is generated, paraphrased, or modified.
All returned legal text comes directly from the indexed
Government Order documents.
"""

from datetime import date
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

    # Minimum semantic similarity accepted for normal
    # natural-language searches.
    #
    # Exact Government Order searches bypass this threshold
    # because PostgreSQL metadata already identifies the
    # requested Government Order.
    DEFAULT_MIN_SEMANTIC_SCORE = 0.78

    def __init__(
        self,
        session: Session,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        min_semantic_score: float = DEFAULT_MIN_SEMANTIC_SCORE,
    ) -> None:
        """Initialize the hybrid search service."""

        if not 0.0 <= min_semantic_score <= 1.0:
            raise ValueError(
                "Minimum semantic score must be between 0 and 1."
            )

        self._repository = GovernmentOrderRepository(
            session
        )

        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._min_semantic_score = min_semantic_score

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> HybridSearchResponse:
        """
        Perform hybrid metadata and semantic search.

        Exact Government Order number queries are handled
        using PostgreSQL metadata first. Semantic retrieval
        is then restricted to the matching document.

        Normal natural-language queries use multilingual
        semantic retrieval across the corpus with a minimum
        similarity threshold.

        No legal text is generated, paraphrased, or modified.
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

        exact_go_number = (
            self._extract_exact_go_number(
                cleaned_query
            )
        )

        # ----------------------------------------------------------
        # Exact Government Order search
        # ----------------------------------------------------------

        if (
            exact_go_number is not None
            and metadata_results
        ):
            return self._search_exact_go(
                query=cleaned_query,
                go_number=exact_go_number,
                metadata_results=metadata_results,
                limit=limit,
            )

        # ----------------------------------------------------------
        # Normal semantic search
        # ----------------------------------------------------------

        semantic_results = self._semantic_search(
            cleaned_query,
            limit,
            min_score=self._get_min_semantic_score(),
        )

        return self._merge_results(
            query=cleaned_query,
            metadata_results=metadata_results,
            semantic_results=semantic_results,
            limit=limit,
        )

    def _get_min_semantic_score(self) -> float:
        """
        Return the configured semantic similarity threshold.

        The fallback is intentional for lightweight unit-test
        service instances that may construct the object without
        executing the production constructor.
        """

        return getattr(
            self,
            "_min_semantic_score",
            self.DEFAULT_MIN_SEMANTIC_SCORE,
        )

    @classmethod
    def _extract_exact_go_number(
        cls,
        query: str,
    ) -> str | None:
        """
        Extract an exact Government Order number from a query.

        Returns:
            Canonical Government Order number when present,
            otherwise None.
        """

        match = cls.GO_NUMBER_PATTERN.search(
            query
        )

        if match is None:
            return None

        category = match.group("category")
        number = match.group("number")
        year = match.group("year")
        department = match.group("department")

        category_map = {
            "p": "P",
            "rt": "Rt",
            "ms": "Ms",
        }

        normalized_category = category_map.get(
            category.lower(),
            category,
        )

        return (
            f"G.O.({normalized_category}) "
            f"No. {number}/{year}/{department}"
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

            category_map = {
                "p": "P",
                "rt": "Rt",
                "ms": "Ms",
            }

            normalized_category = category_map.get(
                category.lower(),
                category,
            )

            go_number = (
                f"G.O.({normalized_category}) "
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

    def _search_exact_go(
        self,
        query: str,
        go_number: str,
        metadata_results: list,
        limit: int,
    ) -> HybridSearchResponse:
        """
        Search an exact Government Order.

        PostgreSQL identifies the Government Order and its
        document first. Qdrant then retrieves semantic
        context from that same document only.

        Exact Government Order searches do not apply the
        normal semantic threshold because the PostgreSQL
        metadata match already establishes the requested
        Government Order.
        """

        normalized_query_go = (
            self._normalize_go_text(
                go_number
            )
        )

        exact_go = None

        for government_order in metadata_results:
            normalized_go = (
                self._normalize_go_text(
                    government_order.go_number
                )
            )

            if normalized_go == normalized_query_go:
                exact_go = government_order
                break

        if exact_go is None:
            return HybridSearchResponse(
                query=query,
                results=[],
            )

        # Retrieve additional candidates so that document-level
        # filtering has enough candidates to work with.
        #
        # min_score=0.0 is intentional here. The exact PostgreSQL
        # metadata match establishes the requested GO, so semantic
        # retrieval is used only to locate the original text.
        semantic_results = self._semantic_search(
            query,
            max(limit * 3, limit),
            min_score=0.0,
        )

        matching_document_results = [
            result
            for result in semantic_results
            if str(result.document_id)
            == str(exact_go.document_id)
        ]

        if not matching_document_results:
            return HybridSearchResponse(
                query=query,
                results=[],
            )

        return self._merge_results(
            query=query,
            metadata_results=[exact_go],
            semantic_results=matching_document_results,
            limit=limit,
            matched_go_number=exact_go.go_number,
        )

    def _semantic_search(
        self,
        query: str,
        limit: int,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        Search Qdrant using a multilingual embedding.

        Results below ``min_score`` are removed after retrieval.

        The threshold is applied after Qdrant retrieval so that
        the vector store remains responsible for similarity
        ranking.
        """

        query_vector = (
            self._embedding_service.embed_query(
                query
            )
        )

        results = self._vector_store.search(
            query_vector=query_vector,
            limit=limit,
        )

        if min_score is None:
            min_score = self._get_min_semantic_score()

        return [
            result
            for result in results
            if result.score >= min_score
        ]

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
        """

        return re.sub(
            r"\s+",
            "",
            value,
        ).lower()

    @classmethod
    def _find_go_in_text(
        cls,
        text: str,
        metadata: list,
    ):
        """
        Identify a Government Order number explicitly
        present in retrieved text.

        Returns:
            Matching Government Order metadata record,
            or None when no metadata record matches.
        """

        normalized_text = (
            cls._normalize_go_text(
                text
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

        return None

    @classmethod
    def _select_metadata(
        cls,
        metadata: list,
        semantic_result: SearchResult,
        direct_metadata: list,
    ):
        """
        Select metadata for the Government Order matched
        by the user's query.

        Priority:

        1. Direct metadata match from the user's GO query.
        2. GO number identified in the retrieved text.
        3. First GO belonging to the document.
        """

        if direct_metadata:
            return direct_metadata[0]

        text_metadata = cls._find_go_in_text(
            semantic_result.text,
            metadata,
        )

        if text_metadata is not None:
            return text_metadata

        return (
            metadata[0]
            if metadata
            else None
        )

    @classmethod
    def _select_source_metadata(
        cls,
        metadata: list,
        semantic_result: SearchResult,
    ):
        """
        Select metadata representing the actual source
        Government Order of the retrieved text.

        Unlike _select_metadata(), this method does not
        prioritize the user's query match.

        This prevents a referenced GO from being incorrectly
        displayed as the source GO.
        """

        text_metadata = cls._find_go_in_text(
            semantic_result.text,
            metadata,
        )

        if text_metadata is not None:
            return text_metadata

        return (
            metadata[0]
            if metadata
            else None
        )

    @staticmethod
    def _format_issue_date(
        issue_date: date | str | None,
    ) -> str | None:
        """Convert a database date into an API-friendly string."""

        if issue_date is None:
            return None

        if isinstance(issue_date, str):
            return issue_date

        return issue_date.isoformat()

    def _merge_results(
        self,
        query: str,
        metadata_results: list,
        semantic_results: list[SearchResult],
        limit: int,
        matched_go_number: str | None = None,
    ) -> HybridSearchResponse:
        """
        Merge PostgreSQL metadata with Qdrant results.

        Semantic text always comes directly from Qdrant.
        PostgreSQL contributes deterministic metadata only.

        For exact GO queries, source_go_number identifies
        the actual source GO while matched_go_number identifies
        the GO requested by the user.

        No legal text is generated or modified.
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
            # Metadata for the GO matched by the query.
            # ------------------------------------------------------

            metadata = self._select_metadata(
                metadata=document_metadata,
                semantic_result=semantic_result,
                direct_metadata=direct_metadata,
            )

            # ------------------------------------------------------
            # Metadata for the actual source GO.
            # ------------------------------------------------------

            source_metadata = (
                self._select_source_metadata(
                    metadata=document_metadata,
                    semantic_result=semantic_result,
                )
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
            # Determine matched GO.
            # ------------------------------------------------------

            resolved_matched_go = (
                matched_go_number
                if matched_go_number is not None
                else (
                    metadata.go_number
                    if metadata is not None
                    else None
                )
            )

            # ------------------------------------------------------
            # Determine source GO.
            # ------------------------------------------------------

            source_go_number = (
                source_metadata.go_number
                if source_metadata is not None
                else None
            )

            # ------------------------------------------------------
            # Build retrieval result.
            #
            # IMPORTANT:
            # Text comes directly from Qdrant.
            # No generation or paraphrasing occurs.
            # ------------------------------------------------------

            result = HybridSearchResult(
                document_id=document_id,

                # Backward-compatible field.
                #
                # This remains the GO matched by the query
                # for exact GO searches.
                go_number=resolved_matched_go,

                source_go_number=source_go_number,

                matched_go_number=(
                    resolved_matched_go
                ),

                issue_date=self._format_issue_date(
                    metadata.issue_date
                    if (
                        metadata is not None
                        and metadata.issue_date
                        is not None
                    )
                    else (
                        source_metadata.issue_date
                        if (
                            source_metadata is not None
                            and source_metadata.issue_date
                            is not None
                        )
                        else None
                    )
                ),

                department=(
                    source_metadata.department
                    if source_metadata is not None
                    else (
                        metadata.department
                        if metadata is not None
                        else None
                    )
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