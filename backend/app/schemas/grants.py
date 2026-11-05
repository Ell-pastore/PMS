"""Pydantic schemas for grant opportunities, applications, awards, expenditures, and reports."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- GRANT OPPORTUNITY ---
class GrantOpportunityBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    funding_organization: str = Field(..., max_length=255)
    eligibility_criteria: Optional[str] = None
    application_opens_at: datetime
    application_closes_at: datetime
    min_funding_amount: Decimal = Field(..., ge=0)
    max_funding_amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    status: str = Field("draft", max_length=32)


class GrantOpportunityCreate(GrantOpportunityBase):
    pass


class GrantOpportunityUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    funding_organization: Optional[str] = Field(None, max_length=255)
    eligibility_criteria: Optional[str] = None
    application_opens_at: Optional[datetime] = None
    application_closes_at: Optional[datetime] = None
    min_funding_amount: Optional[Decimal] = Field(None, ge=0)
    max_funding_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[str] = Field(None, max_length=32)


class GrantOpportunityRead(GrantOpportunityBase):
    id: uuid.UUID
    university_id: uuid.UUID
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- GRANT APPLICATION ---
class GrantApplicationBase(BaseModel):
    opportunity_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=500)
    proposal: str
    requested_amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class GrantApplicationCreate(GrantApplicationBase):
    pass


class GrantApplicationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    project_id: Optional[uuid.UUID] = None
    proposal: Optional[str] = None
    requested_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class GrantApplicationRead(GrantApplicationBase):
    id: uuid.UUID
    university_id: uuid.UUID
    applicant_id: int
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrantApplicationParticipantCreate(BaseModel):
    user_id: int
    participation_role: str = Field(..., max_length=64)


class GrantApplicationParticipantRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    application_id: uuid.UUID
    user_id: int
    participation_role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrantApplicationReviewCreate(BaseModel):
    decision: str = Field(..., max_length=32, pattern="^(approved|rejected|revision_requested|commented)$")
    recommended_amount: Optional[Decimal] = Field(None, ge=0)
    comments: Optional[str] = None


class GrantApplicationReviewRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    application_id: uuid.UUID
    reviewer_id: int
    decision: str
    recommended_amount: Optional[Decimal] = None
    comments: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrantApplicationStatusHistoryRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    application_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    actor_id: int
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- GRANT AWARD ---
class GrantAwardBase(BaseModel):
    application_id: uuid.UUID
    award_reference: str = Field(..., max_length=128)
    awarded_amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    award_start_date: date
    award_end_date: date
    status: str = Field("active", max_length=32)


class GrantAwardCreate(GrantAwardBase):
    pass


class GrantAwardUpdate(BaseModel):
    award_reference: Optional[str] = Field(None, max_length=128)
    awarded_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    award_start_date: Optional[date] = None
    award_end_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=32)


class GrantAwardRead(GrantAwardBase):
    id: uuid.UUID
    university_id: uuid.UUID
    approved_by_id: int
    approved_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- GRANT PROJECT ALLOCATION ---
class GrantAllocationCreate(BaseModel):
    project_id: uuid.UUID
    allocated_amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class GrantAllocationRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    award_id: uuid.UUID
    project_id: uuid.UUID
    allocated_amount: Decimal
    currency: str
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- GRANT EXPENDITURE ---
class GrantExpenditureBase(BaseModel):
    project_id: Optional[uuid.UUID] = None
    description: str
    amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    expenditure_date: date
    reference_number: Optional[str] = Field(None, max_length=128)
    status: str = Field("draft", max_length=32)


class GrantExpenditureCreate(GrantExpenditureBase):
    pass


class GrantExpenditureUpdate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    expenditure_date: Optional[date] = None
    reference_number: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = Field(None, max_length=32)


class GrantExpenditureRead(GrantExpenditureBase):
    id: uuid.UUID
    university_id: uuid.UUID
    award_id: uuid.UUID
    recorded_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- GRANT PROGRESS REPORT ---
class GrantProgressReportBase(BaseModel):
    period_start: date
    period_end: date
    narrative: str
    financial_summary: Optional[str] = None


class GrantProgressReportCreate(GrantProgressReportBase):
    pass


class GrantProgressReportUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    narrative: Optional[str] = None
    financial_summary: Optional[str] = None
    status: Optional[str] = Field(None, max_length=32)


class GrantProgressReportRead(GrantProgressReportBase):
    id: uuid.UUID
    university_id: uuid.UUID
    award_id: uuid.UUID
    submitter_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

