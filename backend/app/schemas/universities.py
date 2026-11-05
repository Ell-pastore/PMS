"""Pydantic schemas for universities, memberships, and settings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class UniversityBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    is_active: bool = True


class UniversityCreate(UniversityBase):
    pass


class UniversityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class UniversityRead(UniversityBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UniversityMembershipCreate(BaseModel):
    user_id: int
    is_active: bool = True


class UniversityMembershipUpdate(BaseModel):
    is_active: bool


class UniversityMembershipRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UniversitySettingsBase(BaseModel):
    max_supervisors_per_project: int = Field(2, gt=0)
    max_active_projects_per_student: int = Field(1, gt=0)
    max_active_supervisees_per_supervisor: int = Field(10, gt=0)
    student_inactivity_days: int = Field(30, gt=0)
    milestone_reminder_days: int = Field(7, ge=0)
    default_proposal_review_days: int = Field(14, gt=0)


class UniversitySettingsCreate(UniversitySettingsBase):
    pass


class UniversitySettingsUpdate(BaseModel):
    max_supervisors_per_project: Optional[int] = Field(None, gt=0)
    max_active_projects_per_student: Optional[int] = Field(None, gt=0)
    max_active_supervisees_per_supervisor: Optional[int] = Field(None, gt=0)
    student_inactivity_days: Optional[int] = Field(None, gt=0)
    milestone_reminder_days: Optional[int] = Field(None, ge=0)
    default_proposal_review_days: Optional[int] = Field(None, gt=0)


class UniversitySettingsRead(UniversitySettingsBase):
    id: uuid.UUID
    university_id: uuid.UUID
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentSettingsBase(BaseModel):
    max_supervisors_per_project: Optional[int] = Field(None, gt=0)
    max_active_projects_per_student: Optional[int] = Field(None, gt=0)
    max_active_supervisees_per_supervisor: Optional[int] = Field(None, gt=0)
    student_inactivity_days: Optional[int] = Field(None, gt=0)
    milestone_reminder_days: Optional[int] = Field(None, ge=0)
    default_proposal_review_days: Optional[int] = Field(None, gt=0)


class DepartmentSettingsCreate(DepartmentSettingsBase):
    department_id: int


class DepartmentSettingsUpdate(DepartmentSettingsBase):
    pass


class DepartmentSettingsRead(DepartmentSettingsBase):
    id: uuid.UUID
    university_id: uuid.UUID
    department_id: int
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemSettingCreate(BaseModel):
    setting_key: str = Field(..., max_length=128)
    setting_value: dict[str, Any] = Field(default_factory=dict)


class SystemSettingUpdate(BaseModel):
    setting_value: dict[str, Any]


class SystemSettingRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    setting_key: str
    setting_value: dict[str, Any]
    updated_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

