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


class ApprovalWorkflow(TimestampMixin, Base):
    __tablename__ = "approval_workflows"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "university_id"],
            ["departments.id", "departments.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_workflows_department_university",
        ),
        ForeignKeyConstraint(
            ["created_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_workflows_created_by_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_approval_workflows_id_university"),
        UniqueConstraint(
            "workflow_type",
            "university_id",
            "department_id",
            "version",
            name="uq_approval_workflows_scope_version",
        ),
        CheckConstraint("version > 0", name="ck_approval_workflows_version"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(128), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    department: Mapped[Optional["Department"]] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    steps: Mapped[list["ApprovalWorkflowStep"]] = relationship(back_populates="workflow", passive_deletes=True)
    instances: Mapped[list["ApprovalInstance"]] = relationship(back_populates="workflow", passive_deletes=True)

class ApprovalWorkflowStep(Base):
    __tablename__ = "approval_workflow_steps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_id", "university_id"],
            ["approval_workflows.id", "approval_workflows.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_workflow_steps_workflow_university",
        ),
        UniqueConstraint("id", "workflow_id", name="uq_approval_workflow_steps_id_workflow"),
        UniqueConstraint("workflow_id", "step_number", name="uq_approval_workflow_steps_number"),
        CheckConstraint("step_number > 0", name="ck_approval_workflow_steps_number"),
        CheckConstraint("required_approvals > 0", name="ck_approval_workflow_steps_required"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=True)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    workflow: Mapped["ApprovalWorkflow"] = relationship(back_populates="steps")
    required_role: Mapped[Optional["Role"]] = relationship()
    actions: Mapped[list["ApprovalAction"]] = relationship(back_populates="step", passive_deletes=True, overlaps="instance,actions")

class ApprovalInstance(Base):
    __tablename__ = "approval_instances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_id", "university_id"],
            ["approval_workflows.id", "approval_workflows.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_instances_workflow_university",
        ),
        ForeignKeyConstraint(
            ["initiated_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_instances_initiator_membership",
        ),
        UniqueConstraint("id", "workflow_id", name="uq_approval_instances_id_workflow"),
        UniqueConstraint("id", "university_id", name="uq_approval_instances_id_university"),
        CheckConstraint("status IN ('pending', 'in_progress', 'approved', 'rejected', 'cancelled')", name="ck_approval_instances_status"),
        Index("ix_approval_instances_target", "target_entity_type", "target_entity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    initiated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped["ApprovalWorkflow"] = relationship(back_populates="instances")
    initiated_by: Mapped["User"] = relationship(foreign_keys=[initiated_by_id])
    actions: Mapped[list["ApprovalAction"]] = relationship(back_populates="instance", passive_deletes=True, overlaps="step,actions")

class ApprovalAction(Base):
    __tablename__ = "approval_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["instance_id", "workflow_id"],
            ["approval_instances.id", "approval_instances.workflow_id"],
            ondelete="RESTRICT",
            name="fk_approval_actions_instance_workflow",
        ),
        ForeignKeyConstraint(
            ["step_id", "workflow_id"],
            ["approval_workflow_steps.id", "approval_workflow_steps.workflow_id"],
            ondelete="RESTRICT",
            name="fk_approval_actions_step_workflow",
        ),
        ForeignKeyConstraint(
            ["workflow_id", "university_id"],
            ["approval_workflows.id", "approval_workflows.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_actions_workflow_university",
        ),
        ForeignKeyConstraint(
            ["acting_user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_actions_actor_membership",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    instance_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    acting_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    instance: Mapped["ApprovalInstance"] = relationship(back_populates="actions", overlaps="step,actions")
    step: Mapped["ApprovalWorkflowStep"] = relationship(back_populates="actions", overlaps="instance,actions")
    acting_user: Mapped["User"] = relationship(foreign_keys=[acting_user_id])
