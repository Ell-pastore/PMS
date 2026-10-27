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


class GrantOpportunity(TimestampMixin, Base):
    __tablename__ = "grant_opportunities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_opportunities_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_grant_opportunities_id_university"),
        CheckConstraint("application_closes_at >= application_opens_at", name="ck_grant_opportunities_dates"),
        CheckConstraint("min_funding_amount >= 0", name="ck_grant_opportunities_min_amount"),
        CheckConstraint("max_funding_amount IS NULL OR max_funding_amount >= min_funding_amount", name="ck_grant_opportunities_max_amount"),
        CheckConstraint("status IN ('draft', 'open', 'closed', 'awarded', 'cancelled')", name="ck_grant_opportunities_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funding_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    eligibility_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    application_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    min_funding_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    max_funding_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    applications: Mapped[list["GrantApplication"]] = relationship(back_populates="opportunity", passive_deletes=True, overlaps="project")


# Backward-compatible domain vocabulary without defining a second table.
FundingOpportunity = GrantOpportunity
