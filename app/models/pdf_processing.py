"""
Models for PDF classification and preprocessing.
"""

from enum import Enum

from pydantic import BaseModel


class PDFType(str, Enum):
    """
    PDF classification.
    """

    NATIVE = "NATIVE"

    SCANNED = "SCANNED"


class ProcessingPath(str, Enum):
    """
    Processing path selected after classification.
    """

    TEXT_EXTRACTION = "TEXT_EXTRACTION"

    IMAGE_PREPROCESSING = "IMAGE_PREPROCESSING"


class PDFClassificationResult(BaseModel):
    """
    Result of PDF classification.

    Attributes:
        document_id: Government Order document ID.
        filename: Original filename.
        pdf_type: Detected PDF type.
        processing_path: Next processing path.
        page_count: Number of pages.
        pages_with_text: Number of pages with text.
    """

    document_id: str

    filename: str

    pdf_type: PDFType

    processing_path: ProcessingPath

    page_count: int

    pages_with_text: int


class PreprocessedPage(BaseModel):
    """
    Metadata for a preprocessed PDF page.
    """

    page_number: int

    object_key: str


class PreprocessingResult(BaseModel):
    """
    Result of scanned-PDF preprocessing.
    """

    document_id: str

    page_count: int

    processed_pages: list[PreprocessedPage]