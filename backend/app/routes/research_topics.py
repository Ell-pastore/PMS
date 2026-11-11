"""FastAPI routes for research topics and duplicate candidates."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.research_topics import (
    DuplicateCandidateController,
    ResearchTopicController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.research_topics import (
    DuplicateCandidateCreate,
    DuplicateCandidateRead,
    DuplicateCandidateReview,
    ResearchTopicCreate,
    ResearchTopicRead,
    ResearchTopicUpdate,
)

topics_router = APIRouter(prefix="/research-topics", tags=["Research Topics"])
duplicates_router = APIRouter(prefix="/duplicate-topic-candidates", tags=["Duplicate Topic Candidates"])


# --- RESEARCH TOPICS ---
@topics_router.post("", response_model=ResearchTopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(
    data: ResearchTopicCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ResearchTopicController.create_topic(db, tenant, data)


@topics_router.get("", response_model=PaginatedResponse[ResearchTopicRead])
def list_topics(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchTopicController.list_topics(
        db, tenant, params, department_id=department_id, search=search, is_active=is_active
    )


@topics_router.get("/{topic_id}", response_model=ResearchTopicRead)
def get_topic(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ResearchTopicController.get_topic(db, tenant, topic_id)


@topics_router.patch("/{topic_id}", response_model=ResearchTopicRead)
@topics_router.put("/{topic_id}", response_model=ResearchTopicRead)
def update_topic(
    topic_id: uuid.UUID,
    data: ResearchTopicUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ResearchTopicController.update_topic(db, tenant, topic_id, data)


@topics_router.delete("/{topic_id}", status_code=status.HTTP_200_OK)
def delete_topic(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return ResearchTopicController.delete_topic(db, tenant, topic_id)


# --- DUPLICATE CANDIDATES ---
@duplicates_router.post("", response_model=DuplicateCandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    data: DuplicateCandidateCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DuplicateCandidateController.create_candidate(db, tenant, data)


@duplicates_router.get("", response_model=PaginatedResponse[DuplicateCandidateRead])
def list_candidates(
    params: PaginationParams = Depends(),
    review_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DuplicateCandidateController.list_candidates(
        db, tenant, params, review_status=review_status
    )


@duplicates_router.get("/{candidate_id}", response_model=DuplicateCandidateRead)
def get_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DuplicateCandidateController.get_candidate(db, tenant, candidate_id)


@duplicates_router.post("/{candidate_id}/review", response_model=DuplicateCandidateRead)
def review_candidate(
    candidate_id: uuid.UUID,
    data: DuplicateCandidateReview,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return DuplicateCandidateController.review_candidate(db, tenant, candidate_id, data)


@duplicates_router.delete("/{candidate_id}", status_code=status.HTTP_200_OK)
def delete_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DuplicateCandidateController.delete_candidate(db, tenant, candidate_id)

