"""
Tests for Module 4 text extraction.
"""

import cv2
import fitz
import numpy as np

from app.services.text_extractor import TextExtractor
from app.storage.mock_storage import MockStorageService


def create_native_pdf() -> bytes:
    """Create a native PDF containing text."""

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
    """Create an image-only PDF for OCR testing."""

    image = np.ones(
        (800, 1200),
        dtype=np.uint8,
    ) * 255

    cv2.putText(
        image,
        "Government Order Kerala",
        (80, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        2,
        0,
        3,
        cv2.LINE_AA,
    )

    success, encoded = cv2.imencode(
        ".png",
        image,
    )

    assert success

    document = fitz.open()

    page = document.new_page(
        width=600,
        height=400,
    )

    page.insert_image(
        page.rect,
        stream=encoded.tobytes(),
    )

    content = document.tobytes()

    document.close()

    return content


def test_native_text_extraction() -> None:
    """Native PDF should use PyMuPDF."""

    storage = MockStorageService()

    pdf_content = create_native_pdf()

    storage.save(
        file_content=pdf_content,
        object_key="original/native.pdf",
        content_type="application/pdf",
    )

    extractor = TextExtractor(
        storage_service=storage
    )

    result = extractor.extract(
        document_id="native-test",
        filename="native.pdf",
        object_key="original/native.pdf",
    )

    assert result.source_type == "NATIVE"

    assert result.page_count == 1

    assert result.pages[0].page_number == 1

    assert (
        "Government Order"
        in result.pages[0].text
    )

    assert (
        result.raw_text_object_keys[0]
        == "ocr/raw/native-test/page_001.txt"
    )


def test_scanned_text_extraction() -> None:
    """Scanned PDF should use Tesseract OCR."""

    storage = MockStorageService()

    pdf_content = create_scanned_pdf()

    storage.save(
        file_content=pdf_content,
        object_key="original/scanned.pdf",
        content_type="application/pdf",
    )

    extractor = TextExtractor(
        storage_service=storage
    )

    result = extractor.extract(
        document_id="scanned-test",
        filename="scanned.pdf",
        object_key="original/scanned.pdf",
    )

    assert result.source_type == "SCANNED"

    assert result.page_count == 1

    assert result.pages[0].page_number == 1

    assert len(
        result.pages[0].text.strip()
    ) > 0

    assert (
        result.raw_text_object_keys[0]
        == "ocr/raw/scanned-test/page_001.txt"
    )


def test_page_boundaries_are_preserved() -> None:
    """Each PDF page should produce a separate result."""

    document = fitz.open()

    page1 = document.new_page()

    page1.insert_text(
        (72, 72),
        "Page One",
    )

    page2 = document.new_page()

    page2.insert_text(
        (72, 72),
        "Page Two",
    )

    pdf_content = document.tobytes()

    document.close()

    storage = MockStorageService()

    storage.save(
        file_content=pdf_content,
        object_key="original/two-pages.pdf",
        content_type="application/pdf",
    )

    extractor = TextExtractor(
        storage_service=storage
    )

    result = extractor.extract(
        document_id="two-page-test",
        filename="two-pages.pdf",
        object_key="original/two-pages.pdf",
    )

    assert result.page_count == 2

    assert result.pages[0].page_number == 1

    assert result.pages[1].page_number == 2

    assert "Page One" in result.pages[0].text

    assert "Page Two" in result.pages[1].text