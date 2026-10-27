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


class ProgressReport(TimestampMixin, Base):
    __tablename__ = "progress_reports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_progress_reports_project_university",
        ),
        ForeignKeyConstraint(
            ["milestone_id", "university_id"],
            ["project_milestones.id", "project_milestones.university_id"],
            ondelete="RESTRICT",
            name="fk_progress_reports_milestone_university",
        ),
        ForeignKeyConstraint(
            ["submitter_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_progress_reports_submitter_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_progress_reports_id_university"),
        CheckConstraint("period_end >= period_start", name="ck_progress_reports_period"),
        CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected')", name="ck_progress_reports_status"),
        Index("ix_progress_reports_project_period", "project_id", "period_start", "period_end"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    challenges: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["ResearchProject"] = relationship(back_populates="progress_reports", overlaps="milestone,progress_reports")
    milestone: Mapped[Optional["ProjectMilestone"]] = relationship(back_populates="progress_reports", overlaps="project,progress_reports")
    submitter: Mapped["User"] = relationship(foreign_keys=[submitter_id])
    reviews: Mapped[list["ProgressReportReview"]] = relationship(back_populates="report", passive_deletes=True)
    comments: Mapped[list["ProjectComment"]] = relationship(back_populates="progress_report", foreign_keys="ProjectComment.progress_report_id", passive_deletes=True)

class ProgressReportReview(Base):
    __tablename__ = "progress_report_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["report_id", "university_id"],
            ["progress_reports.id", "progress_reports.university_id"],
            ondelete="RESTRICT",
            name="fk_progress_report_reviews_report_university",
        ),
        ForeignKeyConstraint(
            ["reviewer_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_progress_report_reviews_reviewer_membership",
        ),
        CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name="ck_progress_report_reviews_decision"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    report_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    report: Mapped["ProgressReport"] = relationship(back_populates="reviews")
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])

class ProjectComment(Base):
    __tablename__ = "project_comments"
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "university_id"], ["research_projects.id", "research_projects.university_id"], ondelete="RESTRICT", name="fk_project_comments_project_university"),
        ForeignKeyConstraint(["milestone_id", "university_id"], ["project_milestones.id", "project_milestones.university_id"], ondelete="RESTRICT", name="fk_project_comments_milestone_university"),
        ForeignKeyConstraint(["progress_report_id", "university_id"], ["progress_reports.id", "progress_reports.university_id"], ondelete="RESTRICT", name="fk_project_comments_report_university"),
        ForeignKeyConstraint(["author_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_project_comments_author_membership"),
        CheckConstraint("num_nonnulls(project_id, milestone_id, progress_report_id) = 1", name="ck_project_comments_one_target"),
        Index("ix_project_comments_project_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    progress_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    project: Mapped[Optional["ResearchProject"]] = relationship(back_populates="comments", foreign_keys=[project_id])
    milestone: Mapped[Optional["ProjectMilestone"]] = relationship(back_populates="comments", foreign_keys=[milestone_id])
    progress_report: Mapped[Optional["ProgressReport"]] = relationship(back_populates="comments", foreign_keys=[progress_report_id])
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

class StudentActivity(Base):
    __tablename__ = "student_activity"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_id", "university_id"],
            ["student_profiles.id", "student_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_student_activity_student_university",
        ),
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_student_activity_project_university",
        ),
        Index("ix_student_activity_student_recorded", "student_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    student: Mapped["StudentProfile"] = relationship(overlaps="project")
    project: Mapped[Optional["ResearchProject"]] = relationship(overlaps="student")
