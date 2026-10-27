"""Academic department model."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Department(TimestampMixin, Base):
    """An academic department belonging to exactly one faculty."""

    __tablename__ = "departments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["faculty_id", "university_id"],
            ["faculties.id", "faculties.university_id"],
            ondelete="RESTRICT",
            name="fk_departments_faculty_university",
        ),
        UniqueConstraint("id", "university_id", name="uq_departments_id_university"),
        UniqueConstraint("university_id", "faculty_id", "name", name="uq_departments_faculty_name"),
        UniqueConstraint("university_id", "faculty_id", "code", name="uq_departments_faculty_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    faculty_id: Mapped[int] = mapped_column(
        nullable=False,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    faculty: Mapped["Faculty"] = relationship(back_populates="departments")
    student_profiles: Mapped[list["StudentProfile"]] = relationship(
        back_populates="department",
        passive_deletes=True,
    )
    staff_profiles: Mapped[list["StaffProfile"]] = relationship(
        back_populates="department",
        passive_deletes=True,
    )
