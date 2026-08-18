"""
PDF classification service.

Uses PyMuPDF to determine whether a PDF contains
a native text layer or is image-only.
"""

from io import BytesIO

import fitz

from app.models.pdf_processing import PDFClassificationResult
from app.models.pdf_processing import PDFType
from app.models.pdf_processing import ProcessingPath


class PDFClassificationError(Exception):
    """Raised when PDF classification fails."""


class PDFClassifier:
    """
    Classifies Government Order PDFs.

    A native PDF contains an extractable text layer.
    A scanned PDF contains no extractable text.
    """

    def classify(
        self,
        document_id: str,
        filename: str,
        pdf_content: bytes,
    ) -> PDFClassificationResult:
        """
        Classify a PDF using PyMuPDF.

        Args:
            document_id: Document identifier.
            filename: Original filename.
            pdf_content: PDF bytes.

        Returns:
            PDF classification result.
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
            raise PDFClassificationError(
                "Unable to open PDF."
            ) from exc

        try:
            page_count = len(document)

            pages_with_text = (
                self._count_text_pages(
                    document
                )
            )

        finally:
            document.close()

        if pages_with_text == page_count:
            pdf_type = PDFType.NATIVE

            processing_path = (
                ProcessingPath.TEXT_EXTRACTION
            )

        elif pages_with_text == 0:
            pdf_type = PDFType.SCANNED

            processing_path = (
                ProcessingPath.IMAGE_PREPROCESSING
            )

        else:
            # Mixed PDFs are treated as scanned for the
            # POC so that image-only pages are not skipped.
            pdf_type = PDFType.SCANNED

            processing_path = (
                ProcessingPath.IMAGE_PREPROCESSING
            )

        return PDFClassificationResult(
            document_id=document_id,
            filename=filename,
            pdf_type=pdf_type,
            processing_path=processing_path,
            page_count=page_count,
            pages_with_text=pages_with_text,
        )

    @staticmethod
    def _count_text_pages(
        document: fitz.Document,
    ) -> int:
        """
        Count pages containing extractable text.

        Args:
            document: Open PyMuPDF document.

        Returns:
            Number of pages with text.
        """
        pages_with_text = 0

        for page in document:
            text = page.get_text(
                "text"
            ).strip()

            if text:
                pages_with_text += 1

        return pages_with_text


pdf_classifier = PDFClassifier()