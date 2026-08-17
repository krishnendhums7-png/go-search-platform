"""
Tests for Module 2 document intake.
"""

from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_valid_pdf() -> None:
    """
    Test successful PDF intake.
    """
    pdf_content = (
        b"%PDF-1.4\n"
        b"Test Government Order\n"
    )

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "GO_001.pdf",
                BytesIO(pdf_content),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["filename"] == "GO_001.pdf"

    assert data["status"] == "UPLOADED"

    assert "document_id" in data


def test_reject_non_pdf_extension() -> None:
    """
    Test rejection of non-PDF filename.
    """
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "GO_001.txt",
                BytesIO(b"%PDF-1.4"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


def test_reject_wrong_content_type() -> None:
    """
    Test rejection of incorrect MIME type.
    """
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "GO_001.pdf",
                BytesIO(b"%PDF-1.4"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_reject_invalid_pdf_signature() -> None:
    """
    Test rejection of a renamed non-PDF file.
    """
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "GO_001.pdf",
                BytesIO(b"This is not a PDF."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


def test_reject_empty_pdf() -> None:
    """
    Test rejection of an empty file.
    """
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "empty.pdf",
                BytesIO(b""),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400