"""Controllers for universities, tenant memberships, and settings."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.universities import (
    DepartmentSettingsCreate,
    DepartmentSettingsRead,
    DepartmentSettingsUpdate,
    SystemSettingCreate,
    SystemSettingRead,
    SystemSettingUpdate,
    UniversityCreate,
    UniversityMembershipCreate,
    UniversityMembershipRead,
    UniversityMembershipUpdate,
    UniversityRead,
    UniversitySettingsRead,
    UniversitySettingsUpdate,
    UniversityUpdate,
)
from ..services.universities import (
    SettingsService,
    UniversityMembershipService,
    UniversityService,
)


class UniversityController:
    @staticmethod
    def create_university(db: Session, data: UniversityCreate) -> UniversityRead:
        univ = UniversityService.create_university(db, data)
        return UniversityRead.model_validate(univ)

    @staticmethod
    def get_university(db: Session, university_id: uuid.UUID) -> UniversityRead:
        univ = UniversityService.get_university(db, university_id)
        return UniversityRead.model_validate(univ)

    @staticmethod
    def list_universities(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[UniversityRead]:
        items, total, total_pages = UniversityService.list_universities(db, params, search=search, is_active=is_active)
        return PaginatedResponse(
            items=[UniversityRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_university(db: Session, university_id: uuid.UUID, data: UniversityUpdate) -> UniversityRead:
        univ = UniversityService.update_university(db, university_id, data)
        return UniversityRead.model_validate(univ)

    @staticmethod
    def delete_university(db: Session, university_id: uuid.UUID) -> dict[str, str]:
        UniversityService.delete_university(db, university_id)
        return {"status": "success", "message": f"University {university_id} deleted"}


class UniversityMembershipController:
    @staticmethod
    def add_membership(
        db: Session,
        tenant: TenantContext,
        data: UniversityMembershipCreate,
    ) -> UniversityMembershipRead:
        membership = UniversityMembershipService.add_membership(db, tenant.university_id, data)
        return UniversityMembershipRead.model_validate(membership)

    @staticmethod
    def get_membership(
        db: Session,
        tenant: TenantContext,
        membership_id: uuid.UUID,
    ) -> UniversityMembershipRead:
        membership = UniversityMembershipService.get_membership(db, tenant.university_id, membership_id)
        return UniversityMembershipRead.model_validate(membership)

    @staticmethod
    def list_memberships(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        user_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[UniversityMembershipRead]:
        items, total, total_pages = UniversityMembershipService.list_memberships(
            db, tenant.university_id, params, user_id=user_id, is_active=is_active
        )
        return PaginatedResponse(
            items=[UniversityMembershipRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_membership(
        db: Session,
        tenant: TenantContext,
        membership_id: uuid.UUID,
        data: UniversityMembershipUpdate,
    ) -> UniversityMembershipRead:
        membership = UniversityMembershipService.update_membership(db, tenant.university_id, membership_id, data)
        return UniversityMembershipRead.model_validate(membership)

    @staticmethod
    def delete_membership(
        db: Session,
        tenant: TenantContext,
        membership_id: uuid.UUID,
    ) -> dict[str, str]:
        UniversityMembershipService.delete_membership(db, tenant.university_id, membership_id)
        return {"status": "success", "message": f"Membership {membership_id} deleted"}


class SettingsController:
    @staticmethod
    def get_university_settings(db: Session, tenant: TenantContext) -> UniversitySettingsRead:
        settings = SettingsService.get_university_settings(db, tenant.university_id)
        return UniversitySettingsRead.model_validate(settings)

    @staticmethod
    def update_university_settings(
        db: Session,
        tenant: TenantContext,
        data: UniversitySettingsUpdate,
    ) -> UniversitySettingsRead:
        settings = SettingsService.upsert_university_settings(db, tenant.university_id, data, tenant.user.id)
        return UniversitySettingsRead.model_validate(settings)

    @staticmethod
    def get_department_settings(
        db: Session,
        tenant: TenantContext,
        department_id: int,
    ) -> DepartmentSettingsRead:
        settings = SettingsService.get_department_settings(db, tenant.university_id, department_id)
        return DepartmentSettingsRead.model_validate(settings)

    @staticmethod
    def update_department_settings(
        db: Session,
        tenant: TenantContext,
        department_id: int,
        data: DepartmentSettingsUpdate,
    ) -> DepartmentSettingsRead:
        settings = SettingsService.upsert_department_settings(
            db, tenant.university_id, department_id, data, tenant.user.id
        )
        return DepartmentSettingsRead.model_validate(settings)

    @staticmethod
    def create_system_setting(
        db: Session,
        tenant: TenantContext,
        data: SystemSettingCreate,
    ) -> SystemSettingRead:
        setting = SettingsService.create_system_setting(db, tenant.university_id, data, tenant.user.id)
        return SystemSettingRead.model_validate(setting)

    @staticmethod
    def get_system_setting(
        db: Session,
        tenant: TenantContext,
        setting_key: str,
    ) -> SystemSettingRead:
        setting = SettingsService.get_system_setting(db, tenant.university_id, setting_key)
        return SystemSettingRead.model_validate(setting)

    @staticmethod
    def list_system_settings(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        search: Optional[str] = None,
    ) -> PaginatedResponse[SystemSettingRead]:
        items, total, total_pages = SettingsService.list_system_settings(
            db, tenant.university_id, params, search=search
        )
        return PaginatedResponse(
            items=[SystemSettingRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_system_setting(
        db: Session,
        tenant: TenantContext,
        setting_key: str,
        data: SystemSettingUpdate,
    ) -> SystemSettingRead:
        setting = SettingsService.update_system_setting(
            db, tenant.university_id, setting_key, data, tenant.user.id
        )
        return SystemSettingRead.model_validate(setting)

    @staticmethod
    def delete_system_setting(
        db: Session,
        tenant: TenantContext,
        setting_key: str,
    ) -> dict[str, str]:
        SettingsService.delete_system_setting(db, tenant.university_id, setting_key)
        return {"status": "success", "message": f"Setting '{setting_key}' deleted"}

