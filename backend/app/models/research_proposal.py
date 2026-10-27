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


class ResearchProposal(TimestampMixin, Base):
    __tablename__ = "research_proposals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["topic_id", "university_id"],
            ["research_topics.id", "research_topics.university_id"],
            ondelete="RESTRICT",
            name="fk_research_proposals_topic_university",
        ),
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_research_proposals_department_university",
        ),
        ForeignKeyConstraint(
            ["submitting_user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_research_proposals_submitter_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_research_proposals_id_university"),
        CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected', 'withdrawn')", name="ck_research_proposals_status"),
        CheckConstraint("submitted_at IS NULL OR status <> 'draft'", name="ck_research_proposals_submission"),
        Index("ix_research_proposals_department_status", "department_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    submitting_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    research_problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objectives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_outcomes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    topic: Mapped["ResearchTopic"] = relationship(back_populates="proposals", overlaps="department")
    submitting_user: Mapped["User"] = relationship(foreign_keys=[submitting_user_id])
    department: Mapped["Department"] = relationship(overlaps="topic")
    participants: Mapped[list["ProposalParticipant"]] = relationship(back_populates="proposal", passive_deletes=True, overlaps="student")
    revisions: Mapped[list["ProposalRevision"]] = relationship(back_populates="proposal", passive_deletes=True)
    supervisors: Mapped[list["ProposalSupervisor"]] = relationship(back_populates="proposal", passive_deletes=True, overlaps="staff")
    reviews: Mapped[list["ProposalReview"]] = relationship(back_populates="proposal", passive_deletes=True)
    status_history: Mapped[list["ProposalStatusHistory"]] = relationship(back_populates="proposal", passive_deletes=True)

class ProposalRevision(Base):
    __tablename__ = "proposal_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_revisions_proposal_university",
        ),
        ForeignKeyConstraint(
            ["submitted_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_revisions_submitter_membership",
        ),
        UniqueConstraint("proposal_id", "revision_number", name="uq_proposal_revisions_number"),
        CheckConstraint("revision_number > 0", name="ck_proposal_revisions_number"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    research_problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objectives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_outcomes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    proposal: Mapped["ResearchProposal"] = relationship(back_populates="revisions")
    submitted_by: Mapped["User"] = relationship(foreign_keys=[submitted_by_id])

class ProposalParticipant(Base):
    __tablename__ = "proposal_participants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_participants_proposal_university",
        ),
        ForeignKeyConstraint(
            ["student_id", "university_id"],
            ["student_profiles.id", "student_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_participants_student_university",
        ),
        UniqueConstraint("proposal_id", "student_id", name="uq_proposal_participants_proposal_student"),
        Index("uq_proposal_participants_lead", "proposal_id", unique=True, postgresql_where=text("is_lead = true")),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    student_id: Mapped[int] = mapped_column(nullable=False)
    participation_role: Mapped[str] = mapped_column(String(64), nullable=False)
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    proposal: Mapped["ResearchProposal"] = relationship(back_populates="participants", overlaps="student,participants")
    student: Mapped["StudentProfile"] = relationship(overlaps="proposal,participants")

class ProposalSupervisor(Base):
    __tablename__ = "proposal_supervisors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_supervisors_proposal_university",
        ),
        ForeignKeyConstraint(
            ["staff_id", "university_id"],
            ["staff_profiles.id", "staff_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_supervisors_staff_university",
        ),
        ForeignKeyConstraint(
            ["assigned_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_supervisors_assigned_by_membership",
        ),
        Index("uq_proposal_supervisors_active", "proposal_id", "staff_id", unique=True, postgresql_where=text("ended_at IS NULL")),
        Index("uq_proposal_supervisors_primary_active", "proposal_id", unique=True, postgresql_where=text("assignment_role = 'primary' AND ended_at IS NULL")),
        CheckConstraint("assignment_role IN ('primary', 'co_supervisor')", name="ck_proposal_supervisors_role"),
        CheckConstraint("ended_at IS NULL OR ended_at >= assigned_at", name="ck_proposal_supervisors_dates"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    staff_id: Mapped[int] = mapped_column(nullable=False)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    proposal: Mapped["ResearchProposal"] = relationship(back_populates="supervisors", overlaps="staff,supervisors")
    staff: Mapped["StaffProfile"] = relationship(overlaps="proposal,supervisors")
    assigned_by: Mapped["User"] = relationship(foreign_keys=[assigned_by_id])

class ProposalReview(Base):
    __tablename__ = "proposal_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_reviews_proposal_university",
        ),
        ForeignKeyConstraint(
            ["reviewer_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_reviews_reviewer_membership",
        ),
        CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name="ck_proposal_reviews_decision"),
        Index("ix_proposal_reviews_proposal_reviewed_at", "proposal_id", "reviewed_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    proposal: Mapped["ResearchProposal"] = relationship(back_populates="reviews")
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])

class ProposalStatusHistory(Base):
    __tablename__ = "proposal_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_history_proposal_university",
        ),
        ForeignKeyConstraint(
            ["actor_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_proposal_history_actor_membership",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    proposal: Mapped["ResearchProposal"] = relationship(back_populates="status_history")
    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])
