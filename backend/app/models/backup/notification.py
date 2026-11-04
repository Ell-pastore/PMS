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


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recipient_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_notifications_recipient_membership",
        ),
        Index("ix_notifications_recipient_unread_created", "recipient_id", "read_at", "created_at"),
        Index("ix_notifications_recipient_created", "recipient_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient: Mapped["User"] = relationship()


class NotificationPreference(TimestampMixin, Base):
    """Per-user, per-university preferences for in-app notifications."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_notification_preferences_membership",
        ),
        UniqueConstraint(
            "user_id",
            "university_id",
            "notification_type",
            "channel",
            name="uq_notification_preferences_user_university_type_channel",
        ),
        CheckConstraint(
            "length(btrim(notification_type)) > 0",
            name="ck_notification_preferences_type_nonempty",
        ),
        CheckConstraint(
            "channel = 'in_app'",
            name="ck_notification_preferences_channel",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="in_app",
        server_default="in_app",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    user: Mapped["User"] = relationship(back_populates="notification_preferences")
    university: Mapped["University"] = relationship(back_populates="notification_preferences")
