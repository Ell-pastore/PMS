"""FastAPI routes for faculties, departments, leadership, and profiles."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.organization import (
    DepartmentController,
    DepartmentLeadershipController,
    FacultyController,
    StaffProfileController,
    StudentProfileController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.organization import (
    DepartmentCreate,
    DepartmentLeadershipCreate,
    DepartmentLeadershipEnd,
    DepartmentLeadershipRead,
    DepartmentRead,
    DepartmentUpdate,
    FacultyCreate,
    FacultyRead,
    FacultyUpdate,
    StaffProfileCreate,
    StaffProfileRead,
    StaffProfileUpdate,
    StudentProfileCreate,
    StudentProfileRead,
    StudentProfileUpdate,
)

faculties_router = APIRouter(prefix="/faculties", tags=["Faculties"])
departments_router = APIRouter(prefix="/departments", tags=["Departments"])
leadership_router = APIRouter(prefix="/department-leadership", tags=["Department Leadership"])
staff_router = APIRouter(prefix="/staff-profiles", tags=["Staff Profiles"])
students_router = APIRouter(prefix="/student-profiles", tags=["Student Profiles"])


# --- FACULTIES ---
@faculties_router.post("", response_model=FacultyRead, status_code=status.HTTP_201_CREATED)
def create_faculty(
    data: FacultyCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return FacultyController.create_faculty(db, tenant, data)


@faculties_router.get("", response_model=PaginatedResponse[FacultyRead])
def list_faculties(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return FacultyController.list_faculties(db, tenant, params, search=search, is_active=is_active)


@faculties_router.get("/{faculty_id}", response_model=FacultyRead)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return FacultyController.get_faculty(db, tenant, faculty_id)


@faculties_router.patch("/{faculty_id}", response_model=FacultyRead)
@faculties_router.put("/{faculty_id}", response_model=FacultyRead)
def update_faculty(
    faculty_id: int,
    data: FacultyUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return FacultyController.update_faculty(db, tenant, faculty_id, data)


@faculties_router.delete("/{faculty_id}", status_code=status.HTTP_200_OK)
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return FacultyController.delete_faculty(db, tenant, faculty_id)


# --- DEPARTMENTS ---
@departments_router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentController.create_department(db, tenant, data)


@departments_router.get("", response_model=PaginatedResponse[DepartmentRead])
def list_departments(
    params: PaginationParams = Depends(),
    faculty_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DepartmentController.list_departments(
        db, tenant, params, faculty_id=faculty_id, search=search, is_active=is_active
    )


@departments_router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DepartmentController.get_department(db, tenant, department_id)


@departments_router.patch("/{department_id}", response_model=DepartmentRead)
@departments_router.put("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentController.update_department(db, tenant, department_id, data)


@departments_router.delete("/{department_id}", status_code=status.HTTP_200_OK)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentController.delete_department(db, tenant, department_id)


# --- DEPARTMENT LEADERSHIP ---
@leadership_router.post("", response_model=DepartmentLeadershipRead, status_code=status.HTTP_201_CREATED)
def appoint_leadership(
    data: DepartmentLeadershipCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentLeadershipController.appoint_leadership(db, tenant, data)


@leadership_router.get("", response_model=PaginatedResponse[DepartmentLeadershipRead])
def list_leadership(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DepartmentLeadershipController.list_leadership(
        db, tenant, params, department_id=department_id, active_only=active_only
    )


@leadership_router.get("/{leadership_id}", response_model=DepartmentLeadershipRead)
def get_leadership(
    leadership_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DepartmentLeadershipController.get_leadership(db, tenant, leadership_id)


@leadership_router.post("/{leadership_id}/end", response_model=DepartmentLeadershipRead)
def end_leadership(
    leadership_id: uuid.UUID,
    data: DepartmentLeadershipEnd,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentLeadershipController.end_leadership(db, tenant, leadership_id, data)


@leadership_router.delete("/{leadership_id}", status_code=status.HTTP_200_OK)
def delete_leadership(
    leadership_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("department_head", "university_admin")),
):
    return DepartmentLeadershipController.delete_leadership(db, tenant, leadership_id)


# --- STAFF PROFILES ---
@staff_router.post("", response_model=StaffProfileRead, status_code=status.HTTP_201_CREATED)
def create_staff_profile(
    data: StaffProfileCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StaffProfileController.create_profile(db, tenant, data)


@staff_router.get("", response_model=PaginatedResponse[StaffProfileRead])
def list_staff_profiles(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StaffProfileController.list_profiles(
        db, tenant, params, department_id=department_id, search=search
    )


@staff_router.get("/{profile_id}", response_model=StaffProfileRead)
def get_staff_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StaffProfileController.get_profile(db, tenant, profile_id)


@staff_router.patch("/{profile_id}", response_model=StaffProfileRead)
@staff_router.put("/{profile_id}", response_model=StaffProfileRead)
def update_staff_profile(
    profile_id: int,
    data: StaffProfileUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StaffProfileController.update_profile(db, tenant, profile_id, data)


@staff_router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
def delete_staff_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StaffProfileController.delete_profile(db, tenant, profile_id)


# --- STUDENT PROFILES ---
@students_router.post("", response_model=StudentProfileRead, status_code=status.HTTP_201_CREATED)
def create_student_profile(
    data: StudentProfileCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentProfileController.create_profile(db, tenant, data)


@students_router.get("", response_model=PaginatedResponse[StudentProfileRead])
def list_student_profiles(
    params: PaginationParams = Depends(),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentProfileController.list_profiles(
        db, tenant, params, department_id=department_id, search=search, status=status
    )


@students_router.get("/{profile_id}", response_model=StudentProfileRead)
def get_student_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentProfileController.get_profile(db, tenant, profile_id)


@students_router.patch("/{profile_id}", response_model=StudentProfileRead)
@students_router.put("/{profile_id}", response_model=StudentProfileRead)
def update_student_profile(
    profile_id: int,
    data: StudentProfileUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentProfileController.update_profile(db, tenant, profile_id, data)


@students_router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
def delete_student_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentProfileController.delete_profile(db, tenant, profile_id)

