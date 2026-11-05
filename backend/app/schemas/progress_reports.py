"""Pydantic schemas for progress reports, reviews, comments, and student activity."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- PROGRESS REPORT ---
class ProgressReportBase(BaseModel):
    project_id: uuid.UUID
    milestone_id: Optional[uuid.UUID] = None
    period_start: date
    period_end: date
    title: str = Field(..., max_length=255)
    content: str
    challenges: Optional[str] = None
    next_steps: Optional[str] = None


class ProgressReportCreate(ProgressReportBase):
    pass


class ProgressReportUpdate(BaseModel):
    milestone_id: Optional[uuid.UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    challenges: Optional[str] = None
    next_steps: Optional[str] = None


class ProgressReportRead(ProgressReportBase):
    id: uuid.UUID
    university_id: uuid.UUID
    submitter_id: int
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PROGRESS REPORT REVIEW ---
class ProgressReportReviewCreate(BaseModel):
    decision: str = Field(..., max_length=32, pattern="^(approved|rejected|revision_requested|commented)$")
    feedback: Optional[str] = None


class ProgressReportReviewRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    report_id: uuid.UUID
    reviewer_id: int
    decision: str
    feedback: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PROJECT COMMENTS ---
class ProjectCommentCreate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None
    progress_report_id: Optional[uuid.UUID] = None
    body: str


class ProjectCommentUpdate(BaseModel):
    body: str


class ProjectCommentRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None
    progress_report_id: Optional[uuid.UUID] = None
    author_id: int
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- STUDENT ACTIVITY ---
class StudentActivityCreate(BaseModel):
    student_id: int
    project_id: Optional[uuid.UUID] = None
    activity_type: str = Field(..., max_length=64)
    activity_metadata: dict[str, Any] = Field(default_factory=dict)


class StudentActivityRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    student_id: int
    project_id: Optional[uuid.UUID] = None
    activity_type: str
    activity_metadata: dict[str, Any]
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

