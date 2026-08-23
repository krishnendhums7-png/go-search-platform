"""
Text extraction service for Government Orders.
"""

from io import BytesIO

import fitz
import pytesseract
from PIL import Image

from app.models.pdf_processing import PDFType
from app.models.text_extraction import ExtractedPage
from app.models.text_extraction import TextExtractionResult
from app.services.image_preprocessor import image_preprocessor
from app.services.pdf_classifier import pdf_classifier
from app.storage.storage_service import StorageService


class TextExtractionError(Exception):
    """Raised when text extraction fails."""


class TextExtractor:
    """
    Extracts raw text from native and scanned PDFs.
    """

    OCR_LANGUAGE = "eng+mal"

    def __init__(
        self,
        storage_service: StorageService,
    ) -> None:
        self._storage_service = storage_service

    def extract(
        self,
        document_id: str,
        filename: str,
        object_key: str,
    ) -> TextExtractionResult:
        """
        Extract raw text from a stored PDF.
        """

        pdf_content = self._storage_service.get(
            object_key
        )

        classification = pdf_classifier.classify(
            document_id=document_id,
            filename=filename,
            pdf_content=pdf_content,
        )

        if classification.pdf_type == PDFType.NATIVE:
            pages = self._extract_native(
                pdf_content
            )
            source_type = "NATIVE"

        else:
            pages = self._extract_scanned(
                pdf_content
            )
            source_type = "SCANNED"

        raw_text_keys = self._store_raw_text(
            document_id,
            pages,
        )

        return TextExtractionResult(
            document_id=document_id,
            source_type=source_type,
            page_count=len(pages),
            pages=pages,
            raw_text_object_keys=raw_text_keys,
        )

    @staticmethod
    def _extract_native(
        pdf_content: bytes,
    ) -> list[ExtractedPage]:
        """
        Extract text directly from a native PDF.
        """

        try:
            document = fitz.open(
                stream=BytesIO(pdf_content),
                filetype="pdf",
            )
        except (
            fitz.FileDataError,
            RuntimeError,
        ) as exc:
            raise TextExtractionError(
                "Unable to open PDF."
            ) from exc

        pages: list[ExtractedPage] = []

        try:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                text = page.get_text(
                    "text"
                )

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=text,
                    )
                )
        finally:
            document.close()

        return pages

    @staticmethod
    def _extract_scanned(
        pdf_content: bytes,
    ) -> list[ExtractedPage]:
        """
        OCR scanned PDF pages using Tesseract.
        """

        processed_pages = (
            image_preprocessor.process_pdf(
                pdf_content
            )
        )

        pages: list[ExtractedPage] = []

        for page_number, image_bytes in enumerate(
            processed_pages,
            start=1,
        ):
            try:
                image = Image.open(
                    BytesIO(image_bytes)
                )

                text = pytesseract.image_to_string(
                    image,
                    lang=TextExtractor.OCR_LANGUAGE,
                )

            except Exception as exc:
                raise TextExtractionError(
                    f"OCR failed on page {page_number}."
                ) from exc

            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=text,
                )
            )

        return pages

    def _store_raw_text(
        self,
        document_id: str,
        pages: list[ExtractedPage],
    ) -> list[str]:
        """
        Store raw extraction output page by page.
        """

        object_keys: list[str] = []

        for page in pages:
            object_key = (
                f"ocr/raw/"
                f"{document_id}/"
                f"page_{page.page_number:03d}.txt"
            )

            self._storage_service.save(
                file_content=page.text.encode(
                    "utf-8"
                ),
                object_key=object_key,
                content_type="text/plain; charset=utf-8",
            )

            object_keys.append(
                object_key
            )

        return object_keys