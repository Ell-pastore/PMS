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


class University(TimestampMixin, Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = _uuid_column()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    faculties: Mapped[list["Faculty"]] = relationship(back_populates="university", passive_deletes=True)
    memberships: Mapped[list["UniversityMembership"]] = relationship(back_populates="university", passive_deletes=True)
    settings: Mapped[Optional["UniversitySettings"]] = relationship(back_populates="university", uselist=False, passive_deletes=True)
    notification_preferences: Mapped[list["NotificationPreference"]] = relationship(
        back_populates="university",
        passive_deletes=True,
    )

class UniversityMembership(TimestampMixin, Base):
    """A university membership whose active state is an authorization concern.

    Foreign keys intentionally validate that historical records point to a
    membership that exists; service operations must separately require
    ``is_active`` when granting access or creating new university-scoped work.
    Deactivation therefore preserves historical references.
    """

    __tablename__ = "university_memberships"
    __table_args__ = (
        UniqueConstraint("university_id", "user_id", name="uq_university_memberships_university_user"),
        UniqueConstraint("user_id", "university_id", name="uq_university_memberships_user_university"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    university: Mapped["University"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="university_memberships")
