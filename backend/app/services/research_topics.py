"""Service layer for research topics and duplicate topic candidates."""

from __future__ import annotations

import re
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
    AlertEvent,
    Department,
    DuplicateTopicCandidate,
    ResearchProposal,
    ResearchTopic,
    UniversityMembership,
)
from ..schemas.research_topics import (
    DuplicateCandidateCreate,
    DuplicateCandidateReview,
    ResearchTopicCreate,
    ResearchTopicUpdate,
)


def normalize_title(title: str) -> str:
    """Produce normalized alphanumeric string for reliable duplicate detection."""
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    return " ".join(cleaned.split())


class ResearchTopicService:
    @staticmethod
    def create_topic(
        db: Session,
        university_id: uuid.UUID,
        data: ResearchTopicCreate,
        user_id: int,
    ) -> ResearchTopic:
        # Validate department in this university
        dept = db.scalar(
            select(Department).where(
                Department.id == data.department_id,
                Department.university_id == university_id,
            )
        )
        if not dept:
            raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")

        # Validate user membership
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        norm = normalize_title(data.title)
        topic = ResearchTopic(
            university_id=university_id,
            title=data.title.strip(),
            normalized_title=norm,
            abstract=data.abstract,
            keywords=data.keywords,
            department_id=data.department_id,
            created_by_id=user_id,
            is_active=data.is_active,
        )
        db.add(topic)
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def get_topic(db: Session, university_id: uuid.UUID, topic_id: uuid.UUID) -> ResearchTopic:
        topic = db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.id == topic_id,
                ResearchTopic.university_id == university_id,
            )
        )
        if not topic:
            raise NotFoundError(f"Research topic {topic_id} not found in this university")
        return topic

    @staticmethod
    def list_topics(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[ResearchTopic], int, int]:
        query = select(ResearchTopic).where(ResearchTopic.university_id == university_id).order_by(ResearchTopic.created_at.desc())
        if department_id:
            query = query.where(ResearchTopic.department_id == department_id)
        if is_active is not None:
            query = query.where(ResearchTopic.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                or_(
                    ResearchTopic.title.ilike(s),
                    ResearchTopic.normalized_title.ilike(s),
                    ResearchTopic.keywords.ilike(s),
                )
            )
        return paginate(query, db, params)

    @staticmethod
    def update_topic(
        db: Session,
        university_id: uuid.UUID,
        topic_id: uuid.UUID,
        data: ResearchTopicUpdate,
    ) -> ResearchTopic:
        topic = ResearchTopicService.get_topic(db, university_id, topic_id)
        if data.department_id is not None and data.department_id != topic.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            topic.department_id = data.department_id

        if data.title is not None:
            topic.title = data.title.strip()
            topic.normalized_title = normalize_title(data.title)
        if data.abstract is not None:
            topic.abstract = data.abstract
        if data.keywords is not None:
            topic.keywords = data.keywords
        if data.is_active is not None:
            topic.is_active = data.is_active

        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def delete_topic(db: Session, university_id: uuid.UUID, topic_id: uuid.UUID) -> None:
        topic = ResearchTopicService.get_topic(db, university_id, topic_id)
        referenced = db.scalar(
            select(ResearchProposal.id).where(ResearchProposal.topic_id == topic_id).limit(1)
        )
        if referenced:
            raise SpecializedOperationError(
                "Cannot delete research topic: proposals reference it. "
                "Delete or reassign the proposals first."
            )
        db.delete(topic)
        db.commit()


class DuplicateCandidateService:
    @staticmethod
    def create_candidate(
        db: Session,
        university_id: uuid.UUID,
        data: DuplicateCandidateCreate,
    ) -> DuplicateTopicCandidate:
        alert = db.scalar(
            select(AlertEvent).where(
                AlertEvent.id == data.alert_event_id,
                AlertEvent.university_id == university_id,
            )
        )
        if not alert:
            raise ForeignKeyViolationError(f"Alert event {data.alert_event_id} not found in this university")

        ResearchTopicService.get_topic(db, university_id, data.topic_a_id)
        ResearchTopicService.get_topic(db, university_id, data.topic_b_id)

        # Enforce check constraint topic_a_id < topic_b_id
        topic_a = min(data.topic_a_id, data.topic_b_id)
        topic_b = max(data.topic_a_id, data.topic_b_id)
        if topic_a == topic_b:
            raise InvalidInputError("Topic A and Topic B must be distinct topics")

        existing_alert = db.scalar(
            select(DuplicateTopicCandidate).where(
                DuplicateTopicCandidate.alert_event_id == data.alert_event_id
            )
        )
        if existing_alert:
            raise DuplicateResourceError(f"Duplicate candidate for alert {data.alert_event_id} already exists")

        candidate = DuplicateTopicCandidate(
            university_id=university_id,
            alert_event_id=data.alert_event_id,
            topic_a_id=topic_a,
            topic_b_id=topic_b,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def review_candidate(
        db: Session,
        university_id: uuid.UUID,
        candidate_id: uuid.UUID,
        data: DuplicateCandidateReview,
        reviewer_id: int,
    ) -> DuplicateTopicCandidate:
        candidate = db.scalar(
            select(DuplicateTopicCandidate).where(
                DuplicateTopicCandidate.id == candidate_id,
                DuplicateTopicCandidate.university_id == university_id,
            )
        )
        if not candidate:
            raise NotFoundError(f"Duplicate topic candidate {candidate_id} not found in this university")

        candidate.review_status = data.review_status
        candidate.reviewed_by_id = reviewer_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def list_candidates(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        review_status: Optional[str] = None,
    ) -> tuple[Sequence[DuplicateTopicCandidate], int, int]:
        query = select(DuplicateTopicCandidate).where(DuplicateTopicCandidate.university_id == university_id)
        if review_status:
            query = query.where(DuplicateTopicCandidate.review_status == review_status)
        return paginate(query, db, params)

    @staticmethod
    def get_candidate(
        db: Session,
        university_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> DuplicateTopicCandidate:
        candidate = db.scalar(
            select(DuplicateTopicCandidate).where(
                DuplicateTopicCandidate.id == candidate_id,
                DuplicateTopicCandidate.university_id == university_id,
            )
        )
        if not candidate:
            raise NotFoundError(f"Duplicate topic candidate {candidate_id} not found in this university")
        return candidate

    @staticmethod
    def delete_candidate(
        db: Session,
        university_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> None:
        candidate = DuplicateCandidateService.get_candidate(db, university_id, candidate_id)
        db.delete(candidate)
        db.commit()

