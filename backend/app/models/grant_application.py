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


class GrantApplication(TimestampMixin, Base):
    __tablename__ = "grant_applications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["opportunity_id", "university_id"],
            ["grant_opportunities.id", "grant_opportunities.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_applications_opportunity_university",
        ),
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_applications_project_university",
        ),
        ForeignKeyConstraint(
            ["applicant_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_grant_applications_applicant_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_grant_applications_id_university"),
        CheckConstraint("requested_amount >= 0", name="ck_grant_applications_amount"),
        CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'withdrawn')", name="ck_grant_applications_status"),
        Index("ix_grant_applications_opportunity_status", "opportunity_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    proposal: Mapped[str] = mapped_column(Text, nullable=False)
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    opportunity: Mapped["GrantOpportunity"] = relationship(back_populates="applications", overlaps="project")
    applicant: Mapped["User"] = relationship(foreign_keys=[applicant_id])
    project: Mapped[Optional["ResearchProject"]] = relationship(overlaps="opportunity,applications")
    participants: Mapped[list["GrantApplicationParticipant"]] = relationship(back_populates="application", passive_deletes=True)
    reviews: Mapped[list["GrantApplicationReview"]] = relationship(back_populates="application", passive_deletes=True)
    status_history: Mapped[list["GrantApplicationStatusHistory"]] = relationship(back_populates="application", passive_deletes=True)
    award: Mapped[Optional["GrantAward"]] = relationship(back_populates="application", uselist=False, passive_deletes=True)

class GrantApplicationParticipant(Base):
    __tablename__ = "grant_application_participants"
    __table_args__ = (
        ForeignKeyConstraint(["application_id", "university_id"], ["grant_applications.id", "grant_applications.university_id"], ondelete="RESTRICT", name="fk_grant_application_participants_application_university"),
        ForeignKeyConstraint(["user_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_application_participants_user_membership"),
        UniqueConstraint("application_id", "user_id", name="uq_grant_application_participants_application_user"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    participation_role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application: Mapped["GrantApplication"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()

class GrantApplicationReview(Base):
    __tablename__ = "grant_application_reviews"
    __table_args__ = (
        ForeignKeyConstraint(["application_id", "university_id"], ["grant_applications.id", "grant_applications.university_id"], ondelete="RESTRICT", name="fk_grant_application_reviews_application_university"),
        ForeignKeyConstraint(["reviewer_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_application_reviews_reviewer_membership"),
        CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name="ck_grant_application_reviews_decision"),
        CheckConstraint("recommended_amount IS NULL OR recommended_amount >= 0", name="ck_grant_application_reviews_amount"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    recommended_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application: Mapped["GrantApplication"] = relationship(back_populates="reviews")
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])

class GrantApplicationStatusHistory(Base):
    __tablename__ = "grant_application_status_history"
    __table_args__ = (
        ForeignKeyConstraint(["application_id", "university_id"], ["grant_applications.id", "grant_applications.university_id"], ondelete="RESTRICT", name="fk_grant_application_history_application_university"),
        ForeignKeyConstraint(["actor_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_grant_application_history_actor_membership"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    application: Mapped["GrantApplication"] = relationship(back_populates="status_history")
    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])
