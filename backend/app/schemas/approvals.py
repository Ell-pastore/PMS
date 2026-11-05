"""Pydantic schemas for versioned approval workflows, steps, instances, and actions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- APPROVAL WORKFLOW ---
class ApprovalWorkflowBase(BaseModel):
    workflow_type: str = Field(..., max_length=128)
    department_id: Optional[int] = None


class ApprovalWorkflowCreate(ApprovalWorkflowBase):
    pass


class ApprovalWorkflowUpdate(BaseModel):
    workflow_type: Optional[str] = Field(None, max_length=128)
    department_id: Optional[int] = None


class ApprovalWorkflowRead(ApprovalWorkflowBase):
    id: uuid.UUID
    university_id: uuid.UUID
    active_version_id: Optional[uuid.UUID] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- APPROVAL WORKFLOW VERSION ---
class ApprovalWorkflowVersionRead(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    university_id: uuid.UUID
    version_number: int
    publication_state: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- APPROVAL WORKFLOW STEP ---
class ApprovalWorkflowStepBase(BaseModel):
    step_number: int = Field(..., gt=0)
    name: str = Field(..., max_length=255)
    required_role_id: Optional[int] = None
    required_approvals: int = Field(1, gt=0)
    is_mandatory: bool = True


class ApprovalWorkflowStepCreate(ApprovalWorkflowStepBase):
    pass


class ApprovalWorkflowStepUpdate(BaseModel):
    step_number: Optional[int] = Field(None, gt=0)
    name: Optional[str] = Field(None, max_length=255)
    required_role_id: Optional[int] = None
    required_approvals: Optional[int] = Field(None, gt=0)
    is_mandatory: Optional[bool] = None


class ApprovalWorkflowStepRead(ApprovalWorkflowStepBase):
    id: uuid.UUID
    workflow_version_id: uuid.UUID
    workflow_id: uuid.UUID
    university_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# --- APPROVAL INSTANCE ---
class ApprovalInstanceCreate(BaseModel):
    workflow_id: uuid.UUID
    target_entity_type: str = Field(..., max_length=128)
    target_entity_id: uuid.UUID
    workflow_version_id: Optional[uuid.UUID] = None


class ApprovalInstanceRead(BaseModel):
    id: uuid.UUID
    workflow_version_id: uuid.UUID
    workflow_id: uuid.UUID
    university_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    status: str
    initiated_by_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- APPROVAL ACTION ---
class ApprovalActionCreate(BaseModel):
    step_id: uuid.UUID
    decision: str = Field(..., max_length=32, pattern="^(approved|rejected)$")
    comments: Optional[str] = None


class ApprovalActionRead(BaseModel):
    id: uuid.UUID
    instance_id: uuid.UUID
    step_id: uuid.UUID
    workflow_version_id: uuid.UUID
    workflow_id: uuid.UUID
    university_id: uuid.UUID
    acting_user_id: int
    decision: str
    comments: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

