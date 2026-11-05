"""Service layer for research projects, milestones, templates, and participants."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    Department,
    MilestoneTemplate,
    ProjectMilestone,
    ProjectParticipant,
    ProjectStatusHistory,
    ProjectSupervisor,
    ResearchProject,
    ResearchProposal,
    StaffProfile,
    StudentProfile,
    UniversityMembership,
)
from ..schemas.research_projects import (
    MilestoneTemplateCreate,
    MilestoneTemplateUpdate,
    ProjectMilestoneCreate,
    ProjectMilestoneUpdate,
    ProjectParticipantCreate,
    ProjectParticipantEnd,
    ProjectStatusTransition,
    ProjectSupervisorCreate,
    ProjectSupervisorEnd,
    ResearchProjectCreate,
    ResearchProjectUpdate,
)


class ResearchProjectService:
    @staticmethod
    def create_project(
        db: Session,
        university_id: uuid.UUID,
        data: ResearchProjectCreate,
        user_id: int,
    ) -> ResearchProject:
        # Validate proposal in university
        proposal = db.scalar(
            select(ResearchProposal).where(
                ResearchProposal.id == data.proposal_id,
                ResearchProposal.university_id == university_id,
            )
        )
        if not proposal:
            raise ForeignKeyViolationError(f"Proposal {data.proposal_id} not found in this university")

        # Unique proposal_id constraint
        existing = db.scalar(select(ResearchProject).where(ResearchProject.proposal_id == data.proposal_id))
        if existing:
            raise DuplicateResourceError(f"A research project has already been created for proposal {data.proposal_id}")

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

        if data.expected_end_date and data.expected_end_date < data.start_date:
            raise InvalidInputError("Expected end date must be on or after start date")

        project = ResearchProject(
            university_id=university_id,
            proposal_id=data.proposal_id,
            department_id=data.department_id,
            title=data.title.strip(),
            abstract=data.abstract,
            start_date=data.start_date,
            expected_end_date=data.expected_end_date,
            status=data.status or "active",
            created_by_id=user_id,
        )
        db.add(project)
        db.flush()

        history = ProjectStatusHistory(
            university_id=university_id,
            project_id=project.id,
            previous_status=None,
            new_status=project.status,
            actor_id=user_id,
            reason="Project created",
        )
        db.add(history)
        db.commit()
        db.refresh(project)

        return project

    @staticmethod
    def get_project(db: Session, university_id: uuid.UUID, project_id: uuid.UUID) -> ResearchProject:
        project = db.scalar(
            select(ResearchProject).where(
                ResearchProject.id == project_id,
                ResearchProject.university_id == university_id,
            )
        )
        if not project:
            raise NotFoundError(f"Research project {project_id} not found in this university")
        return project

    @staticmethod
    def list_projects(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        proposal_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[ResearchProject], int, int]:
        query = select(ResearchProject).where(ResearchProject.university_id == university_id).order_by(ResearchProject.created_at.desc())
        if department_id:
            query = query.where(ResearchProject.department_id == department_id)
        if proposal_id:
            query = query.where(ResearchProject.proposal_id == proposal_id)
        if status:
            query = query.where(ResearchProject.status == status)
        if search:
            query = query.where(ResearchProject.title.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_project(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ResearchProjectUpdate,
    ) -> ResearchProject:
        project = ResearchProjectService.get_project(db, university_id, project_id)

        if data.department_id is not None and data.department_id != project.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            project.department_id = data.department_id

        target_start = data.start_date or project.start_date
        target_expected_end = data.expected_end_date if data.expected_end_date is not None else project.expected_end_date
        target_actual_end = data.actual_end_date if data.actual_end_date is not None else project.actual_end_date

        if target_expected_end and target_expected_end < target_start:
            raise InvalidInputError("Expected end date must be on or after start date")
        if target_actual_end and target_actual_end < target_start:
            raise InvalidInputError("Actual end date must be on or after start date")

        if data.title is not None:
            project.title = data.title.strip()
        if data.abstract is not None:
            project.abstract = data.abstract
        if data.start_date is not None:
            project.start_date = data.start_date
        if data.expected_end_date is not None:
            project.expected_end_date = data.expected_end_date
        if data.actual_end_date is not None:
            project.actual_end_date = data.actual_end_date
        if data.status is not None:
            project.status = data.status

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, university_id: uuid.UUID, project_id: uuid.UUID) -> None:
        project = ResearchProjectService.get_project(db, university_id, project_id)
        db.delete(project)
        db.commit()

    @staticmethod
    def transition_status(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectStatusTransition,
        user_id: int,
    ) -> ResearchProject:
        project = ResearchProjectService.get_project(db, university_id, project_id)
        valid_statuses = ("active", "on_hold", "completed", "cancelled", "archived")
        if data.new_status not in valid_statuses:
            raise SpecializedOperationError(f"Status '{data.new_status}' is invalid. Allowed: {valid_statuses}")

        prev_status = project.status
        project.status = data.new_status
        if data.actual_end_date is not None:
            project.actual_end_date = data.actual_end_date

        history = ProjectStatusHistory(
            university_id=university_id,
            project_id=project.id,
            previous_status=prev_status,
            new_status=data.new_status,
            actor_id=user_id,
            reason=data.reason,
        )
        db.add(history)
        db.commit()
        db.refresh(project)
        return project


class ProjectParticipantService:
    @staticmethod
    def add_participant(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectParticipantCreate,
    ) -> ProjectParticipant:
        ResearchProjectService.get_project(db, university_id, project_id)

        student = db.scalar(
            select(StudentProfile).where(
                StudentProfile.id == data.student_id,
                StudentProfile.university_id == university_id,
            )
        )
        if not student:
            raise ForeignKeyViolationError(f"Student {data.student_id} not found in this university")

        # Active participant check
        existing = db.scalar(
            select(ProjectParticipant).where(
                ProjectParticipant.project_id == project_id,
                ProjectParticipant.student_id == data.student_id,
                ProjectParticipant.ended_at.is_(None),
            )
        )
        if existing:
            raise DuplicateResourceError(f"Student {data.student_id} is already an active participant on this project")

        if data.is_lead:
            existing_lead = db.scalar(
                select(ProjectParticipant).where(
                    ProjectParticipant.project_id == project_id,
                    ProjectParticipant.is_lead.is_(True),
                    ProjectParticipant.ended_at.is_(None),
                )
            )
            if existing_lead:
                raise DuplicateResourceError("An active lead participant is already assigned to this project")

        now = datetime.now(timezone.utc)
        part = ProjectParticipant(
            university_id=university_id,
            project_id=project_id,
            student_id=data.student_id,
            participation_role=data.participation_role,
            is_lead=data.is_lead,
            started_at=data.started_at or now,
        )
        db.add(part)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def end_participant(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        participant_id: uuid.UUID,
        data: ProjectParticipantEnd,
    ) -> ProjectParticipant:
        part = db.scalar(
            select(ProjectParticipant).where(
                ProjectParticipant.id == participant_id,
                ProjectParticipant.project_id == project_id,
                ProjectParticipant.university_id == university_id,
            )
        )
        if not part:
            raise NotFoundError(f"Participant {participant_id} not found on this project")

        part.ended_at = data.ended_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def list_participants(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        active_only: bool = True,
    ) -> Sequence[ProjectParticipant]:
        ResearchProjectService.get_project(db, university_id, project_id)
        query = select(ProjectParticipant).where(
            ProjectParticipant.project_id == project_id,
            ProjectParticipant.university_id == university_id,
        )
        if active_only:
            query = query.where(ProjectParticipant.ended_at.is_(None))
        return db.scalars(query).all()

    @staticmethod
    def delete_participant(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> None:
        part = db.scalar(
            select(ProjectParticipant).where(
                ProjectParticipant.id == participant_id,
                ProjectParticipant.project_id == project_id,
                ProjectParticipant.university_id == university_id,
            )
        )
        if not part:
            raise NotFoundError(f"Participant {participant_id} not found on this project")
        db.delete(part)
        db.commit()


class ProjectSupervisorService:
    @staticmethod
    def assign_supervisor(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectSupervisorCreate,
        assigner_id: int,
    ) -> ProjectSupervisor:
        ResearchProjectService.get_project(db, university_id, project_id)

        staff = db.scalar(
            select(StaffProfile).where(
                StaffProfile.id == data.staff_id,
                StaffProfile.university_id == university_id,
            )
        )
        if not staff:
            raise ForeignKeyViolationError(f"Staff {data.staff_id} not found in this university")

        existing = db.scalar(
            select(ProjectSupervisor).where(
                ProjectSupervisor.project_id == project_id,
                ProjectSupervisor.staff_id == data.staff_id,
                ProjectSupervisor.ended_at.is_(None),
            )
        )
        if existing:
            raise DuplicateResourceError(f"Staff {data.staff_id} is already actively supervising this project")

        if data.assignment_role == "primary":
            primary = db.scalar(
                select(ProjectSupervisor).where(
                    ProjectSupervisor.project_id == project_id,
                    ProjectSupervisor.assignment_role == "primary",
                    ProjectSupervisor.ended_at.is_(None),
                )
            )
            if primary:
                raise DuplicateResourceError("Project already has an active primary supervisor")

        now = datetime.now(timezone.utc)
        sup = ProjectSupervisor(
            university_id=university_id,
            project_id=project_id,
            staff_id=data.staff_id,
            assigned_by_id=assigner_id,
            assignment_role=data.assignment_role,
            started_at=data.started_at or now,
        )
        db.add(sup)
        db.commit()
        db.refresh(sup)
        return sup

    @staticmethod
    def end_supervisor(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        data: ProjectSupervisorEnd,
    ) -> ProjectSupervisor:
        sup = db.scalar(
            select(ProjectSupervisor).where(
                ProjectSupervisor.id == supervisor_id,
                ProjectSupervisor.project_id == project_id,
                ProjectSupervisor.university_id == university_id,
            )
        )
        if not sup:
            raise NotFoundError(f"Supervisor {supervisor_id} not found on this project")

        sup.ended_at = data.ended_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(sup)
        return sup

    @staticmethod
    def list_supervisors(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        active_only: bool = True,
    ) -> Sequence[ProjectSupervisor]:
        ResearchProjectService.get_project(db, university_id, project_id)
        query = select(ProjectSupervisor).where(
            ProjectSupervisor.project_id == project_id,
            ProjectSupervisor.university_id == university_id,
        )
        if active_only:
            query = query.where(ProjectSupervisor.ended_at.is_(None))
        return db.scalars(query).all()


class MilestoneTemplateService:
    @staticmethod
    def create_template(
        db: Session,
        university_id: uuid.UUID,
        data: MilestoneTemplateCreate,
        user_id: int,
    ) -> MilestoneTemplate:
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

        tpl = MilestoneTemplate(
            university_id=university_id,
            department_id=data.department_id,
            name=data.name.strip(),
            description=data.description,
            default_duration_days=data.default_duration_days,
            is_active=data.is_active,
            created_by_id=user_id,
        )
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def get_template(db: Session, university_id: uuid.UUID, template_id: uuid.UUID) -> MilestoneTemplate:
        tpl = db.scalar(
            select(MilestoneTemplate).where(
                MilestoneTemplate.id == template_id,
                MilestoneTemplate.university_id == university_id,
            )
        )
        if not tpl:
            raise NotFoundError(f"Milestone template {template_id} not found in this university")
        return tpl

    @staticmethod
    def list_templates(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[MilestoneTemplate], int, int]:
        query = select(MilestoneTemplate).where(MilestoneTemplate.university_id == university_id).order_by(MilestoneTemplate.created_at.desc())
        if department_id:
            query = query.where(MilestoneTemplate.department_id == department_id)
        if is_active is not None:
            query = query.where(MilestoneTemplate.is_active == is_active)
        if search:
            query = query.where(MilestoneTemplate.name.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_template(
        db: Session,
        university_id: uuid.UUID,
        template_id: uuid.UUID,
        data: MilestoneTemplateUpdate,
    ) -> MilestoneTemplate:
        tpl = MilestoneTemplateService.get_template(db, university_id, template_id)
        if data.department_id is not None and data.department_id != tpl.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            tpl.department_id = data.department_id

        if data.name is not None:
            tpl.name = data.name.strip()
        if data.description is not None:
            tpl.description = data.description
        if data.default_duration_days is not None:
            tpl.default_duration_days = data.default_duration_days
        if data.is_active is not None:
            tpl.is_active = data.is_active

        db.commit()
        db.refresh(tpl)
        return tpl

    @staticmethod
    def delete_template(db: Session, university_id: uuid.UUID, template_id: uuid.UUID) -> None:
        tpl = MilestoneTemplateService.get_template(db, university_id, template_id)
        db.delete(tpl)
        db.commit()


class ProjectMilestoneService:
    @staticmethod
    def create_milestone(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectMilestoneCreate,
        user_id: int,
    ) -> ProjectMilestone:
        ResearchProjectService.get_project(db, university_id, project_id)

        if data.template_id:
            tpl = db.scalar(
                select(MilestoneTemplate).where(
                    MilestoneTemplate.id == data.template_id,
                    MilestoneTemplate.university_id == university_id,
                )
            )
            if not tpl:
                raise ForeignKeyViolationError(f"Milestone template {data.template_id} not found in this university")

        # Unique sequence number per project
        existing = db.scalar(
            select(ProjectMilestone).where(
                ProjectMilestone.project_id == project_id,
                ProjectMilestone.sequence_number == data.sequence_number,
            )
        )
        if existing:
            raise DuplicateResourceError(f"Milestone with sequence number {data.sequence_number} already exists on this project")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        milestone = ProjectMilestone(
            university_id=university_id,
            project_id=project_id,
            template_id=data.template_id,
            title=data.title.strip(),
            description=data.description,
            sequence_number=data.sequence_number,
            due_date=data.due_date,
            status=data.status or "pending",
            created_by_id=user_id,
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    @staticmethod
    def get_milestone(db: Session, university_id: uuid.UUID, milestone_id: uuid.UUID) -> ProjectMilestone:
        milestone = db.scalar(
            select(ProjectMilestone).where(
                ProjectMilestone.id == milestone_id,
                ProjectMilestone.university_id == university_id,
            )
        )
        if not milestone:
            raise NotFoundError(f"Milestone {milestone_id} not found in this university")
        return milestone

    @staticmethod
    def list_milestones(
        db: Session,
        university_id: uuid.UUID,
        project_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
    ) -> tuple[Sequence[ProjectMilestone], int, int]:
        ResearchProjectService.get_project(db, university_id, project_id)
        query = select(ProjectMilestone).where(
            ProjectMilestone.project_id == project_id,
            ProjectMilestone.university_id == university_id,
        ).order_by(ProjectMilestone.sequence_number.asc())
        if status:
            query = query.where(ProjectMilestone.status == status)
        return paginate(query, db, params)

    @staticmethod
    def update_milestone(
        db: Session,
        university_id: uuid.UUID,
        milestone_id: uuid.UUID,
        data: ProjectMilestoneUpdate,
    ) -> ProjectMilestone:
        milestone = ProjectMilestoneService.get_milestone(db, university_id, milestone_id)

        if data.sequence_number is not None and data.sequence_number != milestone.sequence_number:
            existing = db.scalar(
                select(ProjectMilestone).where(
                    ProjectMilestone.project_id == milestone.project_id,
                    ProjectMilestone.sequence_number == data.sequence_number,
                    ProjectMilestone.id != milestone.id,
                )
            )
            if existing:
                raise DuplicateResourceError(f"Milestone sequence number {data.sequence_number} already in use")
            milestone.sequence_number = data.sequence_number

        if data.title is not None:
            milestone.title = data.title.strip()
        if data.description is not None:
            milestone.description = data.description
        if data.due_date is not None:
            milestone.due_date = data.due_date
        if data.template_id is not None:
            milestone.template_id = data.template_id

        target_status = data.status or milestone.status
        milestone.status = target_status
        if target_status == "completed":
            milestone.completed_at = data.completed_at or datetime.now(timezone.utc)
        elif data.status is not None:
            milestone.completed_at = None

        db.commit()
        db.refresh(milestone)
        return milestone

    @staticmethod
    def delete_milestone(db: Session, university_id: uuid.UUID, milestone_id: uuid.UUID) -> None:
        milestone = ProjectMilestoneService.get_milestone(db, university_id, milestone_id)
        db.delete(milestone)
        db.commit()

