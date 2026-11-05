"""FastAPI routes for universities, university memberships, and settings."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.universities import (
    SettingsController,
    UniversityController,
    UniversityMembershipController,
)
from ..core.dependencies import (
    TenantContext,
    get_current_user,
    get_db,
    get_tenant_context,
    require_roles,
)
from ..core.pagination import PaginatedResponse, PaginationParams
from ..models.User import User
from ..schemas.universities import (
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

universities_router = APIRouter(prefix="/universities", tags=["Universities"])
memberships_router = APIRouter(prefix="/university-memberships", tags=["University Memberships"])
settings_router = APIRouter(prefix="/settings", tags=["Settings"])


# --- UNIVERSITIES ---
@universities_router.post("", response_model=UniversityRead, status_code=status.HTTP_201_CREATED)
def create_university(
    data: UniversityCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UniversityController.create_university(db, data)


@universities_router.get("", response_model=PaginatedResponse[UniversityRead])
def list_universities(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search by name or code"),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UniversityController.list_universities(db, params, search=search, is_active=is_active)


@universities_router.get("/{university_id}", response_model=UniversityRead)
def get_university(
    university_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UniversityController.get_university(db, university_id)


@universities_router.patch("/{university_id}", response_model=UniversityRead)
@universities_router.put("/{university_id}", response_model=UniversityRead)
def update_university(
    university_id: uuid.UUID,
    data: UniversityUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UniversityController.update_university(db, university_id, data)


@universities_router.delete("/{university_id}", status_code=status.HTTP_200_OK)
def delete_university(
    university_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UniversityController.delete_university(db, university_id)


# --- UNIVERSITY MEMBERSHIPS ---
@memberships_router.post("", response_model=UniversityMembershipRead, status_code=status.HTTP_201_CREATED)
def add_membership(
    data: UniversityMembershipCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UniversityMembershipController.add_membership(db, tenant, data)


@memberships_router.get("", response_model=PaginatedResponse[UniversityMembershipRead])
def list_memberships(
    params: PaginationParams = Depends(),
    user_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UniversityMembershipController.list_memberships(
        db, tenant, params, user_id=user_id, is_active=is_active
    )


@memberships_router.get("/{membership_id}", response_model=UniversityMembershipRead)
def get_membership(
    membership_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UniversityMembershipController.get_membership(db, tenant, membership_id)


@memberships_router.patch("/{membership_id}", response_model=UniversityMembershipRead)
@memberships_router.put("/{membership_id}", response_model=UniversityMembershipRead)
def update_membership(
    membership_id: uuid.UUID,
    data: UniversityMembershipUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UniversityMembershipController.update_membership(db, tenant, membership_id, data)


@memberships_router.delete("/{membership_id}", status_code=status.HTTP_200_OK)
def delete_membership(
    membership_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UniversityMembershipController.delete_membership(db, tenant, membership_id)


# --- SETTINGS ---
@settings_router.get("/university", response_model=UniversitySettingsRead)
def get_university_settings(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.get_university_settings(db, tenant)


@settings_router.patch("/university", response_model=UniversitySettingsRead)
@settings_router.put("/university", response_model=UniversitySettingsRead)
def update_university_settings(
    data: UniversitySettingsUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.update_university_settings(db, tenant, data)


@settings_router.get("/departments/{department_id}", response_model=DepartmentSettingsRead)
def get_department_settings(
    department_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.get_department_settings(db, tenant, department_id)


@settings_router.patch("/departments/{department_id}", response_model=DepartmentSettingsRead)
@settings_router.put("/departments/{department_id}", response_model=DepartmentSettingsRead)
def update_department_settings(
    department_id: int,
    data: DepartmentSettingsUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.update_department_settings(db, tenant, department_id, data)


@settings_router.post("/system", response_model=SystemSettingRead, status_code=status.HTTP_201_CREATED)
def create_system_setting(
    data: SystemSettingCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.create_system_setting(db, tenant, data)


@settings_router.get("/system", response_model=PaginatedResponse[SystemSettingRead])
def list_system_settings(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.list_system_settings(db, tenant, params, search=search)


@settings_router.get("/system/{setting_key}", response_model=SystemSettingRead)
def get_system_setting(
    setting_key: str,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.get_system_setting(db, tenant, setting_key)


@settings_router.patch("/system/{setting_key}", response_model=SystemSettingRead)
@settings_router.put("/system/{setting_key}", response_model=SystemSettingRead)
def update_system_setting(
    setting_key: str,
    data: SystemSettingUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.update_system_setting(db, tenant, setting_key, data)


@settings_router.delete("/system/{setting_key}", status_code=status.HTTP_200_OK)
def delete_system_setting(
    setting_key: str,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return SettingsController.delete_system_setting(db, tenant, setting_key)

