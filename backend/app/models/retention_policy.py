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


class RetentionPolicy(TimestampMixin, Base):
    __tablename__ = "retention_policies"
    __table_args__ = (
        ForeignKeyConstraint(["department_id", "university_id"], ["departments.id", "departments.university_id"], ondelete="RESTRICT", name="fk_retention_policies_department_university"),
        ForeignKeyConstraint(["created_by_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_retention_policies_created_by_membership"),
        Index("uq_retention_policies_university_category_global", "university_id", "record_category", unique=True, postgresql_where=text("department_id IS NULL")),
        Index("uq_retention_policies_university_category_department", "university_id", "record_category", "department_id", unique=True, postgresql_where=text("department_id IS NOT NULL")),
        CheckConstraint("retention_days > 0", name="ck_retention_policies_days"),
        CheckConstraint("post_retention_action IN ('review', 'archive', 'anonymize', 'delete')", name="ck_retention_policies_action"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    record_category: Mapped[str] = mapped_column(String(128), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    post_retention_action: Mapped[str] = mapped_column(String(32), nullable=False, default="review", server_default="review")
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    department: Mapped[Optional["Department"]] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
