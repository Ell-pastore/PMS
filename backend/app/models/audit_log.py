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


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["acting_user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_audit_logs_actor_membership",
        ),
        CheckConstraint(
            """
            (entity_uuid IS NULL AND entity_integer IS NULL)
            OR (
                entity_uuid IS NULL
                AND entity_integer IS NOT NULL
                AND entity_type IN (
                    'users', 'roles', 'user_roles', 'faculties',
                    'departments', 'student_profiles', 'staff_profiles'
                )
            )
            OR (
                entity_uuid IS NOT NULL
                AND entity_integer IS NULL
                AND entity_type NOT IN (
                    'users', 'roles', 'user_roles', 'faculties',
                    'departments', 'student_profiles', 'staff_profiles'
                )
            )
            """,
            name="ck_audit_logs_entity_identifier_type",
        ),
        Index(
            "ix_audit_logs_entity_uuid_event",
            "entity_type",
            "entity_uuid",
            "event_at",
            postgresql_where=text("entity_uuid IS NOT NULL"),
        ),
        Index(
            "ix_audit_logs_entity_integer_event",
            "entity_type",
            "entity_integer",
            "event_at",
            postgresql_where=text("entity_integer IS NOT NULL"),
        ),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    acting_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_uuid: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    entity_integer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    audit_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    acting_user: Mapped[Optional["User"]] = relationship(foreign_keys=[acting_user_id])
