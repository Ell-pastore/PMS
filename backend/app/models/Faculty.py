"""University faculty model."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Faculty(TimestampMixin, Base):
    """A university faculty containing academic departments."""

    __tablename__ = "faculties"
    __table_args__ = (
        UniqueConstraint("id", "university_id", name="uq_faculties_id_university"),
        UniqueConstraint("university_id", "code", name="uq_faculties_university_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    departments: Mapped[list["Department"]] = relationship(
        back_populates="faculty",
        passive_deletes=True,
    )
    university: Mapped["University"] = relationship(back_populates="faculties")
