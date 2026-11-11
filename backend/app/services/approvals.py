"""Service layer for versioned approval workflows, steps, instances, and actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForbiddenError,
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    ApprovalAction,
    ApprovalInstance,
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    ApprovalWorkflowVersion,
    Department,
    Role,
    UniversityMembership,
    User,
    UserRole,
)
from ..schemas.approvals import (
    ApprovalActionCreate,
    ApprovalInstanceCreate,
    ApprovalWorkflowCreate,
    ApprovalWorkflowStepCreate,
    ApprovalWorkflowStepUpdate,
    ApprovalWorkflowUpdate,
)


class ApprovalWorkflowService:
    @staticmethod
    def create_workflow(
        db: Session,
        university_id: uuid.UUID,
        data: ApprovalWorkflowCreate,
        user_id: int,
    ) -> ApprovalWorkflow:
        if data.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        # Unique scope check
        if data.department_id is not None:
            existing = db.scalar(
                select(ApprovalWorkflow).where(
                    ApprovalWorkflow.workflow_type == data.workflow_type.strip(),
                    ApprovalWorkflow.university_id == university_id,
                    ApprovalWorkflow.department_id == data.department_id,
                )
            )
        else:
            existing = db.scalar(
                select(ApprovalWorkflow).where(
                    ApprovalWorkflow.workflow_type == data.workflow_type.strip(),
                    ApprovalWorkflow.university_id == university_id,
                    ApprovalWorkflow.department_id.is_(None),
                )
            )
        if existing:
            raise DuplicateResourceError(f"Approval workflow for type '{data.workflow_type}' already exists in this scope")

        workflow = ApprovalWorkflow(
            university_id=university_id,
            workflow_type=data.workflow_type.strip(),
            department_id=data.department_id,
            created_by_id=user_id,
        )
        db.add(workflow)
        db.flush()

        # Create initial draft version (single transaction with workflow creation)
        version = ApprovalWorkflowVersion(
            workflow_id=workflow.id,
            university_id=university_id,
            version_number=1,
            publication_state="draft",
        )
        db.add(version)
        db.commit()
        db.refresh(workflow)
        return workflow

    @staticmethod
    def get_workflow(db: Session, university_id: uuid.UUID, workflow_id: uuid.UUID) -> ApprovalWorkflow:
        wf = db.scalar(
            select(ApprovalWorkflow).where(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.university_id == university_id,
            )
        )
        if not wf:
            raise NotFoundError(f"Approval workflow {workflow_id} not found in this university")
        return wf

    @staticmethod
    def list_workflows(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        workflow_type: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> tuple[Sequence[ApprovalWorkflow], int, int]:
        query = select(ApprovalWorkflow).where(ApprovalWorkflow.university_id == university_id).order_by(ApprovalWorkflow.created_at.desc())
        if workflow_type:
            query = query.where(ApprovalWorkflow.workflow_type.ilike(f"%{workflow_type.strip()}%"))
        if department_id:
            query = query.where(ApprovalWorkflow.department_id == department_id)
        return paginate(query, db, params)

    @staticmethod
    def update_workflow(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        data: ApprovalWorkflowUpdate,
    ) -> ApprovalWorkflow:
        wf = ApprovalWorkflowService.get_workflow(db, university_id, workflow_id)
        if data.department_id is not None and data.department_id != wf.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            wf.department_id = data.department_id

        if data.workflow_type is not None:
            wf.workflow_type = data.workflow_type.strip()

        db.commit()
        db.refresh(wf)
        return wf

    @staticmethod
    def delete_workflow(db: Session, university_id: uuid.UUID, workflow_id: uuid.UUID) -> None:
        wf = ApprovalWorkflowService.get_workflow(db, university_id, workflow_id)

        # Guard against deleting a workflow that has run (or could run) against
        # real entities, or whose published versions are immutable by design.
        if db.scalar(
            select(func.count()).select_from(ApprovalInstance).where(ApprovalInstance.workflow_id == wf.id)
        ):
            raise SpecializedOperationError(
                "Cannot delete approval workflow with existing instances. Instances are part of the audit trail."
            )
        if db.scalar(
            select(func.count())
            .select_from(ApprovalWorkflowVersion)
            .where(
                ApprovalWorkflowVersion.workflow_id == wf.id,
                ApprovalWorkflowVersion.publication_state == "published",
            )
        ):
            raise SpecializedOperationError(
                "Cannot delete approval workflow with published versions. Published versions are immutable."
            )

        # Cascade the workflow's draft versions and their steps (the workflow
        # definition is one unit), then delete the workflow in one transaction.
        draft_version_ids = db.scalars(
            select(ApprovalWorkflowVersion.id).where(
                ApprovalWorkflowVersion.workflow_id == wf.id,
                ApprovalWorkflowVersion.university_id == university_id,
            )
        ).all()
        if draft_version_ids:
            db.execute(
                delete(ApprovalWorkflowStep).where(ApprovalWorkflowStep.workflow_version_id.in_(draft_version_ids))
            )
            db.execute(delete(ApprovalWorkflowVersion).where(ApprovalWorkflowVersion.id.in_(draft_version_ids)))

        # Clear active_version_id first to break cyclic foreign key constraint
        wf.active_version_id = None
        db.flush()
        db.delete(wf)
        db.commit()


class ApprovalVersionService:
    @staticmethod
    def create_version(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> ApprovalWorkflowVersion:
        ApprovalWorkflowService.get_workflow(db, university_id, workflow_id)

        max_num = db.scalar(
            select(func.coalesce(func.max(ApprovalWorkflowVersion.version_number), 0)).where(
                ApprovalWorkflowVersion.workflow_id == workflow_id
            )
        )
        next_num = (max_num or 0) + 1

        version = ApprovalWorkflowVersion(
            workflow_id=workflow_id,
            university_id=university_id,
            version_number=next_num,
            publication_state="draft",
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def get_version(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ApprovalWorkflowVersion:
        version = db.scalar(
            select(ApprovalWorkflowVersion).where(
                ApprovalWorkflowVersion.id == version_id,
                ApprovalWorkflowVersion.workflow_id == workflow_id,
                ApprovalWorkflowVersion.university_id == university_id,
            )
        )
        if not version:
            raise NotFoundError(f"Approval workflow version {version_id} not found")
        return version

    @staticmethod
    def list_versions(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> Sequence[ApprovalWorkflowVersion]:
        ApprovalWorkflowService.get_workflow(db, university_id, workflow_id)
        return db.scalars(
            select(ApprovalWorkflowVersion)
            .where(
                ApprovalWorkflowVersion.workflow_id == workflow_id,
                ApprovalWorkflowVersion.university_id == university_id,
            )
            .order_by(ApprovalWorkflowVersion.version_number.desc())
        ).all()

    @staticmethod
    def publish_version(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ApprovalWorkflowVersion:
        workflow = ApprovalWorkflowService.get_workflow(db, university_id, workflow_id)
        version = ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)

        if version.publication_state == "published":
            return version

        version.publication_state = "published"
        workflow.active_version_id = version.id

        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def delete_version(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> None:
        version = ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)
        if version.publication_state == "published":
            raise SpecializedOperationError("Cannot delete a published workflow version. Published versions are immutable.")
        if db.scalar(
            select(func.count()).select_from(ApprovalInstance).where(ApprovalInstance.workflow_version_id == version.id)
        ):
            raise SpecializedOperationError(
                "Cannot delete workflow version with existing instances. Instances are part of the audit trail."
            )

        # Cascade the version's steps (the version definition is one unit),
        # then delete the version in a single transaction.
        db.execute(delete(ApprovalWorkflowStep).where(ApprovalWorkflowStep.workflow_version_id == version.id))
        db.delete(version)
        db.commit()


class ApprovalStepService:
    @staticmethod
    def add_step(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        data: ApprovalWorkflowStepCreate,
    ) -> ApprovalWorkflowStep:
        version = ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)
        if version.publication_state == "published":
            raise SpecializedOperationError("Cannot add steps to a published workflow version. Published versions are immutable.")

        if data.required_role_id:
            role = db.scalar(select(Role).where(Role.id == data.required_role_id))
            if not role:
                raise ForeignKeyViolationError(f"Role {data.required_role_id} not found")

        existing = db.scalar(
            select(ApprovalWorkflowStep).where(
                ApprovalWorkflowStep.workflow_version_id == version_id,
                ApprovalWorkflowStep.step_number == data.step_number,
            )
        )
        if existing:
            raise DuplicateResourceError(f"Step {data.step_number} already exists on this workflow version")

        step = ApprovalWorkflowStep(
            workflow_version_id=version_id,
            workflow_id=workflow_id,
            university_id=university_id,
            step_number=data.step_number,
            name=data.name.strip(),
            required_role_id=data.required_role_id,
            required_approvals=data.required_approvals,
            is_mandatory=data.is_mandatory,
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        return step

    @staticmethod
    def get_step(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> ApprovalWorkflowStep:
        step = db.scalar(
            select(ApprovalWorkflowStep).where(
                ApprovalWorkflowStep.id == step_id,
                ApprovalWorkflowStep.workflow_version_id == version_id,
                ApprovalWorkflowStep.workflow_id == workflow_id,
                ApprovalWorkflowStep.university_id == university_id,
            )
        )
        if not step:
            raise NotFoundError(f"Approval step {step_id} not found on this version")
        return step

    @staticmethod
    def list_steps(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Sequence[ApprovalWorkflowStep]:
        ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)
        return db.scalars(
            select(ApprovalWorkflowStep)
            .where(
                ApprovalWorkflowStep.workflow_version_id == version_id,
                ApprovalWorkflowStep.workflow_id == workflow_id,
                ApprovalWorkflowStep.university_id == university_id,
            )
            .order_by(ApprovalWorkflowStep.step_number.asc())
        ).all()

    @staticmethod
    def update_step(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
        data: ApprovalWorkflowStepUpdate,
    ) -> ApprovalWorkflowStep:
        version = ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)
        if version.publication_state == "published":
            raise SpecializedOperationError("Cannot modify steps on a published workflow version. Published versions are immutable.")

        step = ApprovalStepService.get_step(db, university_id, workflow_id, version_id, step_id)

        if data.step_number is not None and data.step_number != step.step_number:
            existing = db.scalar(
                select(ApprovalWorkflowStep).where(
                    ApprovalWorkflowStep.workflow_version_id == version_id,
                    ApprovalWorkflowStep.step_number == data.step_number,
                    ApprovalWorkflowStep.id != step.id,
                )
            )
            if existing:
                raise DuplicateResourceError(f"Step number {data.step_number} already in use on this version")
            step.step_number = data.step_number

        if data.name is not None:
            step.name = data.name.strip()
        if data.required_role_id is not None:
            role = db.scalar(select(Role).where(Role.id == data.required_role_id))
            if not role:
                raise ForeignKeyViolationError(f"Role {data.required_role_id} not found")
            step.required_role_id = data.required_role_id
        if data.required_approvals is not None:
            step.required_approvals = data.required_approvals
        if data.is_mandatory is not None:
            step.is_mandatory = data.is_mandatory

        db.commit()
        db.refresh(step)
        return step

    @staticmethod
    def delete_step(
        db: Session,
        university_id: uuid.UUID,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> None:
        version = ApprovalVersionService.get_version(db, university_id, workflow_id, version_id)
        if version.publication_state == "published":
            raise SpecializedOperationError("Cannot delete steps from a published workflow version. Published versions are immutable.")

        step = ApprovalStepService.get_step(db, university_id, workflow_id, version_id, step_id)
        if db.scalar(select(func.count()).select_from(ApprovalAction).where(ApprovalAction.step_id == step.id)):
            raise SpecializedOperationError(
                "Cannot delete workflow step with existing approval actions. Actions are part of the audit trail."
            )
        db.delete(step)
        db.commit()


class ApprovalInstanceService:
    @staticmethod
    def create_instance(
        db: Session,
        university_id: uuid.UUID,
        data: ApprovalInstanceCreate,
        user_id: int,
    ) -> ApprovalInstance:
        workflow = ApprovalWorkflowService.get_workflow(db, university_id, data.workflow_id)

        target_version_id = data.workflow_version_id or workflow.active_version_id
        if not target_version_id:
            raise SpecializedOperationError("Cannot initiate approval: workflow has no active published version")

        version = db.scalar(
            select(ApprovalWorkflowVersion).where(
                ApprovalWorkflowVersion.id == target_version_id,
                ApprovalWorkflowVersion.workflow_id == data.workflow_id,
                ApprovalWorkflowVersion.university_id == university_id,
            )
        )
        if not version:
            raise NotFoundError(f"Workflow version {target_version_id} not found")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        instance = ApprovalInstance(
            workflow_version_id=target_version_id,
            workflow_id=data.workflow_id,
            university_id=university_id,
            target_entity_type=data.target_entity_type,
            target_entity_id=data.target_entity_id,
            status="pending",
            initiated_by_id=user_id,
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance

    @staticmethod
    def get_instance(
        db: Session,
        university_id: uuid.UUID,
        instance_id: uuid.UUID,
    ) -> ApprovalInstance:
        instance = db.scalar(
            select(ApprovalInstance).where(
                ApprovalInstance.id == instance_id,
                ApprovalInstance.university_id == university_id,
            )
        )
        if not instance:
            raise NotFoundError(f"Approval instance {instance_id} not found in this university")
        return instance

    @staticmethod
    def list_instances(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        workflow_id: Optional[uuid.UUID] = None,
        target_entity_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[Sequence[ApprovalInstance], int, int]:
        query = select(ApprovalInstance).where(ApprovalInstance.university_id == university_id).order_by(ApprovalInstance.started_at.desc())
        if workflow_id:
            query = query.where(ApprovalInstance.workflow_id == workflow_id)
        if target_entity_type:
            query = query.where(ApprovalInstance.target_entity_type == target_entity_type)
        if status:
            query = query.where(ApprovalInstance.status == status)
        return paginate(query, db, params)


class ApprovalActionService:
    @staticmethod
    def record_action(
        db: Session,
        university_id: uuid.UUID,
        instance_id: uuid.UUID,
        data: ApprovalActionCreate,
        actor_id: int,
    ) -> ApprovalAction:
        instance = ApprovalInstanceService.get_instance(db, university_id, instance_id)
        if instance.status in ("approved", "rejected", "cancelled"):
            raise SpecializedOperationError(f"Cannot record action: instance is already '{instance.status}'")

        # Step must belong to instance's workflow version
        step = db.scalar(
            select(ApprovalWorkflowStep).where(
                ApprovalWorkflowStep.id == data.step_id,
                ApprovalWorkflowStep.workflow_version_id == instance.workflow_version_id,
                ApprovalWorkflowStep.workflow_id == instance.workflow_id,
                ApprovalWorkflowStep.university_id == university_id,
            )
        )
        if not step:
            raise ForeignKeyViolationError("Step does not belong to the instance's workflow version")

        # Verify actor membership
        actor_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == actor_id,
            )
        )
        if not actor_membership:
            raise ForeignKeyViolationError(f"Actor {actor_id} has no membership in this university")

        # If step requires specific role, verify actor holds it actively
        if step.required_role_id:
            has_role = db.scalar(
                select(UserRole.id).where(
                    UserRole.university_id == university_id,
                    UserRole.user_id == actor_id,
                    UserRole.role_id == step.required_role_id,
                    UserRole.revoked_at.is_(None),
                )
            )
            if not has_role:
                raise ForbiddenError(f"Action requires role {step.required_role_id} which the actor does not hold")

        action = ApprovalAction(
            instance_id=instance_id,
            step_id=data.step_id,
            workflow_version_id=instance.workflow_version_id,
            workflow_id=instance.workflow_id,
            university_id=university_id,
            acting_user_id=actor_id,
            decision=data.decision,
            comments=data.comments,
        )
        db.add(action)
        db.flush()

        now = datetime.now(timezone.utc)
        if data.decision == "rejected" and step.is_mandatory:
            instance.status = "rejected"
            instance.completed_at = now
        else:
            instance.status = "in_progress"
            # Check if all mandatory steps are fulfilled
            steps = db.scalars(
                select(ApprovalWorkflowStep).where(
                    ApprovalWorkflowStep.workflow_version_id == instance.workflow_version_id
                )
            ).all()

            all_satisfied = True
            for s in steps:
                if not s.is_mandatory:
                    continue
                approved_count = db.scalar(
                    select(func.count(ApprovalAction.id)).where(
                        ApprovalAction.instance_id == instance.id,
                        ApprovalAction.step_id == s.id,
                        ApprovalAction.decision == "approved",
                    )
                )
                if (approved_count or 0) < s.required_approvals:
                    all_satisfied = False
                    break

            if all_satisfied and steps:
                instance.status = "approved"
                instance.completed_at = now

        db.commit()
        db.refresh(action)
        return action

    @staticmethod
    def list_actions(
        db: Session,
        university_id: uuid.UUID,
        instance_id: uuid.UUID,
    ) -> Sequence[ApprovalAction]:
        ApprovalInstanceService.get_instance(db, university_id, instance_id)
        return db.scalars(
            select(ApprovalAction)
            .where(
                ApprovalAction.instance_id == instance_id,
                ApprovalAction.university_id == university_id,
            )
            .order_by(ApprovalAction.created_at.asc())
        ).all()

