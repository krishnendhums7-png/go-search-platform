"""SQLAlchemy models for Government Order metadata and relationships."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class GovernmentOrderModel(Base):
    """Represent Government Order metadata."""

    __tablename__ = "government_orders"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    document_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    go_number: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    outgoing_relationships: Mapped[list["GORelationshipModel"]] = relationship(
        foreign_keys="GORelationshipModel.source_go_id",
        back_populates="source_go",
        cascade="all, delete-orphan",
    )

    incoming_relationships: Mapped[list["GORelationshipModel"]] = relationship(
        foreign_keys="GORelationshipModel.target_go_id",
        back_populates="target_go",
        cascade="all, delete-orphan",
    )


class GORelationshipModel(Base):
    """Represent a directed relationship between Government Orders."""

    __tablename__ = "go_relationships"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    source_go_id: Mapped[UUID] = mapped_column(
        ForeignKey("government_orders.id"),
        nullable=False,
        index=True,
    )

    target_go_id: Mapped[UUID] = mapped_column(
        ForeignKey("government_orders.id"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    matched_phrase: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_go: Mapped[GovernmentOrderModel] = relationship(
        foreign_keys=[source_go_id],
        back_populates="outgoing_relationships",
    )

    target_go: Mapped[GovernmentOrderModel] = relationship(
        foreign_keys=[target_go_id],
        back_populates="incoming_relationships",
    )