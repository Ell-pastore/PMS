"""Pydantic schemas for research topics and duplicate topic candidates."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResearchTopicBase(BaseModel):
    title: str = Field(..., max_length=500)
    department_id: int
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    is_active: bool = True


class ResearchTopicCreate(ResearchTopicBase):
    pass


class ResearchTopicUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    department_id: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None


class ResearchTopicRead(ResearchTopicBase):
    id: uuid.UUID
    university_id: uuid.UUID
    normalized_title: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuplicateCandidateCreate(BaseModel):
    alert_event_id: uuid.UUID
    topic_a_id: uuid.UUID
    topic_b_id: uuid.UUID


class DuplicateCandidateReview(BaseModel):
    review_status: str = Field(..., max_length=32)


class DuplicateCandidateRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    alert_event_id: uuid.UUID
    topic_a_id: uuid.UUID
    topic_b_id: uuid.UUID
    review_status: str
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

