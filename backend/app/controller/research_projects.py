"""Controllers for research projects, milestones, templates, and participants."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
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
from ..services.research_projects import (
    MilestoneTemplateService,
    ProjectMilestoneService,
    ProjectParticipantService,
    ProjectSupervisorService,
    ResearchProjectService,
)


class ResearchProjectController:
    @staticmethod
    def create_project(db: Session, tenant: TenantContext, data: ResearchProjectCreate) -> ResearchProjectRead:
        project = ResearchProjectService.create_project(db, tenant.university_id, data, tenant.user.id)
        return ResearchProjectRead.model_validate(project)

    @staticmethod
    def get_project(db: Session, tenant: TenantContext, project_id: uuid.UUID) -> ResearchProjectRead:
        project = ResearchProjectService.get_project(db, tenant.university_id, project_id)
        return ResearchProjectRead.model_validate(project)

    @staticmethod
    def list_projects(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        proposal_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ResearchProjectRead]:
        items, total, total_pages = ResearchProjectService.list_projects(
            db,
            tenant.university_id,
            params,
            department_id=department_id,
            proposal_id=proposal_id,
            status=status,
            search=search,
        )
        return PaginatedResponse(
            items=[ResearchProjectRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_project(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        data: ResearchProjectUpdate,
    ) -> ResearchProjectRead:
        project = ResearchProjectService.update_project(db, tenant.university_id, project_id, data)
        return ResearchProjectRead.model_validate(project)

    @staticmethod
    def delete_project(db: Session, tenant: TenantContext, project_id: uuid.UUID) -> dict[str, str]:
        ResearchProjectService.delete_project(db, tenant.university_id, project_id)
        return {"status": "success", "message": f"Project {project_id} deleted"}

    @staticmethod
    def transition_status(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        data: ProjectStatusTransition,
    ) -> ResearchProjectRead:
        project = ResearchProjectService.transition_status(db, tenant.university_id, project_id, data, tenant.user.id)
        return ResearchProjectRead.model_validate(project)


class ProjectParticipantController:
    @staticmethod
    def add_participant(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        data: ProjectParticipantCreate,
    ) -> ProjectParticipantRead:
        part = ProjectParticipantService.add_participant(db, tenant.university_id, project_id, data)
        return ProjectParticipantRead.model_validate(part)

    @staticmethod
    def end_participant(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        participant_id: uuid.UUID,
        data: ProjectParticipantEnd,
    ) -> ProjectParticipantRead:
        part = ProjectParticipantService.end_participant(
            db, tenant.university_id, project_id, participant_id, data
        )
        return ProjectParticipantRead.model_validate(part)

    @staticmethod
    def list_participants(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[ProjectParticipantRead]:
        items = ProjectParticipantService.list_participants(db, tenant.university_id, project_id, active_only)
        return [ProjectParticipantRead.model_validate(item) for item in items]

    @staticmethod
    def delete_participant(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> dict[str, str]:
        ProjectParticipantService.delete_participant(db, tenant.university_id, project_id, participant_id)
        return {"status": "success", "message": f"Participant {participant_id} removed"}


class ProjectSupervisorController:
    @staticmethod
    def assign_supervisor(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        data: ProjectSupervisorCreate,
    ) -> ProjectSupervisorRead:
        sup = ProjectSupervisorService.assign_supervisor(
            db, tenant.university_id, project_id, data, tenant.user.id
        )
        return ProjectSupervisorRead.model_validate(sup)

    @staticmethod
    def end_supervisor(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        data: ProjectSupervisorEnd,
    ) -> ProjectSupervisorRead:
        sup = ProjectSupervisorService.end_supervisor(
            db, tenant.university_id, project_id, supervisor_id, data
        )
        return ProjectSupervisorRead.model_validate(sup)

    @staticmethod
    def list_supervisors(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[ProjectSupervisorRead]:
        items = ProjectSupervisorService.list_supervisors(db, tenant.university_id, project_id, active_only)
        return [ProjectSupervisorRead.model_validate(item) for item in items]


class MilestoneTemplateController:
    @staticmethod
    def create_template(
        db: Session,
        tenant: TenantContext,
        data: MilestoneTemplateCreate,
    ) -> MilestoneTemplateRead:
        tpl = MilestoneTemplateService.create_template(db, tenant.university_id, data, tenant.user.id)
        return MilestoneTemplateRead.model_validate(tpl)

    @staticmethod
    def get_template(
        db: Session,
        tenant: TenantContext,
        template_id: uuid.UUID,
    ) -> MilestoneTemplateRead:
        tpl = MilestoneTemplateService.get_template(db, tenant.university_id, template_id)
        return MilestoneTemplateRead.model_validate(tpl)

    @staticmethod
    def list_templates(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[MilestoneTemplateRead]:
        items, total, total_pages = MilestoneTemplateService.list_templates(
            db, tenant.university_id, params, department_id=department_id, search=search, is_active=is_active
        )
        return PaginatedResponse(
            items=[MilestoneTemplateRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_template(
        db: Session,
        tenant: TenantContext,
        template_id: uuid.UUID,
        data: MilestoneTemplateUpdate,
    ) -> MilestoneTemplateRead:
        tpl = MilestoneTemplateService.update_template(db, tenant.university_id, template_id, data)
        return MilestoneTemplateRead.model_validate(tpl)

    @staticmethod
    def delete_template(
        db: Session,
        tenant: TenantContext,
        template_id: uuid.UUID,
    ) -> dict[str, str]:
        MilestoneTemplateService.delete_template(db, tenant.university_id, template_id)
        return {"status": "success", "message": f"Template {template_id} deleted"}


class ProjectMilestoneController:
    @staticmethod
    def create_milestone(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        data: ProjectMilestoneCreate,
    ) -> ProjectMilestoneRead:
        milestone = ProjectMilestoneService.create_milestone(
            db, tenant.university_id, project_id, data, tenant.user.id
        )
        return ProjectMilestoneRead.model_validate(milestone)

    @staticmethod
    def get_milestone(
        db: Session,
        tenant: TenantContext,
        milestone_id: uuid.UUID,
    ) -> ProjectMilestoneRead:
        milestone = ProjectMilestoneService.get_milestone(db, tenant.university_id, milestone_id)
        return ProjectMilestoneRead.model_validate(milestone)

    @staticmethod
    def list_milestones(
        db: Session,
        tenant: TenantContext,
        project_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
    ) -> PaginatedResponse[ProjectMilestoneRead]:
        items, total, total_pages = ProjectMilestoneService.list_milestones(
            db, tenant.university_id, project_id, params, status=status
        )
        return PaginatedResponse(
            items=[ProjectMilestoneRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_milestone(
        db: Session,
        tenant: TenantContext,
        milestone_id: uuid.UUID,
        data: ProjectMilestoneUpdate,
    ) -> ProjectMilestoneRead:
        milestone = ProjectMilestoneService.update_milestone(db, tenant.university_id, milestone_id, data)
        return ProjectMilestoneRead.model_validate(milestone)

    @staticmethod
    def delete_milestone(
        db: Session,
        tenant: TenantContext,
        milestone_id: uuid.UUID,
    ) -> dict[str, str]:
        ProjectMilestoneService.delete_milestone(db, tenant.university_id, milestone_id)
        return {"status": "success", "message": f"Milestone {milestone_id} deleted"}

