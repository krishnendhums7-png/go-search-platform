"""
Models for Government Order identifier and relationship extraction.
"""

from enum import Enum

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Supported Government Order relationship types."""

    AMENDS = "AMENDS"
    SUPERSEDES = "SUPERSEDES"
    CANCELS = "CANCELS"
    READ_AS = "READ_AS"


class ExtractionConfidence(str, Enum):
    """Confidence level for an extracted value."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExtractedIdentifier(BaseModel):
    """An identifier extracted from a Government Order."""

    value: str
    confidence: ExtractionConfidence
    extraction_method: str


class ExtractedReference(BaseModel):
    """
    A Government Order referenced by an ordinal number.

    Example:
        1 G.O.(Rt) No. 114/2025/ITD

    is represented as:

        ordinal = 1
        go_number = G.O.(Rt) No. 114/2025/ITD
    """

    ordinal: int
    go_number: str
    page_number: int | None = None


class ExtractedRelationship(BaseModel):
    """A relationship signal detected in Government Order text."""

    relationship_type: RelationshipType
    matched_phrase: str
    page_number: int | None = None

    # Ordinal references associated with this relationship.
    #
    # Example:
    # "1st, 2nd and 4th papers above"
    #
    # becomes:
    # [1, 2, 4]
    reference_ordinals: list[int] = Field(
        default_factory=list
    )


class IdentifierExtractionResult(BaseModel):
    """Complete Module 5 extraction result."""

    document_id: str

    go_numbers: list[ExtractedIdentifier] = Field(
        default_factory=list
    )

    issue_dates: list[ExtractedIdentifier] = Field(
        default_factory=list
    )

    departments: list[ExtractedIdentifier] = Field(
        default_factory=list
    )

    references: list[ExtractedReference] = Field(
        default_factory=list
    )

    relationships: list[ExtractedRelationship] = Field(
        default_factory=list
    )

    review_flags: list[str] = Field(
        default_factory=list
    )