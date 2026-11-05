"""Controllers for versioned approval workflows, steps, instances, and actions."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.approvals import (
    ApprovalActionCreate,
    ApprovalActionRead,
    ApprovalInstanceCreate,
    ApprovalInstanceRead,
    ApprovalWorkflowCreate,
    ApprovalWorkflowRead,
    ApprovalWorkflowStepCreate,
    ApprovalWorkflowStepRead,
    ApprovalWorkflowStepUpdate,
    ApprovalWorkflowUpdate,
    ApprovalWorkflowVersionRead,
)
from ..services.approvals import (
    ApprovalActionService,
    ApprovalInstanceService,
    ApprovalStepService,
    ApprovalVersionService,
    ApprovalWorkflowService,
)


class ApprovalWorkflowController:
    @staticmethod
    def create_workflow(
        db: Session,
        tenant: TenantContext,
        data: ApprovalWorkflowCreate,
    ) -> ApprovalWorkflowRead:
        wf = ApprovalWorkflowService.create_workflow(db, tenant.university_id, data, tenant.user.id)
        return ApprovalWorkflowRead.model_validate(wf)

    @staticmethod
    def get_workflow(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
    ) -> ApprovalWorkflowRead:
        wf = ApprovalWorkflowService.get_workflow(db, tenant.university_id, workflow_id)
        return ApprovalWorkflowRead.model_validate(wf)

    @staticmethod
    def list_workflows(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        workflow_type: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> PaginatedResponse[ApprovalWorkflowRead]:
        items, total, total_pages = ApprovalWorkflowService.list_workflows(
            db, tenant.university_id, params, workflow_type=workflow_type, department_id=department_id
        )
        return PaginatedResponse(
            items=[ApprovalWorkflowRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_workflow(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        data: ApprovalWorkflowUpdate,
    ) -> ApprovalWorkflowRead:
        wf = ApprovalWorkflowService.update_workflow(db, tenant.university_id, workflow_id, data)
        return ApprovalWorkflowRead.model_validate(wf)

    @staticmethod
    def delete_workflow(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
    ) -> dict[str, str]:
        ApprovalWorkflowService.delete_workflow(db, tenant.university_id, workflow_id)
        return {"status": "success", "message": f"Approval workflow {workflow_id} deleted"}


class ApprovalVersionController:
    @staticmethod
    def create_version(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
    ) -> ApprovalWorkflowVersionRead:
        ver = ApprovalVersionService.create_version(db, tenant.university_id, workflow_id)
        return ApprovalWorkflowVersionRead.model_validate(ver)

    @staticmethod
    def list_versions(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
    ) -> list[ApprovalWorkflowVersionRead]:
        items = ApprovalVersionService.list_versions(db, tenant.university_id, workflow_id)
        return [ApprovalWorkflowVersionRead.model_validate(item) for item in items]

    @staticmethod
    def publish_version(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ApprovalWorkflowVersionRead:
        ver = ApprovalVersionService.publish_version(db, tenant.university_id, workflow_id, version_id)
        return ApprovalWorkflowVersionRead.model_validate(ver)

    @staticmethod
    def delete_version(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> dict[str, str]:
        ApprovalVersionService.delete_version(db, tenant.university_id, workflow_id, version_id)
        return {"status": "success", "message": f"Version {version_id} deleted"}


class ApprovalStepController:
    @staticmethod
    def add_step(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        data: ApprovalWorkflowStepCreate,
    ) -> ApprovalWorkflowStepRead:
        step = ApprovalStepService.add_step(db, tenant.university_id, workflow_id, version_id, data)
        return ApprovalWorkflowStepRead.model_validate(step)

    @staticmethod
    def get_step(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> ApprovalWorkflowStepRead:
        step = ApprovalStepService.get_step(db, tenant.university_id, workflow_id, version_id, step_id)
        return ApprovalWorkflowStepRead.model_validate(step)

    @staticmethod
    def list_steps(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> list[ApprovalWorkflowStepRead]:
        items = ApprovalStepService.list_steps(db, tenant.university_id, workflow_id, version_id)
        return [ApprovalWorkflowStepRead.model_validate(item) for item in items]

    @staticmethod
    def update_step(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
        data: ApprovalWorkflowStepUpdate,
    ) -> ApprovalWorkflowStepRead:
        step = ApprovalStepService.update_step(db, tenant.university_id, workflow_id, version_id, step_id, data)
        return ApprovalWorkflowStepRead.model_validate(step)

    @staticmethod
    def delete_step(
        db: Session,
        tenant: TenantContext,
        workflow_id: uuid.UUID,
        version_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> dict[str, str]:
        ApprovalStepService.delete_step(db, tenant.university_id, workflow_id, version_id, step_id)
        return {"status": "success", "message": f"Step {step_id} deleted"}


class ApprovalInstanceController:
    @staticmethod
    def create_instance(
        db: Session,
        tenant: TenantContext,
        data: ApprovalInstanceCreate,
    ) -> ApprovalInstanceRead:
        instance = ApprovalInstanceService.create_instance(db, tenant.university_id, data, tenant.user.id)
        return ApprovalInstanceRead.model_validate(instance)

    @staticmethod
    def get_instance(
        db: Session,
        tenant: TenantContext,
        instance_id: uuid.UUID,
    ) -> ApprovalInstanceRead:
        instance = ApprovalInstanceService.get_instance(db, tenant.university_id, instance_id)
        return ApprovalInstanceRead.model_validate(instance)

    @staticmethod
    def list_instances(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        workflow_id: Optional[uuid.UUID] = None,
        target_entity_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[ApprovalInstanceRead]:
        items, total, total_pages = ApprovalInstanceService.list_instances(
            db,
            tenant.university_id,
            params,
            workflow_id=workflow_id,
            target_entity_type=target_entity_type,
            status=status,
        )
        return PaginatedResponse(
            items=[ApprovalInstanceRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )


class ApprovalActionController:
    @staticmethod
    def record_action(
        db: Session,
        tenant: TenantContext,
        instance_id: uuid.UUID,
        data: ApprovalActionCreate,
    ) -> ApprovalActionRead:
        action = ApprovalActionService.record_action(
            db, tenant.university_id, instance_id, data, tenant.user.id
        )
        return ApprovalActionRead.model_validate(action)

    @staticmethod
    def list_actions(
        db: Session,
        tenant: TenantContext,
        instance_id: uuid.UUID,
    ) -> list[ApprovalActionRead]:
        items = ApprovalActionService.list_actions(db, tenant.university_id, instance_id)
        return [ApprovalActionRead.model_validate(item) for item in items]

