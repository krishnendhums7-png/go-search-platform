"""
Tests for scanned-PDF image preprocessing.
"""

import cv2
import fitz
import numpy as np

from app.services.image_preprocessor import (
    ImagePreprocessor,
)


def create_test_scanned_pdf() -> bytes:
    """
    Create a simple image-only PDF.
    """
    image = np.ones(
        (800, 600),
        dtype=np.uint8,
    ) * 255

    # Draw simple dark text-like lines.
    for y in range(100, 500, 50):
        image[
            y:y + 5,
            80:520,
        ] = 0

    success, encoded = cv2.imencode(
        ".png",
            image,
        )

    assert success

    document = fitz.open()

    page = document.new_page(
        width=600,
        height=800,
    )

    page.insert_image(
        page.rect,
        stream=encoded.tobytes(),
    )

    content = document.tobytes()

    document.close()

    return content


def test_preprocess_scanned_pdf() -> None:
    """
    Test that scanned PDF pages are preprocessed.
    """
    preprocessor = ImagePreprocessor()

    pages = preprocessor.process_pdf(
        create_test_scanned_pdf()
    )

    assert len(pages) == 1

    assert isinstance(
        pages[0],
        bytes,
    )

    assert pages[0].startswith(
        b"\x89PNG"
    )