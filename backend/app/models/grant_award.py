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


class GrantAward(TimestampMixin, Base):
    __tablename__ = "grant_awards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "university_id"],
            ["grant_applications.id", "grant_applications.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_awards_application_university",
        ),
        ForeignKeyConstraint(
            ["approved_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_awards_approved_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_grant_awards_id_university"),
        UniqueConstraint("application_id", name="uq_grant_awards_application"),
        UniqueConstraint("award_reference", name="uq_grant_awards_reference"),
        CheckConstraint("awarded_amount >= 0", name="ck_grant_awards_amount"),
        CheckConstraint("award_end_date >= award_start_date", name="ck_grant_awards_dates"),
        CheckConstraint("status IN ('active', 'closed', 'cancelled')", name="ck_grant_awards_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    award_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    awarded_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    award_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    award_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    approved_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application: Mapped["GrantApplication"] = relationship(back_populates="award")
    approved_by: Mapped["User"] = relationship(foreign_keys=[approved_by_id])
    allocations: Mapped[list["GrantProjectAllocation"]] = relationship(back_populates="award", passive_deletes=True, overlaps="project")
    expenditures: Mapped[list["GrantExpenditure"]] = relationship(back_populates="award", passive_deletes=True, overlaps="project")
    reports: Mapped[list["GrantProgressReport"]] = relationship(back_populates="award", passive_deletes=True)

class GrantProjectAllocation(Base):
    __tablename__ = "grant_project_allocations"
    __table_args__ = (
        ForeignKeyConstraint(["award_id", "university_id"], ["grant_awards.id", "grant_awards.university_id"], ondelete="RESTRICT", name="fk_grant_allocations_award_university"),
        ForeignKeyConstraint(["project_id", "university_id"], ["research_projects.id", "research_projects.university_id"], ondelete="RESTRICT", name="fk_grant_allocations_project_university"),
        ForeignKeyConstraint(["created_by_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_allocations_created_by_membership"),
        UniqueConstraint("award_id", "project_id", name="uq_grant_project_allocations_award_project"),
        CheckConstraint("allocated_amount >= 0", name="ck_grant_project_allocations_amount"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    award_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    award: Mapped["GrantAward"] = relationship(back_populates="allocations", overlaps="project")
    project: Mapped["ResearchProject"] = relationship(overlaps="award,allocations")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])

class GrantExpenditure(Base):
    __tablename__ = "grant_expenditures"
    __table_args__ = (
        ForeignKeyConstraint(["award_id", "university_id"], ["grant_awards.id", "grant_awards.university_id"], ondelete="RESTRICT", name="fk_grant_expenditures_award_university"),
        ForeignKeyConstraint(["project_id", "university_id"], ["research_projects.id", "research_projects.university_id"], ondelete="RESTRICT", name="fk_grant_expenditures_project_university"),
        ForeignKeyConstraint(["recorded_by_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_expenditures_recorded_by_membership"),
        CheckConstraint("amount >= 0", name="ck_grant_expenditures_amount"),
        CheckConstraint("status IN ('draft', 'submitted', 'approved', 'rejected', 'paid', 'voided')", name="ck_grant_expenditures_status"),
        Index("ix_grant_expenditures_award_date", "award_id", "expenditure_date"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    award_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expenditure_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    award: Mapped["GrantAward"] = relationship(back_populates="expenditures", overlaps="project")
    project: Mapped[Optional["ResearchProject"]] = relationship(overlaps="award,expenditures")
    recorded_by: Mapped["User"] = relationship(foreign_keys=[recorded_by_id])

class GrantProgressReport(Base):
    __tablename__ = "grant_progress_reports"
    __table_args__ = (
        ForeignKeyConstraint(["award_id", "university_id"], ["grant_awards.id", "grant_awards.university_id"], ondelete="RESTRICT", name="fk_grant_reports_award_university"),
        ForeignKeyConstraint(["submitter_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_reports_submitter_membership"),
        CheckConstraint("period_end >= period_start", name="ck_grant_progress_reports_period"),
        CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected')", name="ck_grant_progress_reports_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    award_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    financial_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    award: Mapped["GrantAward"] = relationship(back_populates="reports")
    submitter: Mapped["User"] = relationship(foreign_keys=[submitter_id])
