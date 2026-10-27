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


class MilestoneTemplate(TimestampMixin, Base):
    __tablename__ = "milestone_templates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_milestone_templates_department_university",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_milestone_templates_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_milestone_templates_id_university"),
        CheckConstraint("default_duration_days > 0", name="ck_milestone_templates_duration"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    department: Mapped[Optional["Department"]] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="template", passive_deletes=True, overlaps="project")

class ProjectMilestone(TimestampMixin, Base):
    __tablename__ = "project_milestones"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_project_milestones_project_university",
        ),
        ForeignKeyConstraint(
            ["template_id", "university_id"],
            ["milestone_templates.id", "milestone_templates.university_id"],
            ondelete="RESTRICT",
            name="fk_project_milestones_template_university",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_project_milestones_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_project_milestones_id_university"),
        UniqueConstraint("id", "project_id", "university_id", name="uq_project_milestones_id_project_university"),
        UniqueConstraint("project_id", "sequence_number", name="uq_project_milestones_sequence"),
        CheckConstraint("sequence_number > 0", name="ck_project_milestones_sequence"),
        CheckConstraint("status IN ('pending', 'in_progress', 'submitted', 'approved', 'revision_requested', 'overdue', 'completed', 'cancelled')", name="ck_project_milestones_status"),
        CheckConstraint("completed_at IS NULL OR status = 'completed'", name="ck_project_milestones_completed"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    project: Mapped["ResearchProject"] = relationship(back_populates="milestones", overlaps="template,milestones")
    template: Mapped[Optional["MilestoneTemplate"]] = relationship(back_populates="milestones", overlaps="project,milestones")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    progress_reports: Mapped[list["ProgressReport"]] = relationship(back_populates="milestone", passive_deletes=True)
    comments: Mapped[list["ProjectComment"]] = relationship(back_populates="milestone", foreign_keys="ProjectComment.milestone_id", passive_deletes=True)
