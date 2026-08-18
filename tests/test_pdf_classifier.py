"""
Tests for PDF classification.
"""

from io import BytesIO

import fitz

from app.models.pdf_processing import (
    PDFType,
)
from app.models.pdf_processing import (
    ProcessingPath,
)
from app.services.pdf_classifier import (
    PDFClassifier,
)


def create_native_pdf() -> bytes:
    """
    Create a PDF containing native text.
    """
    document = fitz.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "Government Order Kerala",
    )

    content = document.tobytes()

    document.close()

    return content


def create_scanned_pdf() -> bytes:
    """
    Create a PDF with no text layer.
    """
    document = fitz.open()

    document.new_page()

    content = document.tobytes()

    document.close()

    return content


def test_native_pdf() -> None:
    """
    Native PDF should use text extraction.
    """
    classifier = PDFClassifier()

    result = classifier.classify(
        document_id="test-id",
        filename="native.pdf",
        pdf_content=create_native_pdf(),
    )

    assert result.pdf_type == PDFType.NATIVE

    assert (
        result.processing_path
        == ProcessingPath.TEXT_EXTRACTION
    )

    assert result.pages_with_text == 1


def test_scanned_pdf() -> None:
    """
    Scanned PDF should use image preprocessing.
    """
    classifier = PDFClassifier()

    result = classifier.classify(
        document_id="test-id",
        filename="scanned.pdf",
        pdf_content=create_scanned_pdf(),
    )

    assert result.pdf_type == PDFType.SCANNED

    assert (
        result.processing_path
        == ProcessingPath.IMAGE_PREPROCESSING
    )

    assert result.pages_with_text == 0