"""
Government Order document intake service.

This service handles:
    - PDF validation
    - PDF storage
    - Document metadata
    - PDF classification
    - Scanned PDF preprocessing

No LLM or text generation is used here.
"""

from uuid import UUID
from uuid import uuid4

from fastapi import UploadFile

from app.core.exceptions import GOSearchException
from app.models.document import Document
from app.models.pdf_processing import (
    PDFClassificationResult,
)
from app.models.pdf_processing import (
    PreprocessedPage,
)
from app.models.pdf_processing import (
    PreprocessingResult,
)
from app.models.pdf_processing import (
    ProcessingPath,
)
from app.repositories.document_repository import (
    document_repository,
)
from app.services.image_preprocessor import (
    image_preprocessor,
)
from app.services.pdf_classifier import (
    pdf_classifier,
)
from app.storage.mock_storage import (
    MockStorageService,
)
from app.models.text_extraction import TextExtractionResult
from app.services.text_extractor import TextExtractor
from app.storage.storage_service import StorageService
from app.models.identifier_extraction import (
    IdentifierExtractionResult,
)
from app.services.identifier_extractor import (
    identifier_extractor,
)
from app.services.text_extractor import (
    TextExtractor,
)

class InvalidDocumentException(GOSearchException):
    """
    Raised when an uploaded document is invalid.
    """


class DocumentService:
    """
    Handles Government Order document intake
    and Module 3 PDF processing.
    """

    MAX_FILE_SIZE = 20 * 1024 * 1024

    ALLOWED_CONTENT_TYPE = "application/pdf"

    def __init__(
        self,
        storage_service: StorageService,
    ) -> None:
        """
        Initialize the document service.

        Args:
            storage_service:
                Object storage implementation.
        """
        self._storage_service = storage_service

        self._text_extractor = TextExtractor(
            storage_service
        )

    # =========================================================
    # MODULE 2 — PDF UPLOAD
    # =========================================================

    async def upload(
        self,
        file: UploadFile,
    ) -> Document:
        """
        Validate and store a Government Order PDF.

        Args:
            file:
                Uploaded PDF file.

        Returns:
            Stored Document metadata.

        Raises:
            InvalidDocumentException:
                If the uploaded file is invalid.
        """

        # -----------------------------------------------------
        # 1. Validate filename
        # -----------------------------------------------------

        self._validate_filename(
            file.filename
        )

        # -----------------------------------------------------
        # 2. Validate MIME type
        # -----------------------------------------------------

        self._validate_content_type(
            file.content_type
        )

        # -----------------------------------------------------
        # 3. Read uploaded file
        # -----------------------------------------------------

        content = await file.read()

        # -----------------------------------------------------
        # 4. Validate file size
        # -----------------------------------------------------

        self._validate_file_size(
            len(content)
        )

        # -----------------------------------------------------
        # 5. Validate actual PDF signature
        # -----------------------------------------------------

        self._validate_pdf_signature(
            content
        )

        # -----------------------------------------------------
        # 6. Generate unique document UUID
        # -----------------------------------------------------

        document_id = uuid4()

        # -----------------------------------------------------
        # 7. Create object-storage key
        # -----------------------------------------------------

        object_key = (
            f"original/{document_id}.pdf"
        )

        # -----------------------------------------------------
        # 8. Store original PDF
        # -----------------------------------------------------

        self._storage_service.save(
            file_content=content,
            object_key=object_key,
            content_type=self.ALLOWED_CONTENT_TYPE,
        )

        # -----------------------------------------------------
        # 9. Create document metadata
        # -----------------------------------------------------

        document = Document(
            id=document_id,
            filename=file.filename,
            object_key=object_key,
            content_type=self.ALLOWED_CONTENT_TYPE,
            file_size=len(content),
        )

        # -----------------------------------------------------
        # 10. Save metadata and RETURN it
        # -----------------------------------------------------

        return document_repository.save(
            document
        )

    # =========================================================
    # MODULE 2 — VALIDATION METHODS
    # =========================================================

    @staticmethod
    def _validate_filename(
        filename: str | None,
    ) -> None:
        """
        Validate uploaded filename.

        Args:
            filename:
                Original filename.

        Raises:
            InvalidDocumentException:
                If filename is missing or not PDF.
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

    @classmethod
    def _validate_content_type(
        cls,
        content_type: str | None,
    ) -> None:
        """
        Validate uploaded MIME type.

        Args:
            content_type:
                MIME type provided by the client.

        Raises:
            InvalidDocumentException:
                If MIME type is not application/pdf.
        """

        if (
            content_type
            != cls.ALLOWED_CONTENT_TYPE
        ):
            raise InvalidDocumentException(
                "Only application/pdf files are allowed."
            )

    @classmethod
    def _validate_file_size(
        cls,
        file_size: int,
    ) -> None:
        """
        Validate uploaded file size.

        Args:
            file_size:
                Size of uploaded file in bytes.

        Raises:
            InvalidDocumentException:
                If file is empty or too large.
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
        Validate the actual PDF file signature.

        PDF files normally begin with:

            %PDF-

        Args:
            content:
                Uploaded file bytes.

        Raises:
            InvalidDocumentException:
                If the file is not a real PDF.
        """

        if not content.startswith(
            b"%PDF-"
        ):
            raise InvalidDocumentException(
                "Uploaded file is not a valid PDF."
            )

    # =========================================================
    # DOCUMENT RETRIEVAL
    # =========================================================

    @staticmethod
    def get_document(
        document_id: UUID,
    ) -> Document | None:
        """
        Retrieve document metadata.

        Args:
            document_id:
                Document UUID.

        Returns:
            Document if found, otherwise None.
        """

        return document_repository.find_by_id(
            document_id
        )

    # =========================================================
    # MODULE 3 — PDF CLASSIFICATION
    # =========================================================

    def classify(
        self,
        document_id: UUID,
    ) -> PDFClassificationResult:
        """
        Classify a stored Government Order PDF.

        The PDF is retrieved through the storage
        abstraction and passed to the PyMuPDF-based
        classifier.

        Args:
            document_id:
                Document UUID.

        Returns:
            PDF classification result.

        Raises:
            InvalidDocumentException:
                If document does not exist.
        """

        document = self.get_document(
            document_id
        )

        if document is None:
            raise InvalidDocumentException(
                "Document not found."
            )

        # Retrieve original PDF from storage.
        pdf_content = (
            self._storage_service.get(
                document.object_key
            )
        )

        # Classify using Module 3 classifier.
        return pdf_classifier.classify(
            document_id=str(
                document.id
            ),
            filename=document.filename,
            pdf_content=pdf_content,
        )

    # =========================================================
    # MODULE 3 — SCANNED PDF PREPROCESSING
    # =========================================================

    def preprocess(
        self,
        document_id: UUID,
    ) -> PreprocessingResult:
        """
        Preprocess a scanned Government Order PDF.

        Processing is performed only when the classifier
        determines that image preprocessing is required.

        Args:
            document_id:
                Document UUID.

        Returns:
            Preprocessing result containing processed
            page object keys.

        Raises:
            InvalidDocumentException:
                If document does not exist or preprocessing
                is not required.
        """

        document = self.get_document(
            document_id
        )

        if document is None:
            raise InvalidDocumentException(
                "Document not found."
            )

        # Retrieve original PDF.
        pdf_content = (
            self._storage_service.get(
                document.object_key
            )
        )

        # Classify the PDF before preprocessing.
        classification = (
            pdf_classifier.classify(
                document_id=str(
                    document.id
                ),
                filename=document.filename,
                pdf_content=pdf_content,
            )
        )

        # Native PDFs should go to text extraction,
        # not image preprocessing.
        if (
            classification.processing_path
            != ProcessingPath.IMAGE_PREPROCESSING
        ):
            raise InvalidDocumentException(
                "Preprocessing is only required "
                "for scanned PDFs."
            )

        # Run OpenCV preprocessing.
        processed_pages = (
            image_preprocessor.process_pdf(
                pdf_content
            )
        )

        page_objects: list[
            PreprocessedPage
        ] = []

        # Store every processed page.
        for index, page_content in enumerate(
            processed_pages,
            start=1,
        ):
            object_key = (
                f"processed/"
                f"{document.id}/"
                f"page_{index:03d}.png"
            )

            self._storage_service.save(
                file_content=page_content,
                object_key=object_key,
                content_type="image/png",
            )

            page_objects.append(
                PreprocessedPage(
                    page_number=index,
                    object_key=object_key,
                )
            )

        return PreprocessingResult(
            document_id=str(
                document.id
            ),
            page_count=len(
                processed_pages
            ),
            processed_pages=page_objects,
        )
    def extract_text(
        self,
        document_id: UUID,
    ) -> TextExtractionResult:
        """
        Extract raw text from a stored Government Order.
        """

        document = self.get_document(
            document_id
        )

        if document is None:
            raise InvalidDocumentException(
                "Document not found."
            )

        return self._text_extractor.extract(
            document_id=str(document.id),
            filename=document.filename,
            object_key=document.object_key,
        )

    def extract_identifiers(
        self,
        document_id: UUID,
    ) -> IdentifierExtractionResult:
        """
        Extract GO identifiers and relationship signals.
        """

        document = self.get_document(
            document_id
        )

        if document is None:
            raise InvalidDocumentException(
                "Document not found."
            )

        text_result = self.extract_text(
            document_id=document.id
        )

        return identifier_extractor.extract(
            text_result
        )

# =============================================================
# SERVICE INSTANCE
# =============================================================

mock_storage = MockStorageService()

document_service = DocumentService(
    storage_service=mock_storage,
)