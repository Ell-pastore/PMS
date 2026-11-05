"""Controllers for research proposals, revisions, participants, supervisors, and reviews."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.research_proposals import (
    ProposalParticipantCreate,
    ProposalParticipantRead,
    ProposalReviewCreate,
    ProposalReviewRead,
    ProposalRevisionCreate,
    ProposalRevisionRead,
    ProposalStatusTransition,
    ProposalSupervisorCreate,
    ProposalSupervisorEnd,
    ProposalSupervisorRead,
    ResearchProposalCreate,
    ResearchProposalRead,
    ResearchProposalUpdate,
)
from ..services.research_proposals import (
    ProposalParticipantService,
    ProposalReviewService,
    ProposalRevisionService,
    ProposalSupervisorService,
    ResearchProposalService,
)


class ResearchProposalController:
    @staticmethod
    def create_proposal(
        db: Session,
        tenant: TenantContext,
        data: ResearchProposalCreate,
    ) -> ResearchProposalRead:
        proposal = ResearchProposalService.create_proposal(db, tenant.university_id, data, tenant.user.id)
        return ResearchProposalRead.model_validate(proposal)

    @staticmethod
    def get_proposal(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> ResearchProposalRead:
        proposal = ResearchProposalService.get_proposal(db, tenant.university_id, proposal_id)
        return ResearchProposalRead.model_validate(proposal)

    @staticmethod
    def list_proposals(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        topic_id: Optional[uuid.UUID] = None,
        submitting_user_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ResearchProposalRead]:
        items, total, total_pages = ResearchProposalService.list_proposals(
            db,
            tenant.university_id,
            params,
            department_id=department_id,
            topic_id=topic_id,
            submitting_user_id=submitting_user_id,
            status=status,
            search=search,
        )
        return PaginatedResponse(
            items=[ResearchProposalRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_proposal(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ResearchProposalUpdate,
    ) -> ResearchProposalRead:
        proposal = ResearchProposalService.update_proposal(db, tenant.university_id, proposal_id, data)
        return ResearchProposalRead.model_validate(proposal)

    @staticmethod
    def delete_proposal(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> dict[str, str]:
        ResearchProposalService.delete_proposal(db, tenant.university_id, proposal_id)
        return {"status": "success", "message": f"Proposal {proposal_id} deleted"}

    @staticmethod
    def submit_proposal(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> ResearchProposalRead:
        proposal = ResearchProposalService.submit_proposal(db, tenant.university_id, proposal_id, tenant.user.id)
        return ResearchProposalRead.model_validate(proposal)

    @staticmethod
    def transition_status(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ProposalStatusTransition,
    ) -> ResearchProposalRead:
        proposal = ResearchProposalService.transition_status(
            db, tenant.university_id, proposal_id, data.new_status, tenant.user.id, data.reason
        )
        return ResearchProposalRead.model_validate(proposal)


class ProposalParticipantController:
    @staticmethod
    def add_participant(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ProposalParticipantCreate,
    ) -> ProposalParticipantRead:
        part = ProposalParticipantService.add_participant(db, tenant.university_id, proposal_id, data)
        return ProposalParticipantRead.model_validate(part)

    @staticmethod
    def list_participants(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> list[ProposalParticipantRead]:
        items = ProposalParticipantService.list_participants(db, tenant.university_id, proposal_id)
        return [ProposalParticipantRead.model_validate(item) for item in items]

    @staticmethod
    def remove_participant(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> dict[str, str]:
        ProposalParticipantService.remove_participant(db, tenant.university_id, proposal_id, participant_id)
        return {"status": "success", "message": f"Participant {participant_id} removed"}


class ProposalSupervisorController:
    @staticmethod
    def assign_supervisor(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ProposalSupervisorCreate,
    ) -> ProposalSupervisorRead:
        sup = ProposalSupervisorService.assign_supervisor(
            db, tenant.university_id, proposal_id, data, tenant.user.id
        )
        return ProposalSupervisorRead.model_validate(sup)

    @staticmethod
    def end_supervisor(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        data: ProposalSupervisorEnd,
    ) -> ProposalSupervisorRead:
        sup = ProposalSupervisorService.end_supervisor(
            db, tenant.university_id, proposal_id, supervisor_id, data
        )
        return ProposalSupervisorRead.model_validate(sup)

    @staticmethod
    def list_supervisors(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[ProposalSupervisorRead]:
        items = ProposalSupervisorService.list_supervisors(
            db, tenant.university_id, proposal_id, active_only=active_only
        )
        return [ProposalSupervisorRead.model_validate(item) for item in items]


class ProposalRevisionController:
    @staticmethod
    def create_revision(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ProposalRevisionCreate,
    ) -> ProposalRevisionRead:
        rev = ProposalRevisionService.create_revision(
            db, tenant.university_id, proposal_id, data, tenant.user.id
        )
        return ProposalRevisionRead.model_validate(rev)

    @staticmethod
    def list_revisions(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> list[ProposalRevisionRead]:
        items = ProposalRevisionService.list_revisions(db, tenant.university_id, proposal_id)
        return [ProposalRevisionRead.model_validate(item) for item in items]


class ProposalReviewController:
    @staticmethod
    def create_review(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
        data: ProposalReviewCreate,
    ) -> ProposalReviewRead:
        review = ProposalReviewService.create_review(
            db, tenant.university_id, proposal_id, data, tenant.user.id
        )
        return ProposalReviewRead.model_validate(review)

    @staticmethod
    def list_reviews(
        db: Session,
        tenant: TenantContext,
        proposal_id: uuid.UUID,
    ) -> list[ProposalReviewRead]:
        items = ProposalReviewService.list_reviews(db, tenant.university_id, proposal_id)
        return [ProposalReviewRead.model_validate(item) for item in items]

