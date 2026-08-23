"""
Models for Module 4 text extraction.
"""

from pydantic import BaseModel


class ExtractedPage(BaseModel):
    """
    Raw text extracted from one PDF page.
    """

    page_number: int
    text: str


class TextExtractionResult(BaseModel):
    """
    Result of extracting text from a Government Order.
    """

    document_id: str
    source_type: str
    page_count: int
    pages: list[ExtractedPage]
    raw_text_object_keys: list[str]