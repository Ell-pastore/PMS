"""FastAPI routes for research projects, milestones, templates, and participants."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.research_projects import (
    MilestoneTemplateController,
    ProjectMilestoneController,
    ProjectParticipantController,
    ProjectSupervisorController,
    ResearchProjectController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.research_projects import (
    MilestoneTemplateCreate,
    MilestoneTemplateRead,
    MilestoneTemplateUpdate,
    ProjectMilestoneCreate,
    ProjectMilestoneRead,
    ProjectMilestoneUpdate,
    ProjectParticipantCreate,
    ProjectParticipantEnd,
    ProjectParticipantRead,
    ProjectStatusTransition,
    ProjectSupervisorCreate,
    ProjectSupervisorEnd,
    ProjectSupervisorRead,
    ResearchProjectCreate,
    ResearchProjectRead,
    ResearchProjectUpdate,
)

projects_router = APIRouter(prefix="/research-projects", tags=["Research Projects"])
templates_router = APIRouter(prefix="/milestone-templates", tags=["Milestone Templates"])
milestones_router = APIRouter(prefix="/project-milestones", tags=["Project Milestones"])


# --- RESEARCH PROJECTS ---
@projects_router.post("", response_model=ResearchProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ResearchProjectCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.create_project(db, tenant, data)


@projects_router.get("", response_model=PaginatedResponse[ResearchProjectRead])
def list_projects(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    proposal_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.list_projects(
        db,
        tenant,
        params,
        department_id=department_id,
        proposal_id=proposal_id,
        status=status,
        search=search,
    )


@projects_router.get("/{project_id}", response_model=ResearchProjectRead)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.get_project(db, tenant, project_id)


@projects_router.patch("/{project_id}", response_model=ResearchProjectRead)
@projects_router.put("/{project_id}", response_model=ResearchProjectRead)
def update_project(
    project_id: uuid.UUID,
    data: ResearchProjectUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.update_project(db, tenant, project_id, data)


@projects_router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.delete_project(db, tenant, project_id)


@projects_router.post("/{project_id}/status", response_model=ResearchProjectRead)
def transition_project_status(
    project_id: uuid.UUID,
    data: ProjectStatusTransition,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProjectController.transition_status(db, tenant, project_id, data)


# --- PROJECT PARTICIPANTS ---
@projects_router.post("/{project_id}/participants", response_model=ProjectParticipantRead, status_code=status.HTTP_201_CREATED)
def add_participant(
    project_id: uuid.UUID,
    data: ProjectParticipantCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectParticipantController.add_participant(db, tenant, project_id, data)


@projects_router.get("/{project_id}/participants", response_model=list[ProjectParticipantRead])
def list_participants(
    project_id: uuid.UUID,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectParticipantController.list_participants(db, tenant, project_id, active_only)


@projects_router.post("/{project_id}/participants/{participant_id}/end", response_model=ProjectParticipantRead)
def end_participant(
    project_id: uuid.UUID,
    participant_id: uuid.UUID,
    data: ProjectParticipantEnd,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectParticipantController.end_participant(db, tenant, project_id, participant_id, data)


@projects_router.delete("/{project_id}/participants/{participant_id}", status_code=status.HTTP_200_OK)
def remove_participant(
    project_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectParticipantController.delete_participant(db, tenant, project_id, participant_id)


# --- PROJECT SUPERVISORS ---
@projects_router.post("/{project_id}/supervisors", response_model=ProjectSupervisorRead, status_code=status.HTTP_201_CREATED)
def assign_supervisor(
    project_id: uuid.UUID,
    data: ProjectSupervisorCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectSupervisorController.assign_supervisor(db, tenant, project_id, data)


@projects_router.get("/{project_id}/supervisors", response_model=list[ProjectSupervisorRead])
def list_supervisors(
    project_id: uuid.UUID,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectSupervisorController.list_supervisors(db, tenant, project_id, active_only)


@projects_router.post("/{project_id}/supervisors/{supervisor_id}/end", response_model=ProjectSupervisorRead)
def end_supervisor(
    project_id: uuid.UUID,
    supervisor_id: uuid.UUID,
    data: ProjectSupervisorEnd,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectSupervisorController.end_supervisor(db, tenant, project_id, supervisor_id, data)


# --- MILESTONE TEMPLATES ---
@templates_router.post("", response_model=MilestoneTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    data: MilestoneTemplateCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return MilestoneTemplateController.create_template(db, tenant, data)


@templates_router.get("", response_model=PaginatedResponse[MilestoneTemplateRead])
def list_templates(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return MilestoneTemplateController.list_templates(
        db, tenant, params, department_id=department_id, search=search, is_active=is_active
    )


@templates_router.get("/{template_id}", response_model=MilestoneTemplateRead)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return MilestoneTemplateController.get_template(db, tenant, template_id)


@templates_router.patch("/{template_id}", response_model=MilestoneTemplateRead)
@templates_router.put("/{template_id}", response_model=MilestoneTemplateRead)
def update_template(
    template_id: uuid.UUID,
    data: MilestoneTemplateUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return MilestoneTemplateController.update_template(db, tenant, template_id, data)


@templates_router.delete("/{template_id}", status_code=status.HTTP_200_OK)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return MilestoneTemplateController.delete_template(db, tenant, template_id)


# --- PROJECT MILESTONES ---
@projects_router.post("/{project_id}/milestones", response_model=ProjectMilestoneRead, status_code=status.HTTP_201_CREATED)
def create_milestone(
    project_id: uuid.UUID,
    data: ProjectMilestoneCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectMilestoneController.create_milestone(db, tenant, project_id, data)


@projects_router.get("/{project_id}/milestones", response_model=PaginatedResponse[ProjectMilestoneRead])
def list_milestones(
    project_id: uuid.UUID,
    params: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectMilestoneController.list_milestones(db, tenant, project_id, params, status=status)


@milestones_router.get("/{milestone_id}", response_model=ProjectMilestoneRead)
def get_milestone(
    milestone_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectMilestoneController.get_milestone(db, tenant, milestone_id)


@milestones_router.patch("/{milestone_id}", response_model=ProjectMilestoneRead)
@milestones_router.put("/{milestone_id}", response_model=ProjectMilestoneRead)
def update_milestone(
    milestone_id: uuid.UUID,
    data: ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectMilestoneController.update_milestone(db, tenant, milestone_id, data)


@milestones_router.delete("/{milestone_id}", status_code=status.HTTP_200_OK)
def delete_milestone(
    milestone_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectMilestoneController.delete_milestone(db, tenant, milestone_id)

