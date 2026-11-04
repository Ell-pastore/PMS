"""Versioned approval-workflow models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    and_,
    event,
    func,
    inspect,
    select,
    text,
    true,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from .base import Base, TimestampMixin


def _uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class ApprovalWorkflow(TimestampMixin, Base):
    """Stable identity and scope for a family of workflow versions.

    ``active_version_id`` is the single active-version pointer. Its composite
    foreign key proves that the selected version belongs to this workflow and
    university. Publishing and switching that pointer must still happen in one
    service transaction.
    """

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
        ForeignKeyConstraint(
            ["active_version_id", "id", "university_id"],
            [
                "approval_workflow_versions.id",
                "approval_workflow_versions.workflow_id",
                "approval_workflow_versions.university_id",
            ],
            ondelete="RESTRICT",
            name="fk_approval_workflows_active_version",
            use_alter=True,
        ),
        UniqueConstraint("id", "university_id", name="uq_approval_workflows_id_university"),
        Index(
            "uq_approval_workflows_department_scope",
            "workflow_type",
            "university_id",
            "department_id",
            unique=True,
            postgresql_where=text("department_id IS NOT NULL"),
        ),
        Index(
            "uq_approval_workflows_university_scope",
            "workflow_type",
            "university_id",
            unique=True,
            postgresql_where=text("department_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(String(128), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    active_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    department: Mapped[Optional["Department"]] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    versions: Mapped[list["ApprovalWorkflowVersion"]] = relationship(
        back_populates="workflow",
        foreign_keys=lambda: [
            ApprovalWorkflowVersion.workflow_id,
            ApprovalWorkflowVersion.university_id,
        ],
        passive_deletes=True,
    )
    active_version: Mapped[Optional["ApprovalWorkflowVersion"]] = relationship(
        foreign_keys=[active_version_id],
        primaryjoin=lambda: and_(
            ApprovalWorkflow.active_version_id == ApprovalWorkflowVersion.id,
            ApprovalWorkflow.id == ApprovalWorkflowVersion.workflow_id,
            ApprovalWorkflow.university_id == ApprovalWorkflowVersion.university_id,
        ),
        viewonly=True,
        uselist=False,
    )


class ApprovalWorkflowVersion(TimestampMixin, Base):
    """An immutable definition once its publication state becomes published."""

    __tablename__ = "approval_workflow_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_id", "university_id"],
            ["approval_workflows.id", "approval_workflows.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_workflow_versions_workflow_university",
        ),
        UniqueConstraint(
            "id",
            "workflow_id",
            "university_id",
            name="uq_approval_workflow_versions_id_workflow_university",
        ),
        UniqueConstraint(
            "workflow_id",
            "version_number",
            name="uq_approval_workflow_versions_workflow_number",
        ),
        CheckConstraint(
            "publication_state IN ('draft', 'published')",
            name="ck_approval_workflow_versions_publication_state",
        ),
        CheckConstraint("version_number > 0", name="ck_approval_workflow_versions_number"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    publication_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    workflow: Mapped["ApprovalWorkflow"] = relationship(
        back_populates="versions",
        foreign_keys=[workflow_id, university_id],
    )
    steps: Mapped[list["ApprovalWorkflowStep"]] = relationship(
        back_populates="workflow_version",
        passive_deletes=True,
    )
    instances: Mapped[list["ApprovalInstance"]] = relationship(
        back_populates="workflow_version",
        passive_deletes=True,
    )


class ApprovalWorkflowStep(Base):
    """A step owned by exactly one workflow version."""

    __tablename__ = "approval_workflow_steps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_version_id", "workflow_id", "university_id"],
            [
                "approval_workflow_versions.id",
                "approval_workflow_versions.workflow_id",
                "approval_workflow_versions.university_id",
            ],
            ondelete="RESTRICT",
            name="fk_approval_workflow_steps_version_workflow_university",
        ),
        UniqueConstraint(
            "id",
            "workflow_version_id",
            "workflow_id",
            "university_id",
            name="uq_approval_workflow_steps_id_version_workflow_university",
        ),
        UniqueConstraint(
            "workflow_version_id",
            "step_number",
            name="uq_approval_workflow_steps_version_number",
        ),
        CheckConstraint("step_number > 0", name="ck_approval_workflow_steps_number"),
        CheckConstraint("required_approvals > 0", name="ck_approval_workflow_steps_required"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    workflow_version: Mapped["ApprovalWorkflowVersion"] = relationship(
        back_populates="steps",
    )
    required_role: Mapped[Optional["Role"]] = relationship()
    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="step",
        primaryjoin=lambda: and_(
            foreign(ApprovalAction.step_id) == ApprovalWorkflowStep.id,
            ApprovalAction.workflow_version_id == ApprovalWorkflowStep.workflow_version_id,
            ApprovalAction.workflow_id == ApprovalWorkflowStep.workflow_id,
            ApprovalAction.university_id == ApprovalWorkflowStep.university_id,
        ),
        foreign_keys=lambda: [ApprovalAction.step_id],
        passive_deletes=True,
    )


class ApprovalInstance(Base):
    """An approval run tied to one immutable workflow-version definition."""

    __tablename__ = "approval_instances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workflow_version_id", "workflow_id", "university_id"],
            [
                "approval_workflow_versions.id",
                "approval_workflow_versions.workflow_id",
                "approval_workflow_versions.university_id",
            ],
            ondelete="RESTRICT",
            name="fk_approval_instances_version_workflow_university",
        ),
        ForeignKeyConstraint(
            ["initiated_by_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_instances_initiator_membership",
        ),
        UniqueConstraint(
            "id",
            "workflow_version_id",
            "workflow_id",
            "university_id",
            name="uq_approval_instances_id_version_workflow_university",
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'approved', 'rejected', 'cancelled')",
            name="ck_approval_instances_status",
        ),
        Index("ix_approval_instances_target", "target_entity_type", "target_entity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    initiated_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_version: Mapped["ApprovalWorkflowVersion"] = relationship(
        back_populates="instances",
    )
    initiated_by: Mapped["User"] = relationship(foreign_keys=[initiated_by_id])
    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="instance",
        primaryjoin=lambda: and_(
            foreign(ApprovalAction.instance_id) == ApprovalInstance.id,
            ApprovalAction.workflow_version_id == ApprovalInstance.workflow_version_id,
            ApprovalAction.workflow_id == ApprovalInstance.workflow_id,
            ApprovalAction.university_id == ApprovalInstance.university_id,
        ),
        foreign_keys=lambda: [ApprovalAction.instance_id],
        passive_deletes=True,
    )


class ApprovalAction(Base):
    """An action tied to the same version as its instance and step."""

    __tablename__ = "approval_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["instance_id", "workflow_version_id", "workflow_id", "university_id"],
            [
                "approval_instances.id",
                "approval_instances.workflow_version_id",
                "approval_instances.workflow_id",
                "approval_instances.university_id",
            ],
            ondelete="RESTRICT",
            name="fk_approval_actions_instance_version_workflow_university",
        ),
        ForeignKeyConstraint(
            ["step_id", "workflow_version_id", "workflow_id", "university_id"],
            [
                "approval_workflow_steps.id",
                "approval_workflow_steps.workflow_version_id",
                "approval_workflow_steps.workflow_id",
                "approval_workflow_steps.university_id",
            ],
            ondelete="RESTRICT",
            name="fk_approval_actions_step_version_workflow_university",
        ),
        ForeignKeyConstraint(
            ["acting_user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_approval_actions_actor_membership",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    instance_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    acting_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    instance: Mapped["ApprovalInstance"] = relationship(
        back_populates="actions",
        primaryjoin=lambda: and_(
            foreign(ApprovalAction.instance_id) == ApprovalInstance.id,
            ApprovalAction.workflow_version_id == ApprovalInstance.workflow_version_id,
            ApprovalAction.workflow_id == ApprovalInstance.workflow_id,
            ApprovalAction.university_id == ApprovalInstance.university_id,
        ),
        foreign_keys=[instance_id],
    )
    step: Mapped["ApprovalWorkflowStep"] = relationship(
        back_populates="actions",
        primaryjoin=lambda: and_(
            foreign(ApprovalAction.step_id) == ApprovalWorkflowStep.id,
            ApprovalAction.workflow_version_id == ApprovalWorkflowStep.workflow_version_id,
            ApprovalAction.workflow_id == ApprovalWorkflowStep.workflow_id,
            ApprovalAction.university_id == ApprovalWorkflowStep.university_id,
        ),
        foreign_keys=[step_id],
    )
    acting_user: Mapped["User"] = relationship(foreign_keys=[acting_user_id])


def _reject_published_version_update(publication_state: str) -> None:
    if publication_state == "published":
        raise ValueError("Published approval workflow versions are immutable")


def _reject_published_version_delete(publication_state: str) -> None:
    if publication_state == "published":
        raise ValueError("Published approval workflow versions cannot be deleted")


@event.listens_for(ApprovalWorkflowVersion, "before_insert")
def _require_draft_version_on_insert(mapper, connection, target: ApprovalWorkflowVersion) -> None:
    if target.publication_state not in {None, "draft"}:
        raise ValueError("Approval workflow versions must be created as drafts")


@event.listens_for(ApprovalWorkflowVersion, "before_update")
def _prevent_published_version_update(mapper, connection, target: ApprovalWorkflowVersion) -> None:
    history = inspect(target).attrs.publication_state.history
    previous_state = history.deleted[0] if history.deleted else target.publication_state
    _reject_published_version_update(previous_state)


@event.listens_for(ApprovalWorkflowVersion, "before_delete")
def _prevent_published_version_delete(mapper, connection, target: ApprovalWorkflowVersion) -> None:
    _reject_published_version_delete(target.publication_state)


def _version_details(connection, version_id: uuid.UUID):
    return connection.execute(
        select(
            ApprovalWorkflowVersion.workflow_id,
            ApprovalWorkflowVersion.university_id,
            ApprovalWorkflowVersion.publication_state,
        ).where(ApprovalWorkflowVersion.id == version_id)
    ).one_or_none()


def _history_value(target, attribute: str, fallback):
    history = inspect(target).attrs[attribute].history
    return history.deleted[0] if history.deleted else fallback


def _validate_step_version_identity(connection, target: ApprovalWorkflowStep, version_id: uuid.UUID) -> None:
    details = _version_details(connection, version_id)
    if details is None:
        return
    if details.workflow_id != target.workflow_id or details.university_id != target.university_id:
        raise ValueError("Approval workflow steps must retain their workflow and university identity")


def _validate_step_version_transition(
    connection,
    target: ApprovalWorkflowStep,
    old_version_id: uuid.UUID,
) -> None:
    old_details = _version_details(connection, old_version_id)
    new_details = _version_details(connection, target.workflow_version_id)
    if (old_details and old_details.publication_state == "published") or (
        new_details and new_details.publication_state == "published"
    ):
        raise ValueError("Steps belonging to published approval workflow versions are immutable")
    if old_details and (
        old_details.workflow_id != _history_value(target, "workflow_id", target.workflow_id)
        or old_details.university_id != _history_value(target, "university_id", target.university_id)
    ):
        raise ValueError("Approval workflow steps cannot change their original workflow identity")
    _validate_step_version_identity(connection, target, target.workflow_version_id)


@event.listens_for(ApprovalWorkflowStep, "before_update")
def _prevent_published_step_update(mapper, connection, target: ApprovalWorkflowStep) -> None:
    old_version_id = _history_value(target, "workflow_version_id", target.workflow_version_id)
    _validate_step_version_transition(connection, target, old_version_id)


@event.listens_for(ApprovalWorkflowStep, "before_insert")
def _prevent_step_insert_into_published_version(mapper, connection, target: ApprovalWorkflowStep) -> None:
    details = _version_details(connection, target.workflow_version_id)
    if details and details.publication_state == "published":
        raise ValueError("Steps cannot be added to published approval workflow versions")
    _validate_step_version_identity(connection, target, target.workflow_version_id)


@event.listens_for(ApprovalWorkflowStep, "before_delete")
def _prevent_published_step_delete(mapper, connection, target: ApprovalWorkflowStep) -> None:
    details = _version_details(connection, target.workflow_version_id)
    if details and details.publication_state == "published":
        raise ValueError("Steps belonging to published approval workflow versions cannot be deleted")
    if details and (
        details.workflow_id != target.workflow_id or details.university_id != target.university_id
    ):
        raise ValueError("Approval workflow steps cannot be deleted with an inconsistent workflow identity")


def _workflow_has_history(connection, workflow_id: uuid.UUID) -> bool:
    version_exists = connection.execute(
        select(ApprovalWorkflowVersion.id).where(ApprovalWorkflowVersion.workflow_id == workflow_id).limit(1)
    ).first()
    if version_exists is not None:
        return True
    instance_exists = connection.execute(
        select(ApprovalInstance.id).where(ApprovalInstance.workflow_id == workflow_id).limit(1)
    ).first()
    return instance_exists is not None


def _ensure_workflow_identity_mutable(connection, workflow_id: uuid.UUID) -> None:
    if _workflow_has_history(connection, workflow_id):
        raise ValueError("Approval workflow identity cannot change after versions or instances exist")


@event.listens_for(ApprovalWorkflow, "before_update")
def _prevent_workflow_identity_update(mapper, connection, target: ApprovalWorkflow) -> None:
    state = inspect(target)
    identity_fields = ("workflow_type", "department_id", "university_id", "created_by_id")
    if not any(state.attrs[field].history.has_changes() for field in identity_fields):
        return
    _ensure_workflow_identity_mutable(connection, target.id)


def _validate_active_version_pointer(connection, target: ApprovalWorkflow) -> None:
    if target.active_version_id is None:
        return
    row = connection.execute(
        select(
            ApprovalWorkflowVersion.workflow_id,
            ApprovalWorkflowVersion.university_id,
            ApprovalWorkflowVersion.publication_state,
        ).where(ApprovalWorkflowVersion.id == target.active_version_id)
    ).one_or_none()
    if row is None or row.workflow_id != target.id or row.university_id != target.university_id:
        raise ValueError("The active approval workflow version must belong to its workflow")
    if row.publication_state != "published":
        raise ValueError("The active approval workflow version must be published")


@event.listens_for(ApprovalWorkflow, "before_insert")
def _validate_active_version_on_insert(mapper, connection, target: ApprovalWorkflow) -> None:
    _validate_active_version_pointer(connection, target)


@event.listens_for(ApprovalWorkflow, "before_update")
def _validate_active_version_on_update(mapper, connection, target: ApprovalWorkflow) -> None:
    _validate_active_version_pointer(connection, target)


# These statements are intentionally not executed here. They are migration-ready
# PostgreSQL DDL for the forthcoming Alembic migration.
APPROVAL_TRIGGER_SQL: tuple[str, ...] = (
    """
    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_version()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.publication_state IS DISTINCT FROM 'draft' THEN
                RAISE EXCEPTION 'Approval workflow versions must be created as drafts'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END IF;

        IF TG_OP = 'DELETE' THEN
            IF OLD.publication_state = 'published' THEN
                RAISE EXCEPTION 'Published approval workflow versions cannot be deleted'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN OLD;
        END IF;

        IF OLD.publication_state = 'published' THEN
            RAISE EXCEPTION 'Published approval workflow versions are immutable'
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END;
    $function$;
    """,
    """
    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_step()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    DECLARE
        old_workflow_id uuid;
        old_university_id uuid;
        old_state text;
        new_workflow_id uuid;
        new_university_id uuid;
        new_state text;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            SELECT workflow_id, university_id, publication_state
              INTO old_workflow_id, old_university_id, old_state
              FROM approval_workflow_versions
             WHERE id = OLD.workflow_version_id;
            IF old_state = 'published' THEN
                RAISE EXCEPTION 'Steps belonging to published approval workflow versions cannot be deleted'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF old_workflow_id IS DISTINCT FROM OLD.workflow_id
               OR old_university_id IS DISTINCT FROM OLD.university_id THEN
                RAISE EXCEPTION 'Approval workflow step identity is inconsistent'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
            RETURN OLD;
        END IF;

        SELECT workflow_id, university_id, publication_state
          INTO new_workflow_id, new_university_id, new_state
          FROM approval_workflow_versions
         WHERE id = NEW.workflow_version_id;
        IF new_state = 'published' THEN
            RAISE EXCEPTION 'Steps belonging to published approval workflow versions are immutable'
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF new_workflow_id IS DISTINCT FROM NEW.workflow_id
           OR new_university_id IS DISTINCT FROM NEW.university_id THEN
            RAISE EXCEPTION 'Approval workflow step identity is inconsistent'
                USING ERRCODE = 'foreign_key_violation';
        END IF;

        IF TG_OP = 'UPDATE' THEN
            SELECT workflow_id, university_id, publication_state
              INTO old_workflow_id, old_university_id, old_state
              FROM approval_workflow_versions
             WHERE id = OLD.workflow_version_id;
            IF old_state = 'published' THEN
                RAISE EXCEPTION 'Steps belonging to published approval workflow versions are immutable'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF old_workflow_id IS DISTINCT FROM OLD.workflow_id
               OR old_university_id IS DISTINCT FROM OLD.university_id THEN
                RAISE EXCEPTION 'Approval workflow step identity is inconsistent'
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $function$;
    """,
    """
    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_identity()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    BEGIN
        IF OLD.workflow_type IS DISTINCT FROM NEW.workflow_type
           OR OLD.department_id IS DISTINCT FROM NEW.department_id
           OR OLD.university_id IS DISTINCT FROM NEW.university_id
           OR OLD.created_by_id IS DISTINCT FROM NEW.created_by_id THEN
            IF EXISTS (
                SELECT 1
                  FROM approval_workflow_versions
                 WHERE workflow_id = OLD.id
            ) OR EXISTS (
                SELECT 1
                  FROM approval_instances
                 WHERE workflow_id = OLD.id
            ) THEN
                RAISE EXCEPTION 'Approval workflow identity cannot change after history exists'
                    USING ERRCODE = 'restrict_violation';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $function$;
    """,
    """
    CREATE OR REPLACE FUNCTION pms_guard_approval_active_version()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    DECLARE
        selected_workflow_id uuid;
        selected_university_id uuid;
        selected_state text;
    BEGIN
        IF NEW.active_version_id IS NULL THEN
            RETURN NEW;
        END IF;

        SELECT workflow_id, university_id, publication_state
          INTO selected_workflow_id, selected_university_id, selected_state
          FROM approval_workflow_versions
         WHERE id = NEW.active_version_id;
        IF NOT FOUND
           OR selected_workflow_id IS DISTINCT FROM NEW.id
           OR selected_university_id IS DISTINCT FROM NEW.university_id THEN
            RAISE EXCEPTION 'The active approval workflow version must belong to its workflow'
                USING ERRCODE = 'foreign_key_violation';
        END IF;
        IF selected_state IS DISTINCT FROM 'published' THEN
            RAISE EXCEPTION 'The active approval workflow version must be published'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    $function$;
    """,
    """
    CREATE TRIGGER trg_approval_workflow_versions_guard
    BEFORE INSERT OR UPDATE OR DELETE ON approval_workflow_versions
    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_version();
    """,
    """
    CREATE TRIGGER trg_approval_workflow_steps_guard
    BEFORE INSERT OR UPDATE OR DELETE ON approval_workflow_steps
    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_step();
    """,
    """
    CREATE TRIGGER trg_approval_workflows_identity_guard
    BEFORE UPDATE ON approval_workflows
    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_identity();
    """,
    """
    CREATE TRIGGER trg_approval_workflows_active_version_guard
    BEFORE INSERT OR UPDATE OF active_version_id ON approval_workflows
    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_active_version();
    """,
)


APPROVAL_PUBLICATION_TRANSACTION_GUIDANCE = """
Approval publication must run in one transaction. Lock the stable workflow row
with SELECT ... FOR UPDATE, create or edit only a draft version and its steps,
publish the draft, then set active_version_id to that published version before
committing. Replacing active_version_id retires the previous selection without
editing or deleting its published version. Use a consistent workflow-row lock
order for concurrent publishers. The trigger DDL above is intended to enforce
these rules for non-ORM writers as well.
"""
