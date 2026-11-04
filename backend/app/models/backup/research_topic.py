"""PMS SQLAlchemy models for this domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin


def _uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class ResearchTopic(TimestampMixin, Base):
    __tablename__ = "research_topics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_research_topics_department_university",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_research_topics_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_research_topics_id_university"),
        Index("ix_research_topics_normalized_title", "normalized_title"),
        Index("ix_research_topics_department_status", "department_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_id: Mapped[int] = mapped_column(nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    department: Mapped["Department"] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    proposals: Mapped[list["ResearchProposal"]] = relationship(back_populates="topic", passive_deletes=True, overlaps="department")
