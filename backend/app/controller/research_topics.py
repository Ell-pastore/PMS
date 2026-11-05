"""Controllers for research topics and duplicate topic candidates."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.research_topics import (
    DuplicateCandidateCreate,
    DuplicateCandidateRead,
    DuplicateCandidateReview,
    ResearchTopicCreate,
    ResearchTopicRead,
    ResearchTopicUpdate,
)
from ..services.research_topics import (
    DuplicateCandidateService,
    ResearchTopicService,
)


class ResearchTopicController:
    @staticmethod
    def create_topic(db: Session, tenant: TenantContext, data: ResearchTopicCreate) -> ResearchTopicRead:
        topic = ResearchTopicService.create_topic(db, tenant.university_id, data, tenant.user.id)
        return ResearchTopicRead.model_validate(topic)

    @staticmethod
    def get_topic(db: Session, tenant: TenantContext, topic_id: uuid.UUID) -> ResearchTopicRead:
        topic = ResearchTopicService.get_topic(db, tenant.university_id, topic_id)
        return ResearchTopicRead.model_validate(topic)

    @staticmethod
    def list_topics(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[ResearchTopicRead]:
        items, total, total_pages = ResearchTopicService.list_topics(
            db, tenant.university_id, params, department_id=department_id, search=search, is_active=is_active
        )
        return PaginatedResponse(
            items=[ResearchTopicRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_topic(
        db: Session,
        tenant: TenantContext,
        topic_id: uuid.UUID,
        data: ResearchTopicUpdate,
    ) -> ResearchTopicRead:
        topic = ResearchTopicService.update_topic(db, tenant.university_id, topic_id, data)
        return ResearchTopicRead.model_validate(topic)

    @staticmethod
    def delete_topic(db: Session, tenant: TenantContext, topic_id: uuid.UUID) -> dict[str, str]:
        ResearchTopicService.delete_topic(db, tenant.university_id, topic_id)
        return {"status": "success", "message": f"Topic {topic_id} deleted"}


class DuplicateCandidateController:
    @staticmethod
    def create_candidate(
        db: Session,
        tenant: TenantContext,
        data: DuplicateCandidateCreate,
    ) -> DuplicateCandidateRead:
        candidate = DuplicateCandidateService.create_candidate(db, tenant.university_id, data)
        return DuplicateCandidateRead.model_validate(candidate)

    @staticmethod
    def review_candidate(
        db: Session,
        tenant: TenantContext,
        candidate_id: uuid.UUID,
        data: DuplicateCandidateReview,
    ) -> DuplicateCandidateRead:
        candidate = DuplicateCandidateService.review_candidate(
            db, tenant.university_id, candidate_id, data, tenant.user.id
        )
        return DuplicateCandidateRead.model_validate(candidate)

    @staticmethod
    def get_candidate(
        db: Session,
        tenant: TenantContext,
        candidate_id: uuid.UUID,
    ) -> DuplicateCandidateRead:
        candidate = DuplicateCandidateService.get_candidate(db, tenant.university_id, candidate_id)
        return DuplicateCandidateRead.model_validate(candidate)

    @staticmethod
    def list_candidates(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        review_status: Optional[str] = None,
    ) -> PaginatedResponse[DuplicateCandidateRead]:
        items, total, total_pages = DuplicateCandidateService.list_candidates(
            db, tenant.university_id, params, review_status=review_status
        )
        return PaginatedResponse(
            items=[DuplicateCandidateRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_candidate(
        db: Session,
        tenant: TenantContext,
        candidate_id: uuid.UUID,
    ) -> dict[str, str]:
        DuplicateCandidateService.delete_candidate(db, tenant.university_id, candidate_id)
        return {"status": "success", "message": f"Candidate {candidate_id} deleted"}

