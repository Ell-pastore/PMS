"""Controllers for faculties, departments, leadership, and profiles."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
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
from ..services.organization import (
    DepartmentLeadershipService,
    DepartmentService,
    FacultyService,
    StaffProfileService,
    StudentProfileService,
)


class FacultyController:
    @staticmethod
    def create_faculty(db: Session, tenant: TenantContext, data: FacultyCreate) -> FacultyRead:
        faculty = FacultyService.create_faculty(db, tenant.university_id, data)
        return FacultyRead.model_validate(faculty)

    @staticmethod
    def get_faculty(db: Session, tenant: TenantContext, faculty_id: int) -> FacultyRead:
        faculty = FacultyService.get_faculty(db, tenant.university_id, faculty_id)
        return FacultyRead.model_validate(faculty)

    @staticmethod
    def list_faculties(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[FacultyRead]:
        items, total, total_pages = FacultyService.list_faculties(
            db, tenant.university_id, params, search=search, is_active=is_active
        )
        return PaginatedResponse(
            items=[FacultyRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_faculty(
        db: Session,
        tenant: TenantContext,
        faculty_id: int,
        data: FacultyUpdate,
    ) -> FacultyRead:
        faculty = FacultyService.update_faculty(db, tenant.university_id, faculty_id, data)
        return FacultyRead.model_validate(faculty)

    @staticmethod
    def delete_faculty(db: Session, tenant: TenantContext, faculty_id: int) -> dict[str, str]:
        FacultyService.delete_faculty(db, tenant.university_id, faculty_id)
        return {"status": "success", "message": f"Faculty {faculty_id} deleted"}


class DepartmentController:
    @staticmethod
    def create_department(db: Session, tenant: TenantContext, data: DepartmentCreate) -> DepartmentRead:
        dept = DepartmentService.create_department(db, tenant.university_id, data)
        return DepartmentRead.model_validate(dept)

    @staticmethod
    def get_department(db: Session, tenant: TenantContext, department_id: int) -> DepartmentRead:
        dept = DepartmentService.get_department(db, tenant.university_id, department_id)
        return DepartmentRead.model_validate(dept)

    @staticmethod
    def list_departments(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        faculty_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[DepartmentRead]:
        items, total, total_pages = DepartmentService.list_departments(
            db, tenant.university_id, params, faculty_id=faculty_id, search=search, is_active=is_active
        )
        return PaginatedResponse(
            items=[DepartmentRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_department(
        db: Session,
        tenant: TenantContext,
        department_id: int,
        data: DepartmentUpdate,
    ) -> DepartmentRead:
        dept = DepartmentService.update_department(db, tenant.university_id, department_id, data)
        return DepartmentRead.model_validate(dept)

    @staticmethod
    def delete_department(db: Session, tenant: TenantContext, department_id: int) -> dict[str, str]:
        DepartmentService.delete_department(db, tenant.university_id, department_id)
        return {"status": "success", "message": f"Department {department_id} deleted"}


class DepartmentLeadershipController:
    @staticmethod
    def appoint_leadership(
        db: Session,
        tenant: TenantContext,
        data: DepartmentLeadershipCreate,
    ) -> DepartmentLeadershipRead:
        leadership = DepartmentLeadershipService.appoint_leadership(
            db, tenant.university_id, data, tenant.user.id
        )
        return DepartmentLeadershipRead.model_validate(leadership)

    @staticmethod
    def end_leadership(
        db: Session,
        tenant: TenantContext,
        leadership_id: uuid.UUID,
        data: DepartmentLeadershipEnd,
    ) -> DepartmentLeadershipRead:
        leadership = DepartmentLeadershipService.end_leadership(
            db, tenant.university_id, leadership_id, data
        )
        return DepartmentLeadershipRead.model_validate(leadership)

    @staticmethod
    def get_leadership(
        db: Session,
        tenant: TenantContext,
        leadership_id: uuid.UUID,
    ) -> DepartmentLeadershipRead:
        leadership = DepartmentLeadershipService.get_leadership(db, tenant.university_id, leadership_id)
        return DepartmentLeadershipRead.model_validate(leadership)

    @staticmethod
    def list_leadership(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        active_only: bool = True,
    ) -> PaginatedResponse[DepartmentLeadershipRead]:
        items, total, total_pages = DepartmentLeadershipService.list_leadership(
            db, tenant.university_id, params, department_id=department_id, active_only=active_only
        )
        return PaginatedResponse(
            items=[DepartmentLeadershipRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_leadership(
        db: Session,
        tenant: TenantContext,
        leadership_id: uuid.UUID,
    ) -> dict[str, str]:
        DepartmentLeadershipService.delete_leadership(db, tenant.university_id, leadership_id)
        return {"status": "success", "message": f"Department leadership {leadership_id} deleted"}


class StaffProfileController:
    @staticmethod
    def create_profile(db: Session, tenant: TenantContext, data: StaffProfileCreate) -> StaffProfileRead:
        profile = StaffProfileService.create_profile(db, tenant.university_id, data)
        return StaffProfileRead.model_validate(profile)

    @staticmethod
    def get_profile(db: Session, tenant: TenantContext, profile_id: int) -> StaffProfileRead:
        profile = StaffProfileService.get_profile(db, tenant.university_id, profile_id)
        return StaffProfileRead.model_validate(profile)

    @staticmethod
    def list_profiles(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[StaffProfileRead]:
        items, total, total_pages = StaffProfileService.list_profiles(
            db, tenant.university_id, params, department_id=department_id, search=search
        )
        return PaginatedResponse(
            items=[StaffProfileRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_profile(
        db: Session,
        tenant: TenantContext,
        profile_id: int,
        data: StaffProfileUpdate,
    ) -> StaffProfileRead:
        profile = StaffProfileService.update_profile(db, tenant.university_id, profile_id, data)
        return StaffProfileRead.model_validate(profile)

    @staticmethod
    def delete_profile(db: Session, tenant: TenantContext, profile_id: int) -> dict[str, str]:
        StaffProfileService.delete_profile(db, tenant.university_id, profile_id)
        return {"status": "success", "message": f"Staff profile {profile_id} deleted"}


class StudentProfileController:
    @staticmethod
    def create_profile(db: Session, tenant: TenantContext, data: StudentProfileCreate) -> StudentProfileRead:
        profile = StudentProfileService.create_profile(db, tenant.university_id, data)
        return StudentProfileRead.model_validate(profile)

    @staticmethod
    def get_profile(db: Session, tenant: TenantContext, profile_id: int) -> StudentProfileRead:
        profile = StudentProfileService.get_profile(db, tenant.university_id, profile_id)
        return StudentProfileRead.model_validate(profile)

    @staticmethod
    def list_profiles(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[StudentProfileRead]:
        items, total, total_pages = StudentProfileService.list_profiles(
            db, tenant.university_id, params, department_id=department_id, search=search, status=status
        )
        return PaginatedResponse(
            items=[StudentProfileRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_profile(
        db: Session,
        tenant: TenantContext,
        profile_id: int,
        data: StudentProfileUpdate,
    ) -> StudentProfileRead:
        profile = StudentProfileService.update_profile(db, tenant.university_id, profile_id, data)
        return StudentProfileRead.model_validate(profile)

    @staticmethod
    def delete_profile(db: Session, tenant: TenantContext, profile_id: int) -> dict[str, str]:
        StudentProfileService.delete_profile(db, tenant.university_id, profile_id)
        return {"status": "success", "message": f"Student profile {profile_id} deleted"}

