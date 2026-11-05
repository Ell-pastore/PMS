"""Pydantic schemas for research projects, milestones, templates, and participants."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- PROJECT ---
class ResearchProjectBase(BaseModel):
    proposal_id: uuid.UUID
    department_id: int
    title: str = Field(..., max_length=500)
    abstract: Optional[str] = None
    start_date: date
    expected_end_date: Optional[date] = None
    status: str = Field("active", max_length=32)


class ResearchProjectCreate(ResearchProjectBase):
    pass


class ResearchProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    department_id: Optional[int] = None
    abstract: Optional[str] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=32)


class ResearchProjectRead(ResearchProjectBase):
    id: uuid.UUID
    university_id: uuid.UUID
    actual_end_date: Optional[date] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectStatusTransition(BaseModel):
    new_status: str = Field(..., max_length=32, pattern="^(active|on_hold|completed|cancelled|archived)$")
    reason: Optional[str] = None
    actual_end_date: Optional[date] = None


# --- PARTICIPANTS ---
class ProjectParticipantCreate(BaseModel):
    student_id: int
    participation_role: str = Field(..., max_length=64)
    is_lead: bool = False
    started_at: Optional[datetime] = None


class ProjectParticipantEnd(BaseModel):
    ended_at: Optional[datetime] = None


class ProjectParticipantRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    project_id: uuid.UUID
    student_id: int
    participation_role: str
    is_lead: bool
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- SUPERVISORS ---
class ProjectSupervisorCreate(BaseModel):
    staff_id: int
    assignment_role: str = Field(..., max_length=32, pattern="^(primary|co_supervisor)$")
    started_at: Optional[datetime] = None


class ProjectSupervisorEnd(BaseModel):
    ended_at: Optional[datetime] = None


class ProjectSupervisorRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    project_id: uuid.UUID
    staff_id: int
    assigned_by_id: int
    assignment_role: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- MILESTONE TEMPLATES ---
class MilestoneTemplateBase(BaseModel):
    department_id: Optional[int] = None
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    default_duration_days: int = Field(..., gt=0)
    is_active: bool = True


class MilestoneTemplateCreate(MilestoneTemplateBase):
    pass


class MilestoneTemplateUpdate(BaseModel):
    department_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    default_duration_days: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class MilestoneTemplateRead(MilestoneTemplateBase):
    id: uuid.UUID
    university_id: uuid.UUID
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PROJECT MILESTONES ---
class ProjectMilestoneBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    sequence_number: int = Field(..., gt=0)
    due_date: date
    template_id: Optional[uuid.UUID] = None
    status: str = Field("pending", max_length=32)


class ProjectMilestoneCreate(ProjectMilestoneBase):
    pass


class ProjectMilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    sequence_number: Optional[int] = Field(None, gt=0)
    due_date: Optional[date] = None
    template_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(None, max_length=32)
    completed_at: Optional[datetime] = None


class ProjectMilestoneRead(ProjectMilestoneBase):
    id: uuid.UUID
    university_id: uuid.UUID
    project_id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- STATUS HISTORY ---
class ProjectStatusHistoryRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    project_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    actor_id: int
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

