"""
Government Order document intake service.
"""

from pathlib import PurePosixPath
from uuid import UUID
from uuid import uuid4

from fastapi import UploadFile

from app.core.exceptions import GOSearchException
from app.models.document import Document
from app.repositories.document_repository import (
    document_repository,
)
from app.storage.mock_storage import MockStorageService


class InvalidDocumentException(GOSearchException):
    """
    Raised when an uploaded document is invalid.
    """


class DocumentService:
    """
    Handles raw Government Order PDF intake.
    """

    MAX_FILE_SIZE = 20 * 1024 * 1024

    ALLOWED_CONTENT_TYPE = "application/pdf"

    def __init__(
        self,
        storage_service: MockStorageService,
    ) -> None:
        """
        Initialize document service.

        Args:
            storage_service: Object storage implementation.
        """
        self._storage_service = storage_service

    async def upload(
        self,
        file: UploadFile,
    ) -> Document:
        """
        Validate and store a Government Order PDF.

        Args:
            file: Uploaded PDF.

        Returns:
            Stored document metadata.

        Raises:
            InvalidDocumentException:
                If the uploaded file is invalid.
        """
        self._validate_filename(
            file.filename
        )

        self._validate_content_type(
            file.content_type
        )

        content = await file.read()

        self._validate_file_size(
            len(content)
        )

        self._validate_pdf_signature(
            content
        )

        document_id = uuid4()

        object_key = str(
            PurePosixPath(
                "original",
                f"{document_id}.pdf",
            )
        )

        self._storage_service.save(
            file_content=content,
            object_key=object_key,
            content_type=file.content_type,
        )

        document = Document(
            id=document_id,
            filename=file.filename,
            object_key=object_key,
            content_type=file.content_type,
            file_size=len(content),
        )

        return document_repository.save(
            document
        )

    @staticmethod
    def _validate_filename(
        filename: str | None,
    ) -> None:
        """
        Validate the original filename.

        Args:
            filename: Uploaded filename.

        Raises:
            InvalidDocumentException:
                If filename is missing or not a PDF.
        """
        if not filename:
            raise InvalidDocumentException(
                "Filename is required."
            )

        if not filename.lower().endswith(
            ".pdf"
        ):
            raise InvalidDocumentException(
                "Only PDF files are allowed."
            )

    @staticmethod
    def _validate_content_type(
        content_type: str | None,
    ) -> None:
        """
        Validate uploaded MIME type.

        Args:
            content_type: MIME type.

        Raises:
            InvalidDocumentException:
                If MIME type is not PDF.
        """
        if content_type != "application/pdf":
            raise InvalidDocumentException(
                "Only application/pdf files are allowed."
            )

    @classmethod
    def _validate_file_size(
        cls,
        file_size: int,
    ) -> None:
        """
        Validate file size.

        Args:
            file_size: Size in bytes.

        Raises:
            InvalidDocumentException:
                If file is empty or exceeds the limit.
        """
        if file_size == 0:
            raise InvalidDocumentException(
                "Uploaded file is empty."
            )

        if file_size > cls.MAX_FILE_SIZE:
            raise InvalidDocumentException(
                "File size exceeds the 20 MB limit."
            )

    @staticmethod
    def _validate_pdf_signature(
        content: bytes,
    ) -> None:
        """
        Validate the PDF magic signature.

        Args:
            content: Uploaded file bytes.

        Raises:
            InvalidDocumentException:
                If the file does not have a PDF signature.
        """
        if not content.startswith(
            b"%PDF-"
        ):
            raise InvalidDocumentException(
                "Uploaded file is not a valid PDF."
            )

    @staticmethod
    def get_document(
        document_id: UUID,
    ) -> Document | None:
        """
        Retrieve document metadata.

        Args:
            document_id: Document UUID.

        Returns:
            Document if found, otherwise None.
        """
        return document_repository.find_by_id(
            document_id
        )


mock_storage = MockStorageService()

document_service = DocumentService(
    storage_service=mock_storage,
)