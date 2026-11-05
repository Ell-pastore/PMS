"""Service layer for faculties, departments, leadership, and profiles."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForeignKeyViolationError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    Department,
    DepartmentLeadership,
    Faculty,
    ResearchProposal,
    ResearchProject,
    StaffProfile,
    StudentProfile,
    UniversityMembership,
)
from ..schemas.organization import (
    DepartmentCreate,
    DepartmentLeadershipCreate,
    DepartmentLeadershipEnd,
    DepartmentUpdate,
    FacultyCreate,
    FacultyUpdate,
    StaffProfileCreate,
    StaffProfileUpdate,
    StudentProfileCreate,
    StudentProfileUpdate,
)


class FacultyService:
    @staticmethod
    def create_faculty(db: Session, university_id: uuid.UUID, data: FacultyCreate) -> Faculty:
        existing = db.scalar(
            select(Faculty).where(
                Faculty.university_id == university_id,
                Faculty.code == data.code.strip(),
            )
        )
        if existing:
            raise DuplicateResourceError(f"Faculty with code '{data.code}' already exists in this university")

        faculty = Faculty(
            university_id=university_id,
            name=data.name.strip(),
            code=data.code.strip(),
            description=data.description,
            is_active=data.is_active,
        )
        db.add(faculty)
        db.commit()
        db.refresh(faculty)
        return faculty

    @staticmethod
    def get_faculty(db: Session, university_id: uuid.UUID, faculty_id: int) -> Faculty:
        faculty = db.scalar(
            select(Faculty).where(
                Faculty.id == faculty_id,
                Faculty.university_id == university_id,
            )
        )
        if not faculty:
            raise NotFoundError(f"Faculty {faculty_id} not found in this university")
        return faculty

    @staticmethod
    def list_faculties(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[Faculty], int, int]:
        query = select(Faculty).where(Faculty.university_id == university_id).order_by(Faculty.id.asc())
        if is_active is not None:
            query = query.where(Faculty.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Faculty.name.ilike(s), Faculty.code.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_faculty(
        db: Session,
        university_id: uuid.UUID,
        faculty_id: int,
        data: FacultyUpdate,
    ) -> Faculty:
        faculty = FacultyService.get_faculty(db, university_id, faculty_id)
        if data.code is not None and data.code.strip() != faculty.code:
            existing = db.scalar(
                select(Faculty).where(
                    Faculty.university_id == university_id,
                    Faculty.code == data.code.strip(),
                )
            )
            if existing:
                raise DuplicateResourceError(f"Faculty with code '{data.code}' already exists in this university")
            faculty.code = data.code.strip()
        if data.name is not None:
            faculty.name = data.name.strip()
        if data.description is not None:
            faculty.description = data.description
        if data.is_active is not None:
            faculty.is_active = data.is_active

        db.commit()
        db.refresh(faculty)
        return faculty

    @staticmethod
    def delete_faculty(db: Session, university_id: uuid.UUID, faculty_id: int) -> None:
        faculty = FacultyService.get_faculty(db, university_id, faculty_id)
        referenced = db.scalar(
            select(Department.id).where(Department.faculty_id == faculty_id).limit(1)
        )
        if referenced:
            raise SpecializedOperationError(
                "Cannot delete faculty: departments belong to it. "
                "Delete or move the departments first."
            )
        db.delete(faculty)
        db.commit()


class DepartmentService:
    @staticmethod
    def create_department(db: Session, university_id: uuid.UUID, data: DepartmentCreate) -> Department:
        # Validate faculty exists in this university
        FacultyService.get_faculty(db, university_id, data.faculty_id)

        # Check unique constraints within faculty
        existing = db.scalar(
            select(Department).where(
                Department.university_id == university_id,
                Department.faculty_id == data.faculty_id,
                or_(Department.name == data.name.strip(), Department.code == data.code.strip()),
            )
        )
        if existing:
            raise DuplicateResourceError("Department with same name or code already exists in this faculty")

        dept = Department(
            university_id=university_id,
            faculty_id=data.faculty_id,
            name=data.name.strip(),
            code=data.code.strip(),
            description=data.description,
            is_active=data.is_active,
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def get_department(db: Session, university_id: uuid.UUID, department_id: int) -> Department:
        dept = db.scalar(
            select(Department).where(
                Department.id == department_id,
                Department.university_id == university_id,
            )
        )
        if not dept:
            raise NotFoundError(f"Department {department_id} not found in this university")
        return dept

    @staticmethod
    def list_departments(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        faculty_id: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[Department], int, int]:
        query = select(Department).where(Department.university_id == university_id).order_by(Department.id.asc())
        if faculty_id:
            query = query.where(Department.faculty_id == faculty_id)
        if is_active is not None:
            query = query.where(Department.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Department.name.ilike(s), Department.code.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_department(
        db: Session,
        university_id: uuid.UUID,
        department_id: int,
        data: DepartmentUpdate,
    ) -> Department:
        dept = DepartmentService.get_department(db, university_id, department_id)
        target_faculty = data.faculty_id if data.faculty_id is not None else dept.faculty_id
        if data.faculty_id is not None and data.faculty_id != dept.faculty_id:
            FacultyService.get_faculty(db, university_id, data.faculty_id)
            dept.faculty_id = data.faculty_id

        target_name = data.name.strip() if data.name is not None else dept.name
        target_code = data.code.strip() if data.code is not None else dept.code

        if target_name != dept.name or target_code != dept.code or data.faculty_id is not None:
            existing = db.scalar(
                select(Department).where(
                    Department.university_id == university_id,
                    Department.faculty_id == target_faculty,
                    Department.id != dept.id,
                    or_(Department.name == target_name, Department.code == target_code),
                )
            )
            if existing:
                raise DuplicateResourceError("Department with same name or code already exists in target faculty")

        if data.name is not None:
            dept.name = data.name.strip()
        if data.code is not None:
            dept.code = data.code.strip()
        if data.description is not None:
            dept.description = data.description
        if data.is_active is not None:
            dept.is_active = data.is_active

        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def delete_department(db: Session, university_id: uuid.UUID, department_id: int) -> None:
        dept = DepartmentService.get_department(db, university_id, department_id)
        checks = [
            (select(ResearchProposal.id).where(ResearchProposal.department_id == department_id).limit(1), "research proposals"),
            (select(ResearchProject.id).where(ResearchProject.department_id == department_id).limit(1), "research projects"),
            (select(StaffProfile.id).where(StaffProfile.department_id == department_id).limit(1), "staff profiles"),
            (select(StudentProfile.id).where(StudentProfile.department_id == department_id).limit(1), "student profiles"),
            (select(DepartmentLeadership.id).where(DepartmentLeadership.department_id == department_id).limit(1), "department leadership assignments"),
        ]
        for stmt, desc in checks:
            if db.scalar(stmt):
                raise SpecializedOperationError(
                    f"Cannot delete department {department_id}: it is still referenced by {desc}. "
                    "Delete or reassign those records first."
                )
        db.delete(dept)
        db.commit()


class DepartmentLeadershipService:
    @staticmethod
    def appoint_leadership(
        db: Session,
        university_id: uuid.UUID,
        data: DepartmentLeadershipCreate,
        appointed_by_id: int,
    ) -> DepartmentLeadership:
        DepartmentService.get_department(db, university_id, data.department_id)

        # Validate staff profile belongs to this department and university
        staff = db.scalar(
            select(StaffProfile).where(
                StaffProfile.id == data.staff_id,
                StaffProfile.department_id == data.department_id,
                StaffProfile.university_id == university_id,
            )
        )
        if not staff:
            raise ForeignKeyViolationError(
                f"Staff {data.staff_id} does not belong to department {data.department_id} in this university"
            )

        # End any currently active leadership for this department
        now = datetime.now(timezone.utc)
        active_leaders = db.scalars(
            select(DepartmentLeadership).where(
                DepartmentLeadership.university_id == university_id,
                DepartmentLeadership.department_id == data.department_id,
                DepartmentLeadership.ended_at.is_(None),
            )
        ).all()
        for leader in active_leaders:
            leader.ended_at = now

        leadership = DepartmentLeadership(
            university_id=university_id,
            department_id=data.department_id,
            staff_id=data.staff_id,
            appointed_by_id=appointed_by_id,
            started_at=data.started_at or now,
        )
        db.add(leadership)
        db.commit()
        db.refresh(leadership)
        return leadership

    @staticmethod
    def end_leadership(
        db: Session,
        university_id: uuid.UUID,
        leadership_id: uuid.UUID,
        data: DepartmentLeadershipEnd,
    ) -> DepartmentLeadership:
        leadership = db.scalar(
            select(DepartmentLeadership).where(
                DepartmentLeadership.id == leadership_id,
                DepartmentLeadership.university_id == university_id,
            )
        )
        if not leadership:
            raise NotFoundError(f"Department leadership {leadership_id} not found in this university")

        leadership.ended_at = data.ended_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(leadership)
        return leadership

    @staticmethod
    def get_leadership(
        db: Session,
        university_id: uuid.UUID,
        leadership_id: uuid.UUID,
    ) -> DepartmentLeadership:
        leadership = db.scalar(
            select(DepartmentLeadership).where(
                DepartmentLeadership.id == leadership_id,
                DepartmentLeadership.university_id == university_id,
            )
        )
        if not leadership:
            raise NotFoundError(f"Department leadership {leadership_id} not found in this university")
        return leadership

    @staticmethod
    def list_leadership(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        active_only: bool = True,
    ) -> tuple[Sequence[DepartmentLeadership], int, int]:
        query = select(DepartmentLeadership).where(DepartmentLeadership.university_id == university_id).order_by(DepartmentLeadership.started_at.desc())
        if department_id:
            query = query.where(DepartmentLeadership.department_id == department_id)
        if active_only:
            query = query.where(DepartmentLeadership.ended_at.is_(None))
        return paginate(query, db, params)

    @staticmethod
    def delete_leadership(
        db: Session,
        university_id: uuid.UUID,
        leadership_id: uuid.UUID,
    ) -> None:
        leadership = DepartmentLeadershipService.get_leadership(db, university_id, leadership_id)
        db.delete(leadership)
        db.commit()


class StaffProfileService:
    @staticmethod
    def create_profile(db: Session, university_id: uuid.UUID, data: StaffProfileCreate) -> StaffProfile:
        # Validate user membership
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {data.user_id} has no membership in this university")

        # Validate department
        DepartmentService.get_department(db, university_id, data.department_id)

        # Check unique constraints
        existing_user = db.scalar(
            select(StaffProfile).where(
                StaffProfile.university_id == university_id,
                StaffProfile.user_id == data.user_id,
            )
        )
        if existing_user:
            raise DuplicateResourceError(f"Staff profile already exists for user {data.user_id} in this university")

        existing_staff_id = db.scalar(
            select(StaffProfile).where(
                StaffProfile.university_id == university_id,
                StaffProfile.staff_id == data.staff_id.strip(),
            )
        )
        if existing_staff_id:
            raise DuplicateResourceError(f"Staff ID '{data.staff_id}' already assigned in this university")

        profile = StaffProfile(
            university_id=university_id,
            user_id=data.user_id,
            staff_id=data.staff_id.strip(),
            department_id=data.department_id,
            job_title=data.job_title,
            academic_designation=data.academic_designation,
            gender=data.gender,
            phone_number=data.phone_number,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_profile(db: Session, university_id: uuid.UUID, profile_id: int) -> StaffProfile:
        profile = db.scalar(
            select(StaffProfile).where(
                StaffProfile.id == profile_id,
                StaffProfile.university_id == university_id,
            )
        )
        if not profile:
            raise NotFoundError(f"Staff profile {profile_id} not found in this university")
        return profile

    @staticmethod
    def list_profiles(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[StaffProfile], int, int]:
        query = select(StaffProfile).where(StaffProfile.university_id == university_id).order_by(StaffProfile.id.desc())
        if department_id:
            query = query.where(StaffProfile.department_id == department_id)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(StaffProfile.staff_id.ilike(s), StaffProfile.job_title.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_profile(
        db: Session,
        university_id: uuid.UUID,
        profile_id: int,
        data: StaffProfileUpdate,
    ) -> StaffProfile:
        profile = StaffProfileService.get_profile(db, university_id, profile_id)
        if data.department_id is not None and data.department_id != profile.department_id:
            DepartmentService.get_department(db, university_id, data.department_id)
            profile.department_id = data.department_id
        if data.staff_id is not None and data.staff_id.strip() != profile.staff_id:
            existing = db.scalar(
                select(StaffProfile).where(
                    StaffProfile.university_id == university_id,
                    StaffProfile.staff_id == data.staff_id.strip(),
                    StaffProfile.id != profile.id,
                )
            )
            if existing:
                raise DuplicateResourceError(f"Staff ID '{data.staff_id}' already assigned in this university")
            profile.staff_id = data.staff_id.strip()
        if data.job_title is not None:
            profile.job_title = data.job_title
        if data.academic_designation is not None:
            profile.academic_designation = data.academic_designation
        if data.gender is not None:
            profile.gender = data.gender
        if data.phone_number is not None:
            profile.phone_number = data.phone_number

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete_profile(db: Session, university_id: uuid.UUID, profile_id: int) -> None:
        profile = StaffProfileService.get_profile(db, university_id, profile_id)
        db.delete(profile)
        db.commit()


class StudentProfileService:
    @staticmethod
    def create_profile(db: Session, university_id: uuid.UUID, data: StudentProfileCreate) -> StudentProfile:
        # Validate user membership
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {data.user_id} has no membership in this university")

        # Validate department
        DepartmentService.get_department(db, university_id, data.department_id)

        # Check unique constraints
        existing_user = db.scalar(
            select(StudentProfile).where(
                StudentProfile.university_id == university_id,
                StudentProfile.user_id == data.user_id,
            )
        )
        if existing_user:
            raise DuplicateResourceError(f"Student profile already exists for user {data.user_id} in this university")

        existing_student_id = db.scalar(
            select(StudentProfile).where(
                StudentProfile.university_id == university_id,
                StudentProfile.student_id == data.student_id.strip(),
            )
        )
        if existing_student_id:
            raise DuplicateResourceError(f"Student ID '{data.student_id}' already assigned in this university")

        profile = StudentProfile(
            university_id=university_id,
            user_id=data.user_id,
            student_id=data.student_id.strip(),
            department_id=data.department_id,
            academic_level=data.academic_level,
            gender=data.gender,
            enrollment_date=data.enrollment_date,
            academic_account_status=data.academic_account_status,
            phone_number=data.phone_number,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_profile(db: Session, university_id: uuid.UUID, profile_id: int) -> StudentProfile:
        profile = db.scalar(
            select(StudentProfile).where(
                StudentProfile.id == profile_id,
                StudentProfile.university_id == university_id,
            )
        )
        if not profile:
            raise NotFoundError(f"Student profile {profile_id} not found in this university")
        return profile

    @staticmethod
    def list_profiles(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[Sequence[StudentProfile], int, int]:
        query = select(StudentProfile).where(StudentProfile.university_id == university_id).order_by(StudentProfile.id.desc())
        if department_id:
            query = query.where(StudentProfile.department_id == department_id)
        if status:
            query = query.where(StudentProfile.academic_account_status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(StudentProfile.student_id.ilike(s), StudentProfile.academic_level.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_profile(
        db: Session,
        university_id: uuid.UUID,
        profile_id: int,
        data: StudentProfileUpdate,
    ) -> StudentProfile:
        profile = StudentProfileService.get_profile(db, university_id, profile_id)
        if data.department_id is not None and data.department_id != profile.department_id:
            DepartmentService.get_department(db, university_id, data.department_id)
            profile.department_id = data.department_id
        if data.student_id is not None and data.student_id.strip() != profile.student_id:
            existing = db.scalar(
                select(StudentProfile).where(
                    StudentProfile.university_id == university_id,
                    StudentProfile.student_id == data.student_id.strip(),
                    StudentProfile.id != profile.id,
                )
            )
            if existing:
                raise DuplicateResourceError(f"Student ID '{data.student_id}' already assigned in this university")
            profile.student_id = data.student_id.strip()
        if data.academic_level is not None:
            profile.academic_level = data.academic_level
        if data.gender is not None:
            profile.gender = data.gender
        if data.enrollment_date is not None:
            profile.enrollment_date = data.enrollment_date
        if data.academic_account_status is not None:
            profile.academic_account_status = data.academic_account_status
        if data.phone_number is not None:
            profile.phone_number = data.phone_number

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete_profile(db: Session, university_id: uuid.UUID, profile_id: int) -> None:
        profile = StudentProfileService.get_profile(db, university_id, profile_id)
        db.delete(profile)
        db.commit()

