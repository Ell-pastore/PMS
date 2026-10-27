"""User accounts and account-verification records."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin


class AccountStatus(str, Enum):
    """Lifecycle states supported for a user account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(TimestampMixin, Base):
    """Core account shared by students and staff."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        SqlEnum(
            AccountStatus,
            native_enum=False,
            length=32,
            values_callable=lambda enum_type: [member.value for member in enum_type],
            create_constraint=False,
            name="account_status",
        ),
        nullable=False,
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="account_status",
        ),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        foreign_keys="UserRole.user_id",
        passive_deletes=True,
    )
    student_profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user",
        uselist=False,
        passive_deletes=True,
    )
    staff_profile: Mapped[Optional["StaffProfile"]] = relationship(
        back_populates="user",
        uselist=False,
        passive_deletes=True,
    )
    account_verifications: Mapped[list["AccountVerification"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    university_memberships: Mapped[list["UniversityMembership"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        """Keep ORM-assigned email addresses canonical for reliable lookup."""

        return value.strip().casefold()


class AccountVerification(Base):
    __tablename__ = "account_verifications"
    __table_args__ = (
        Index("ix_account_verifications_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="account_verifications")
