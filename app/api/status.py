"""
Government Order status, details, and relationship API.
"""

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from app.services.metadata_service import MetadataService
from app.services.status_verification_service import (
    StatusVerificationService,
)
from app.storage.relational.session import SessionFactory


router = APIRouter(
    prefix="/government-orders",
    tags=["Government Orders"],
)


@router.get("/details")
def get_go_details(
    go_number: str = Query(
        ...,
        min_length=1,
        description="Government Order number",
    ),
) -> dict:
    """
    Retrieve Government Order metadata by its number.
    """

    try:
        with SessionFactory() as session:
            metadata_service = MetadataService(
                session=session,
            )

            status_service = StatusVerificationService(
                metadata_service=metadata_service,
            )

            normalized_go_number = (
                status_service._normalize_go_number(
                    go_number,
                )
            )

            government_order = (
                metadata_service.find_by_go_number(
                    normalized_go_number,
                )
            )

            if government_order is None:
                raise HTTPException(
                    status_code=404,
                    detail="Government Order was not found.",
                )

            status_result = status_service.verify(
                government_order.id,
            )

            return {
                "document_id": str(
                    government_order.document_id,
                ),
                "go_number": government_order.go_number,
                "department": government_order.department,
                "issue_date": (
                    government_order.issue_date.isoformat()
                    if government_order.issue_date
                    else None
                ),
                "status": status_result.status.value,
            }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get("/relationships")
def get_go_relationships(
    go_number: str = Query(
        ...,
        min_length=1,
        description="Government Order number",
    ),
) -> dict:
    """
    Retrieve recorded incoming and outgoing relationships
    and verify the Government Order's status.
    """

    try:
        with SessionFactory() as session:
            metadata_service = MetadataService(
                session=session,
            )

            status_service = StatusVerificationService(
                metadata_service=metadata_service,
            )

            normalized_go_number = (
                status_service._normalize_go_number(
                    go_number,
                )
            )

            government_order = (
                metadata_service.find_by_go_number(
                    normalized_go_number,
                )
            )

            if government_order is None:
                raise HTTPException(
                    status_code=404,
                    detail="Government Order was not found.",
                )

            relationships = []

            # Incoming: another Government Order acts on this GO.
            incoming = (
                metadata_service.get_incoming_relationships(
                    government_order.id,
                )
            )

            for relation in incoming:
                related_go = metadata_service.get_by_id(
                    relation.source_go_id,
                )

                if related_go is None:
                    continue

                relationships.append({
                    "direction": "incoming",
                    "relationship_type": (
                        relation.relationship_type
                    ),
                    "related_go_number": related_go.go_number,
                    "related_document_id": str(
                        related_go.document_id,
                    ),
                    "department": related_go.department,
                    "issue_date": (
                        related_go.issue_date.isoformat()
                        if related_go.issue_date
                        else None
                    ),
                    "matched_phrase": relation.matched_phrase,
                    "page_number": relation.page_number,
                })

            # Outgoing: this GO acts on another Government Order.
            outgoing = (
                metadata_service.get_outgoing_relationships(
                    government_order.id,
                )
            )

            for relation in outgoing:
                related_go = metadata_service.get_by_id(
                    relation.target_go_id,
                )

                if related_go is None:
                    continue

                relationships.append({
                    "direction": "outgoing",
                    "relationship_type": (
                        relation.relationship_type
                    ),
                    "related_go_number": related_go.go_number,
                    "related_document_id": str(
                        related_go.document_id,
                    ),
                    "department": related_go.department,
                    "issue_date": (
                        related_go.issue_date.isoformat()
                        if related_go.issue_date
                        else None
                    ),
                    "matched_phrase": relation.matched_phrase,
                    "page_number": relation.page_number,
                })

            status_result = status_service.verify(
                government_order.id,
            )

            return {
                "go_number": government_order.go_number,
                "status": status_result.status.value,
                "relationships": relationships,
                "relationship_count": len(relationships),
            }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get("/status")
def get_go_status(
    go_number: str = Query(
        ...,
        min_length=1,
        description="Government Order number",
    ),
) -> dict:
    """
    Verify legal status using the deterministic
    Government Order relationship graph.
    """

    try:
        with SessionFactory() as session:
            metadata_service = MetadataService(
                session=session,
            )

            status_service = StatusVerificationService(
                metadata_service=metadata_service,
            )

            result = status_service.verify_by_go_number(
                go_number,
            )

            return result.model_dump(mode="json")

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc