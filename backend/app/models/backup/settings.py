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


class DepartmentLeadership(TimestampMixin, Base):
    __tablename__ = "department_leadership"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_department_leadership_department_university",
        ),
        ForeignKeyConstraint(
            ["staff_id", "department_id", "university_id"],
            ["staff_profiles.id", "staff_profiles.department_id", "staff_profiles.university_id"],
            ondelete="RESTRICT",
            name="fk_department_leadership_staff_department_university",
        ),
        ForeignKeyConstraint(
            ["appointed_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_department_leadership_appointed_by_membership",
        ),
        Index(
            "uq_department_leadership_active",
            "department_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_department_leadership_dates"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[int] = mapped_column(nullable=False)
    staff_id: Mapped[int] = mapped_column(nullable=False)
    appointed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    department: Mapped["Department"] = relationship(overlaps="staff")
    staff: Mapped["StaffProfile"] = relationship(overlaps="department")
    appointed_by: Mapped["User"] = relationship(foreign_keys=[appointed_by_id])

class UniversitySettings(TimestampMixin, Base):
    __tablename__ = "university_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["updated_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_university_settings_updated_by_membership",
        ),
        CheckConstraint("max_supervisors_per_project > 0", name="ck_university_settings_supervisors"),
        CheckConstraint("max_active_projects_per_student > 0", name="ck_university_settings_projects"),
        CheckConstraint("max_active_supervisees_per_supervisor > 0", name="ck_university_settings_supervisees"),
        CheckConstraint("student_inactivity_days > 0", name="ck_university_settings_inactivity"),
        CheckConstraint("milestone_reminder_days >= 0", name="ck_university_settings_reminder"),
        CheckConstraint("default_proposal_review_days > 0", name="ck_university_settings_review"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False, unique=True)
    max_supervisors_per_project: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_active_projects_per_student: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_active_supervisees_per_supervisor: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    student_inactivity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    milestone_reminder_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    default_proposal_review_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    university: Mapped["University"] = relationship(back_populates="settings")
    updated_by: Mapped[Optional["User"]] = relationship(foreign_keys=[updated_by_id])

class DepartmentSettings(TimestampMixin, Base):
    __tablename__ = "department_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_department_settings_department_university",
        ),
        ForeignKeyConstraint(
            ["updated_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_department_settings_updated_by_membership",
        ),
        UniqueConstraint("department_id", name="uq_department_settings_department"),
        CheckConstraint("max_supervisors_per_project IS NULL OR max_supervisors_per_project > 0", name="ck_department_settings_supervisors"),
        CheckConstraint("max_active_projects_per_student IS NULL OR max_active_projects_per_student > 0", name="ck_department_settings_projects"),
        CheckConstraint("max_active_supervisees_per_supervisor IS NULL OR max_active_supervisees_per_supervisor > 0", name="ck_department_settings_supervisees"),
        CheckConstraint("student_inactivity_days IS NULL OR student_inactivity_days > 0", name="ck_department_settings_inactivity"),
        CheckConstraint("milestone_reminder_days IS NULL OR milestone_reminder_days >= 0", name="ck_department_settings_reminder"),
        CheckConstraint("default_proposal_review_days IS NULL OR default_proposal_review_days > 0", name="ck_department_settings_review"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[int] = mapped_column(nullable=False)
    max_supervisors_per_project: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_active_projects_per_student: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_active_supervisees_per_supervisor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    student_inactivity_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    milestone_reminder_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    default_proposal_review_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    department: Mapped["Department"] = relationship()
    updated_by: Mapped[Optional["User"]] = relationship(foreign_keys=[updated_by_id])

class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["updated_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_system_settings_updated_by_membership",
        ),
        UniqueConstraint("university_id", "setting_key", name="uq_system_settings_university_key"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    setting_key: Mapped[str] = mapped_column(String(128), nullable=False)
    setting_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    university: Mapped["University"] = relationship()
    updated_by: Mapped["User"] = relationship(foreign_keys=[updated_by_id])
