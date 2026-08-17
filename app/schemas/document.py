"""
API schemas for Government Order documents.
"""

from uuid import UUID

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    """
    Response returned after a Government Order upload.
    """

    document_id: UUID

    filename: str

    status: DocumentStatus