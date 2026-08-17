"""
Government Order document domain model.
"""

from datetime import UTC
from datetime import datetime
from enum import Enum
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field


class DocumentStatus(str, Enum):
    """
    Status of a Government Order document.
    """

    UPLOADED = "UPLOADED"


class Document(BaseModel):
    """
    Represents a Government Order received by the system.

    Attributes:
        id: Unique tracking UUID.
        filename: Original uploaded filename.
        object_key: Key used by object storage.
        content_type: MIME type.
        file_size: File size in bytes.
        status: Current document status.
        created_at: Time at which the document was received.
    """

    id: UUID = Field(
        default_factory=uuid4
    )

    filename: str

    object_key: str

    content_type: str

    file_size: int

    status: DocumentStatus = DocumentStatus.UPLOADED

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )