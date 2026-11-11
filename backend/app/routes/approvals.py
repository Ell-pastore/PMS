"""FastAPI routes for versioned approval workflows, steps, instances, and actions."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.approvals import (
    ApprovalActionController,
    ApprovalInstanceController,
    ApprovalStepController,
    ApprovalVersionController,
    ApprovalWorkflowController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
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

workflows_router = APIRouter(prefix="/approval-workflows", tags=["Approval Workflows"])
instances_router = APIRouter(prefix="/approval-instances", tags=["Approval Instances"])


# --- WORKFLOWS ---
@workflows_router.post("", response_model=ApprovalWorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    data: ApprovalWorkflowCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalWorkflowController.create_workflow(db, tenant, data)


@workflows_router.get("", response_model=PaginatedResponse[ApprovalWorkflowRead])
def list_workflows(
    params: PaginationParams = Depends(),
    workflow_type: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalWorkflowController.list_workflows(
        db, tenant, params, workflow_type=workflow_type, department_id=department_id
    )


@workflows_router.get("/{workflow_id}", response_model=ApprovalWorkflowRead)
def get_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalWorkflowController.get_workflow(db, tenant, workflow_id)


@workflows_router.patch("/{workflow_id}", response_model=ApprovalWorkflowRead)
@workflows_router.put("/{workflow_id}", response_model=ApprovalWorkflowRead)
def update_workflow(
    workflow_id: uuid.UUID,
    data: ApprovalWorkflowUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalWorkflowController.update_workflow(db, tenant, workflow_id, data)


@workflows_router.delete("/{workflow_id}", status_code=status.HTTP_200_OK)
def delete_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalWorkflowController.delete_workflow(db, tenant, workflow_id)


# --- VERSIONS ---
@workflows_router.post("/{workflow_id}/versions", response_model=ApprovalWorkflowVersionRead, status_code=status.HTTP_201_CREATED)
def create_version(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalVersionController.create_version(db, tenant, workflow_id)


@workflows_router.get("/{workflow_id}/versions", response_model=list[ApprovalWorkflowVersionRead])
def list_versions(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalVersionController.list_versions(db, tenant, workflow_id)


@workflows_router.post("/{workflow_id}/versions/{version_id}/publish", response_model=ApprovalWorkflowVersionRead)
def publish_version(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalVersionController.publish_version(db, tenant, workflow_id, version_id)


@workflows_router.delete("/{workflow_id}/versions/{version_id}", status_code=status.HTTP_200_OK)
def delete_version(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalVersionController.delete_version(db, tenant, workflow_id, version_id)


# --- STEPS ---
@workflows_router.post("/{workflow_id}/versions/{version_id}/steps", response_model=ApprovalWorkflowStepRead, status_code=status.HTTP_201_CREATED)
def add_step(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    data: ApprovalWorkflowStepCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalStepController.add_step(db, tenant, workflow_id, version_id, data)


@workflows_router.get("/{workflow_id}/versions/{version_id}/steps", response_model=list[ApprovalWorkflowStepRead])
def list_steps(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalStepController.list_steps(db, tenant, workflow_id, version_id)


@workflows_router.get("/{workflow_id}/versions/{version_id}/steps/{step_id}", response_model=ApprovalWorkflowStepRead)
def get_step(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalStepController.get_step(db, tenant, workflow_id, version_id, step_id)


@workflows_router.patch("/{workflow_id}/versions/{version_id}/steps/{step_id}", response_model=ApprovalWorkflowStepRead)
@workflows_router.put("/{workflow_id}/versions/{version_id}/steps/{step_id}", response_model=ApprovalWorkflowStepRead)
def update_step(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    step_id: uuid.UUID,
    data: ApprovalWorkflowStepUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalStepController.update_step(db, tenant, workflow_id, version_id, step_id, data)


@workflows_router.delete("/{workflow_id}/versions/{version_id}/steps/{step_id}", status_code=status.HTTP_200_OK)
def delete_step(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ApprovalStepController.delete_step(db, tenant, workflow_id, version_id, step_id)


# --- INSTANCES ---
@instances_router.post("", response_model=ApprovalInstanceRead, status_code=status.HTTP_201_CREATED)
def create_instance(
    data: ApprovalInstanceCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalInstanceController.create_instance(db, tenant, data)


@instances_router.get("", response_model=PaginatedResponse[ApprovalInstanceRead])
def list_instances(
    params: PaginationParams = Depends(),
    workflow_id: Optional[uuid.UUID] = Query(None),
    target_entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalInstanceController.list_instances(
        db,
        tenant,
        params,
        workflow_id=workflow_id,
        target_entity_type=target_entity_type,
        status=status,
    )


@instances_router.get("/{instance_id}", response_model=ApprovalInstanceRead)
def get_instance(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalInstanceController.get_instance(db, tenant, instance_id)


# Actions
@instances_router.post("/{instance_id}/actions", response_model=ApprovalActionRead, status_code=status.HTTP_201_CREATED)
def record_action(
    instance_id: uuid.UUID,
    data: ApprovalActionCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalActionController.record_action(db, tenant, instance_id, data)


@instances_router.get("/{instance_id}/actions", response_model=list[ApprovalActionRead])
def list_actions(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ApprovalActionController.list_actions(db, tenant, instance_id)

