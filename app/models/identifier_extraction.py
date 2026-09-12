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


class ExtractedRelationship(BaseModel):
    """A relationship signal detected in Government Order text."""

    relationship_type: RelationshipType
    matched_phrase: str
    page_number: int | None = None


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

    relationships: list[ExtractedRelationship] = Field(
        default_factory=list
    )

    review_flags: list[str] = Field(
        default_factory=list
    )