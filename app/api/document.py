"""
Government Order document API.
"""

from uuid import UUID

from fastapi import APIRouter
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status

from app.schemas.document import DocumentUploadResponse
from app.services.document_service import (
    InvalidDocumentException,
)
from app.services.document_service import (
    document_service,
)

from app.models.pdf_processing import (
    PDFClassificationResult,
)
from app.models.pdf_processing import (
    PreprocessingResult,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """
    Receive and store a Government Order PDF.

    Args:
        file: Uploaded PDF.

    Returns:
        Document tracking information.
    """
    try:
        document = await document_service.upload(
            file
        )

        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
        )

    except InvalidDocumentException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{document_id}",
)
def get_document(
    document_id: UUID,
) -> dict:
    """
    Retrieve document metadata.

    Args:
        document_id: Document tracking UUID.

    Returns:
        Document metadata.
    """
    document = document_service.get_document(
        document_id
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document.model_dump(
        mode="json"
    )

@router.post(
    "/{document_id}/classify",
    response_model=PDFClassificationResult,
)
def classify_document(
    document_id: UUID,
) -> PDFClassificationResult:
    """
    Classify a stored Government Order PDF.
    """
    try:
        return document_service.classify(
            document_id
        )

    except InvalidDocumentException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.post(
    "/{document_id}/preprocess",
    response_model=PreprocessingResult,
)
def preprocess_document(
    document_id: UUID,
) -> PreprocessingResult:
    """
    Preprocess a scanned Government Order PDF.
    """
    try:
        return document_service.preprocess(
            document_id
        )

    except InvalidDocumentException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc