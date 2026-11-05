"""Pydantic schemas for research proposals, revisions, participants, supervisors, and reviews."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- PROPOSAL ---
class ResearchProposalBase(BaseModel):
    topic_id: uuid.UUID
    department_id: int
    title: str = Field(..., max_length=500)
    abstract: Optional[str] = None
    research_problem: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcomes: Optional[str] = None


class ResearchProposalCreate(ResearchProposalBase):
    pass


class ResearchProposalUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    department_id: Optional[int] = None
    abstract: Optional[str] = None
    research_problem: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcomes: Optional[str] = None


class ResearchProposalRead(ResearchProposalBase):
    id: uuid.UUID
    university_id: uuid.UUID
    submitting_user_id: int
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalStatusTransition(BaseModel):
    new_status: str = Field(..., max_length=32, pattern="^(draft|submitted|under_review|revision_requested|approved|rejected|withdrawn)$")
    reason: Optional[str] = None


# --- PARTICIPANTS ---
class ProposalParticipantCreate(BaseModel):
    student_id: int
    participation_role: str = Field(..., max_length=64)
    is_lead: bool = False


class ProposalParticipantUpdate(BaseModel):
    participation_role: Optional[str] = Field(None, max_length=64)
    is_lead: Optional[bool] = None


class ProposalParticipantRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    proposal_id: uuid.UUID
    student_id: int
    participation_role: str
    is_lead: bool

    model_config = ConfigDict(from_attributes=True)


# --- SUPERVISORS ---
class ProposalSupervisorCreate(BaseModel):
    staff_id: int
    assignment_role: str = Field(..., max_length=32, pattern="^(primary|co_supervisor)$")


class ProposalSupervisorEnd(BaseModel):
    ended_at: Optional[datetime] = None


class ProposalSupervisorRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    proposal_id: uuid.UUID
    staff_id: int
    assigned_by_id: int
    assignment_role: str
    assigned_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- REVISIONS ---
class ProposalRevisionCreate(BaseModel):
    title: str = Field(..., max_length=500)
    abstract: Optional[str] = None
    research_problem: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcomes: Optional[str] = None


class ProposalRevisionRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    proposal_id: uuid.UUID
    revision_number: int
    title: str
    abstract: Optional[str] = None
    research_problem: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    expected_outcomes: Optional[str] = None
    submitted_by_id: int
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- REVIEWS ---
class ProposalReviewCreate(BaseModel):
    decision: str = Field(..., max_length=32, pattern="^(approved|rejected|revision_requested|commented)$")
    comments: Optional[str] = None


class ProposalReviewRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    proposal_id: uuid.UUID
    reviewer_id: int
    decision: str
    comments: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- STATUS HISTORY ---
class ProposalStatusHistoryRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    proposal_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    actor_id: int
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

