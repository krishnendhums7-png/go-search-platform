"""
Government Order document repository.
"""

from uuid import UUID

from app.models.document import Document


class DocumentRepository:
    """
    Temporary in-memory repository for the POC.
    """

    def __init__(self) -> None:
        """
        Initialize repository.
        """
        self._documents: dict[UUID, Document] = {}

    def save(
        self,
        document: Document,
    ) -> Document:
        """
        Save document metadata.

        Args:
            document: Document metadata.

        Returns:
            Saved document.
        """
        self._documents[document.id] = document

        return document

    def find_by_id(
        self,
        document_id: UUID,
    ) -> Document | None:
        """
        Find document by UUID.

        Args:
            document_id: Document UUID.

        Returns:
            Document if found, otherwise None.
        """
        return self._documents.get(document_id)


document_repository = DocumentRepository()