"""Service layer for universities, tenant memberships, and settings."""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import func, or_, select
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
    DepartmentSettings,
    Faculty,
    StaffProfile,
    StudentProfile,
    SystemSetting,
    University,
    UniversityMembership,
    UniversitySettings,
    User,
    UserRole,
)
from ..schemas.universities import (
    DepartmentSettingsCreate,
    DepartmentSettingsUpdate,
    SystemSettingCreate,
    SystemSettingUpdate,
    UniversityCreate,
    UniversityMembershipCreate,
    UniversityMembershipUpdate,
    UniversitySettingsCreate,
    UniversitySettingsUpdate,
    UniversityUpdate,
)


class UniversityService:
    @staticmethod
    def create_university(db: Session, data: UniversityCreate) -> University:
        existing = db.scalar(select(University).where(University.code == data.code.strip()))
        if existing:
            raise DuplicateResourceError(f"University with code '{data.code}' already exists")
        university = University(
            name=data.name.strip(),
            code=data.code.strip(),
            is_active=data.is_active,
        )
        db.add(university)
        db.commit()
        db.refresh(university)
        return university

    @staticmethod
    def get_university(db: Session, university_id: uuid.UUID) -> University:
        university = db.scalar(select(University).where(University.id == university_id))
        if not university:
            raise NotFoundError(f"University {university_id} not found")
        return university

    @staticmethod
    def list_universities(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[University], int, int]:
        query = select(University).order_by(University.created_at.desc())
        if is_active is not None:
            query = query.where(University.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(University.name.ilike(s), University.code.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_university(db: Session, university_id: uuid.UUID, data: UniversityUpdate) -> University:
        university = UniversityService.get_university(db, university_id)
        if data.code is not None and data.code.strip() != university.code:
            existing = db.scalar(select(University).where(University.code == data.code.strip()))
            if existing:
                raise DuplicateResourceError(f"University with code '{data.code}' already exists")
            university.code = data.code.strip()
        if data.name is not None:
            university.name = data.name.strip()
        if data.is_active is not None:
            university.is_active = data.is_active
        db.commit()
        db.refresh(university)
        return university

    @staticmethod
    def delete_university(db: Session, university_id: uuid.UUID) -> None:
        university = UniversityService.get_university(db, university_id)

        # Guard against deleting a university that still holds tenant data
        # (RESTRICT foreign keys would otherwise surface as a raw integrity
        # error). Domain records referencing the university keep it retained.
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(UniversityMembership).where(UniversityMembership.university_id == university.id)):
            blockers.append("members")
        if db.scalar(select(func.count()).select_from(Faculty).where(Faculty.university_id == university.id)):
            blockers.append("faculties")
        if db.scalar(select(func.count()).select_from(Department).where(Department.university_id == university.id)):
            blockers.append("departments")
        if db.scalar(select(func.count()).select_from(UniversitySettings).where(UniversitySettings.university_id == university.id)):
            blockers.append("settings")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete university with existing {', '.join(blockers)}. Remove them first."
            )
        db.delete(university)
        db.commit()


class UniversityMembershipService:
    @staticmethod
    def add_membership(
        db: Session,
        university_id: uuid.UUID,
        data: UniversityMembershipCreate,
    ) -> UniversityMembership:
        UniversityService.get_university(db, university_id)
        user = db.scalar(select(User).where(User.id == data.user_id))
        if not user:
            raise ForeignKeyViolationError(f"User {data.user_id} not found")

        existing = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.user_id,
            )
        )
        if existing:
            raise DuplicateResourceError(f"User {data.user_id} is already a member of this university")

        membership = UniversityMembership(
            university_id=university_id,
            user_id=data.user_id,
            is_active=data.is_active,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    @staticmethod
    def get_membership(db: Session, university_id: uuid.UUID, membership_id: uuid.UUID) -> UniversityMembership:
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.id == membership_id,
                UniversityMembership.university_id == university_id,
            )
        )
        if not membership:
            raise NotFoundError(f"University membership {membership_id} not found in this university")
        return membership

    @staticmethod
    def list_memberships(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[UniversityMembership], int, int]:
        query = select(UniversityMembership).where(UniversityMembership.university_id == university_id).order_by(UniversityMembership.created_at.desc())
        if user_id:
            query = query.where(UniversityMembership.user_id == user_id)
        if is_active is not None:
            query = query.where(UniversityMembership.is_active == is_active)
        return paginate(query, db, params)

    @staticmethod
    def update_membership(
        db: Session,
        university_id: uuid.UUID,
        membership_id: uuid.UUID,
        data: UniversityMembershipUpdate,
    ) -> UniversityMembership:
        membership = UniversityMembershipService.get_membership(db, university_id, membership_id)
        membership.is_active = data.is_active
        db.commit()
        db.refresh(membership)
        return membership

    @staticmethod
    def delete_membership(db: Session, university_id: uuid.UUID, membership_id: uuid.UUID) -> None:
        membership = UniversityMembershipService.get_membership(db, university_id, membership_id)

        # Guard against deleting a membership that still holds user data
        # (RESTRICT composite foreign keys would otherwise surface as a raw
        # integrity error). Historical records keep the membership retained.
        blockers: list[str] = []
        if db.scalar(
            select(func.count()).select_from(UserRole).where(
                UserRole.user_id == membership.user_id,
                UserRole.university_id == membership.university_id,
            )
        ):
            blockers.append("role assignments")
        if db.scalar(
            select(func.count()).select_from(StaffProfile).where(
                StaffProfile.user_id == membership.user_id,
                StaffProfile.university_id == membership.university_id,
            )
        ):
            blockers.append("staff profiles")
        if db.scalar(
            select(func.count()).select_from(StudentProfile).where(
                StudentProfile.user_id == membership.user_id,
                StudentProfile.university_id == membership.university_id,
            )
        ):
            blockers.append("student profiles")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete membership with existing {', '.join(blockers)}. Remove them first."
            )
        db.delete(membership)
        db.commit()


class SettingsService:
    @staticmethod
    def get_university_settings(db: Session, university_id: uuid.UUID) -> UniversitySettings:
        settings = db.scalar(select(UniversitySettings).where(UniversitySettings.university_id == university_id))
        if not settings:
            # Create default settings if not exists
            settings = UniversitySettings(university_id=university_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def upsert_university_settings(
        db: Session,
        university_id: uuid.UUID,
        data: UniversitySettingsUpdate,
        user_id: int,
    ) -> UniversitySettings:
        settings = db.scalar(select(UniversitySettings).where(UniversitySettings.university_id == university_id))
        if not settings:
            settings = UniversitySettings(university_id=university_id)
            db.add(settings)

        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, val)
        settings.updated_by_id = user_id

        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def get_department_settings(
        db: Session,
        university_id: uuid.UUID,
        department_id: int,
    ) -> DepartmentSettings:
        dept = db.scalar(
            select(Department).where(
                Department.id == department_id,
                Department.university_id == university_id,
            )
        )
        if not dept:
            raise NotFoundError(f"Department {department_id} not found in this university")

        settings = db.scalar(
            select(DepartmentSettings).where(
                DepartmentSettings.department_id == department_id,
                DepartmentSettings.university_id == university_id,
            )
        )
        if not settings:
            raise NotFoundError(f"No specific settings configured for department {department_id}")
        return settings

    @staticmethod
    def upsert_department_settings(
        db: Session,
        university_id: uuid.UUID,
        department_id: int,
        data: DepartmentSettingsUpdate,
        user_id: int,
    ) -> DepartmentSettings:
        dept = db.scalar(
            select(Department).where(
                Department.id == department_id,
                Department.university_id == university_id,
            )
        )
        if not dept:
            raise NotFoundError(f"Department {department_id} not found in this university")

        settings = db.scalar(
            select(DepartmentSettings).where(
                DepartmentSettings.department_id == department_id,
                DepartmentSettings.university_id == university_id,
            )
        )
        if not settings:
            settings = DepartmentSettings(
                university_id=university_id,
                department_id=department_id,
            )
            db.add(settings)

        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, val)
        settings.updated_by_id = user_id

        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def create_system_setting(
        db: Session,
        university_id: uuid.UUID,
        data: SystemSettingCreate,
        user_id: int,
    ) -> SystemSetting:
        existing = db.scalar(
            select(SystemSetting).where(
                SystemSetting.university_id == university_id,
                SystemSetting.setting_key == data.setting_key,
            )
        )
        if existing:
            raise DuplicateResourceError(f"System setting '{data.setting_key}' already exists for this university")

        setting = SystemSetting(
            university_id=university_id,
            setting_key=data.setting_key,
            setting_value=data.setting_value,
            updated_by_id=user_id,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def get_system_setting(
        db: Session,
        university_id: uuid.UUID,
        setting_key: str,
    ) -> SystemSetting:
        setting = db.scalar(
            select(SystemSetting).where(
                SystemSetting.university_id == university_id,
                SystemSetting.setting_key == setting_key,
            )
        )
        if not setting:
            raise NotFoundError(f"Setting '{setting_key}' not found in this university")
        return setting

    @staticmethod
    def list_system_settings(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        search: Optional[str] = None,
    ) -> tuple[Sequence[SystemSetting], int, int]:
        query = select(SystemSetting).where(SystemSetting.university_id == university_id).order_by(SystemSetting.setting_key.asc())
        if search:
            query = query.where(SystemSetting.setting_key.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_system_setting(
        db: Session,
        university_id: uuid.UUID,
        setting_key: str,
        data: SystemSettingUpdate,
        user_id: int,
    ) -> SystemSetting:
        setting = SettingsService.get_system_setting(db, university_id, setting_key)
        setting.setting_value = data.setting_value
        setting.updated_by_id = user_id
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def delete_system_setting(
        db: Session,
        university_id: uuid.UUID,
        setting_key: str,
    ) -> None:
        setting = SettingsService.get_system_setting(db, university_id, setting_key)
        db.delete(setting)
        db.commit()

