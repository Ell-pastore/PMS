"""FastAPI routes for research proposals, revisions, participants, supervisors, and reviews."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.research_proposals import (
    ProposalParticipantController,
    ProposalReviewController,
    ProposalRevisionController,
    ProposalSupervisorController,
    ResearchProposalController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context
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

proposals_router = APIRouter(prefix="/research-proposals", tags=["Research Proposals"])


# --- PROPOSAL CRUD & SEARCH ---
@proposals_router.post("", response_model=ResearchProposalRead, status_code=status.HTTP_201_CREATED)
def create_proposal(
    data: ResearchProposalCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.create_proposal(db, tenant, data)


@proposals_router.get("", response_model=PaginatedResponse[ResearchProposalRead])
def list_proposals(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    topic_id: Optional[uuid.UUID] = Query(None),
    submitting_user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.list_proposals(
        db,
        tenant,
        params,
        department_id=department_id,
        topic_id=topic_id,
        submitting_user_id=submitting_user_id,
        status=status,
        search=search,
    )


@proposals_router.get("/{proposal_id}", response_model=ResearchProposalRead)
def get_proposal(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.get_proposal(db, tenant, proposal_id)


@proposals_router.patch("/{proposal_id}", response_model=ResearchProposalRead)
@proposals_router.put("/{proposal_id}", response_model=ResearchProposalRead)
def update_proposal(
    proposal_id: uuid.UUID,
    data: ResearchProposalUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.update_proposal(db, tenant, proposal_id, data)


@proposals_router.delete("/{proposal_id}", status_code=status.HTTP_200_OK)
def delete_proposal(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.delete_proposal(db, tenant, proposal_id)


@proposals_router.post("/{proposal_id}/submit", response_model=ResearchProposalRead)
def submit_proposal(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.submit_proposal(db, tenant, proposal_id)


@proposals_router.post("/{proposal_id}/status", response_model=ResearchProposalRead)
def transition_status(
    proposal_id: uuid.UUID,
    data: ProposalStatusTransition,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchProposalController.transition_status(db, tenant, proposal_id, data)


# --- PARTICIPANTS ---
@proposals_router.post("/{proposal_id}/participants", response_model=ProposalParticipantRead, status_code=status.HTTP_201_CREATED)
def add_participant(
    proposal_id: uuid.UUID,
    data: ProposalParticipantCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalParticipantController.add_participant(db, tenant, proposal_id, data)


@proposals_router.get("/{proposal_id}/participants", response_model=list[ProposalParticipantRead])
def list_participants(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalParticipantController.list_participants(db, tenant, proposal_id)


@proposals_router.delete("/{proposal_id}/participants/{participant_id}", status_code=status.HTTP_200_OK)
def remove_participant(
    proposal_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalParticipantController.remove_participant(db, tenant, proposal_id, participant_id)


# --- SUPERVISORS ---
@proposals_router.post("/{proposal_id}/supervisors", response_model=ProposalSupervisorRead, status_code=status.HTTP_201_CREATED)
def assign_supervisor(
    proposal_id: uuid.UUID,
    data: ProposalSupervisorCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalSupervisorController.assign_supervisor(db, tenant, proposal_id, data)


@proposals_router.get("/{proposal_id}/supervisors", response_model=list[ProposalSupervisorRead])
def list_supervisors(
    proposal_id: uuid.UUID,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalSupervisorController.list_supervisors(db, tenant, proposal_id, active_only=active_only)


@proposals_router.post("/{proposal_id}/supervisors/{supervisor_id}/end", response_model=ProposalSupervisorRead)
def end_supervisor(
    proposal_id: uuid.UUID,
    supervisor_id: uuid.UUID,
    data: ProposalSupervisorEnd,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalSupervisorController.end_supervisor(db, tenant, proposal_id, supervisor_id, data)


# --- REVISIONS ---
@proposals_router.post("/{proposal_id}/revisions", response_model=ProposalRevisionRead, status_code=status.HTTP_201_CREATED)
def create_revision(
    proposal_id: uuid.UUID,
    data: ProposalRevisionCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalRevisionController.create_revision(db, tenant, proposal_id, data)


@proposals_router.get("/{proposal_id}/revisions", response_model=list[ProposalRevisionRead])
def list_revisions(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalRevisionController.list_revisions(db, tenant, proposal_id)


# --- REVIEWS ---
@proposals_router.post("/{proposal_id}/reviews", response_model=ProposalReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    proposal_id: uuid.UUID,
    data: ProposalReviewCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalReviewController.create_review(db, tenant, proposal_id, data)


@proposals_router.get("/{proposal_id}/reviews", response_model=list[ProposalReviewRead])
def list_reviews(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProposalReviewController.list_reviews(db, tenant, proposal_id)

