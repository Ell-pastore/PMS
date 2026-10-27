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


class StaffProfile(TimestampMixin, Base):
    """Staff information kept separately from the user account."""

    __tablename__ = "staff_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_staff_profiles_membership",
        ),
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_staff_profiles_department_university",
        ),
        UniqueConstraint("id", "university_id", name="uq_staff_profiles_id_university"),
        UniqueConstraint("university_id", "staff_id", name="uq_staff_profiles_university_staff_id"),
        CheckConstraint(
            "gender IS NULL OR gender IN ('female', 'male', 'non_binary', 'undisclosed')",
            name="ck_staff_profiles_gender",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    staff_id: Mapped[str] = mapped_column(String(64), nullable=False)
    department_id: Mapped[int] = mapped_column(
        nullable=False,
    )
    job_title: Mapped[str] = mapped_column(String(128), nullable=False)
    academic_designation: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(back_populates="staff_profile")
    department: Mapped["Department"] = relationship(back_populates="staff_profiles")
