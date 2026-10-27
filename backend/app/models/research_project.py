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


class ResearchProject(TimestampMixin, Base):
    __tablename__ = "research_projects"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id", "university_id"],
            ["research_proposals.id", "research_proposals.university_id"],
            ondelete="RESTRICT",
            name="fk_research_projects_proposal_university",
        ),
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_research_projects_department_university",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_research_projects_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_research_projects_id_university"),
        CheckConstraint("status IN ('active', 'on_hold', 'completed', 'cancelled', 'archived')", name="ck_research_projects_status"),
        CheckConstraint("expected_end_date IS NULL OR expected_end_date >= start_date", name="ck_research_projects_dates"),
        CheckConstraint("actual_end_date IS NULL OR actual_end_date >= start_date", name="ck_research_projects_actual_end"),
        Index("ix_research_projects_department_status", "department_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    department_id: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    proposal: Mapped["ResearchProposal"] = relationship(overlaps="department")
    department: Mapped["Department"] = relationship(overlaps="proposal")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    participants: Mapped[list["ProjectParticipant"]] = relationship(back_populates="project", passive_deletes=True, overlaps="student")
    supervisors: Mapped[list["ProjectSupervisor"]] = relationship(back_populates="project", passive_deletes=True, overlaps="staff")
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="project", passive_deletes=True, overlaps="template,milestones")
    progress_reports: Mapped[list["ProgressReport"]] = relationship(back_populates="project", passive_deletes=True, overlaps="milestone,progress_reports")
    comments: Mapped[list["ProjectComment"]] = relationship(back_populates="project", foreign_keys="ProjectComment.project_id", passive_deletes=True)
    status_history: Mapped[list["ProjectStatusHistory"]] = relationship(back_populates="project", passive_deletes=True)
    publications: Mapped[list["PublicationProject"]] = relationship(back_populates="project", passive_deletes=True, overlaps="publication,projects")

class ProjectParticipant(Base):
    __tablename__ = "project_participants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_project_participants_project_university",
        ),
        ForeignKeyConstraint(
            ["student_id", "university_id"],
            ["student_profiles.id", "student_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_project_participants_student_university",
        ),
        Index("uq_project_participants_active_student", "project_id", "student_id", unique=True, postgresql_where=text("ended_at IS NULL")),
        Index("uq_project_participants_active_lead", "project_id", unique=True, postgresql_where=text("is_lead = true AND ended_at IS NULL")),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_project_participants_dates"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    student_id: Mapped[int] = mapped_column(nullable=False)
    participation_role: Mapped[str] = mapped_column(String(64), nullable=False)
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project: Mapped["ResearchProject"] = relationship(back_populates="participants", overlaps="student,participants")
    student: Mapped["StudentProfile"] = relationship(overlaps="project,participants")

class ProjectSupervisor(Base):
    __tablename__ = "project_supervisors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_project_supervisors_project_university",
        ),
        ForeignKeyConstraint(
            ["staff_id", "university_id"],
            ["staff_profiles.id", "staff_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_project_supervisors_staff_university",
        ),
        ForeignKeyConstraint(
            ["assigned_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_project_supervisors_assigned_by_membership",
        ),
        Index("uq_project_supervisors_active_staff", "project_id", "staff_id", unique=True, postgresql_where=text("ended_at IS NULL")),
        Index("uq_project_supervisors_primary_active", "project_id", unique=True, postgresql_where=text("assignment_role = 'primary' AND ended_at IS NULL")),
        CheckConstraint("assignment_role IN ('primary', 'co_supervisor')", name="ck_project_supervisors_role"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_project_supervisors_dates"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    staff_id: Mapped[int] = mapped_column(nullable=False)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project: Mapped["ResearchProject"] = relationship(back_populates="supervisors", overlaps="staff,supervisors")
    staff: Mapped["StaffProfile"] = relationship(overlaps="project,supervisors")
    assigned_by: Mapped["User"] = relationship(foreign_keys=[assigned_by_id])

class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_project_history_project_university",
        ),
        ForeignKeyConstraint(
            ["actor_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_project_history_actor_membership",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project: Mapped["ResearchProject"] = relationship(back_populates="status_history")
    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])
