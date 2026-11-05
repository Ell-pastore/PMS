"""Pydantic schemas for faculties, departments, leadership, and profiles."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- FACULTY ---
class FacultyBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    description: Optional[str] = None
    is_active: bool = True


class FacultyCreate(FacultyBase):
    pass


class FacultyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FacultyRead(FacultyBase):
    id: int
    university_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DEPARTMENT ---
class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=64)
    faculty_id: int
    description: Optional[str] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=64)
    faculty_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentRead(DepartmentBase):
    id: int
    university_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DEPARTMENT LEADERSHIP ---
class DepartmentLeadershipCreate(BaseModel):
    department_id: int
    staff_id: int
    started_at: Optional[datetime] = None


class DepartmentLeadershipEnd(BaseModel):
    ended_at: Optional[datetime] = None


class DepartmentLeadershipRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    department_id: int
    staff_id: int
    appointed_by_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- STAFF PROFILE ---
class StaffProfileBase(BaseModel):
    user_id: int
    staff_id: str = Field(..., max_length=64)
    department_id: int
    job_title: str = Field(..., max_length=128)
    academic_designation: Optional[str] = Field(None, max_length=128)
    gender: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=32)


class StaffProfileCreate(StaffProfileBase):
    pass


class StaffProfileUpdate(BaseModel):
    staff_id: Optional[str] = Field(None, max_length=64)
    department_id: Optional[int] = None
    job_title: Optional[str] = Field(None, max_length=128)
    academic_designation: Optional[str] = Field(None, max_length=128)
    gender: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=32)


class StaffProfileRead(StaffProfileBase):
    id: int
    university_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- STUDENT PROFILE ---
class StudentProfileBase(BaseModel):
    user_id: int
    student_id: str = Field(..., max_length=64)
    department_id: int
    academic_level: str = Field(..., max_length=64)
    gender: Optional[str] = Field(None, max_length=32)
    enrollment_date: Optional[date] = None
    academic_account_status: str = Field("active", max_length=32)
    phone_number: Optional[str] = Field(None, max_length=32)


class StudentProfileCreate(StudentProfileBase):
    pass


class StudentProfileUpdate(BaseModel):
    student_id: Optional[str] = Field(None, max_length=64)
    department_id: Optional[int] = None
    academic_level: Optional[str] = Field(None, max_length=64)
    gender: Optional[str] = Field(None, max_length=32)
    enrollment_date: Optional[date] = None
    academic_account_status: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=32)


class StudentProfileRead(StudentProfileBase):
    id: int
    university_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

