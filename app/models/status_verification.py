"""
Models for Government Order status verification.
"""

from enum import Enum

from pydantic import BaseModel, Field


class GovernmentOrderStatus(str, Enum):
    """Represent the current legal status of a Government Order."""

    ACTIVE = "ACTIVE"
    AMENDED = "AMENDED"
    CANCELED = "CANCELED"


class StatusVerificationResult(BaseModel):
    """
    Represent the result of recursive Government Order
    status verification.
    """

    document_id: str
    go_number: str
    status: GovernmentOrderStatus

    traversed_go_numbers: list[str] = Field(
        default_factory=list
    )

    relationships_checked: int = 0

    cycle_detected: bool = False