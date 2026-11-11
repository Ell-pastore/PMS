"""FastAPI routes for users, auth, roles, permissions, and tenant user-roles."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.users import (
    PermissionController,
    RoleController,
    UserController,
    UserRoleController,
)
from ..core.dependencies import (
    TenantContext,
    get_current_user,
    get_db,
    get_tenant_context,
    require_roles,
)
from ..core.exceptions import ForbiddenError
from ..core.pagination import PaginatedResponse, PaginationParams
from ..models.User import AccountStatus, User
from ..schemas.users import (
    LoginRequest,
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    RoleCreate,
    RolePermissionCreate,
    RolePermissionRead,
    RoleRead,
    RoleUpdate,
    TokenResponse,
    UserCreate,
    UserRead,
    UserRoleCreate,
    UserRoleRead,
    UserUpdate,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])
roles_router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])
user_roles_router = APIRouter(prefix="/user-roles", tags=["User Roles (Tenant)"])


# --- AUTH ENDPOINTS ---
@auth_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return UserController.register(db, data)


@auth_router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return UserController.login(db, data)


@auth_router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return UserController.get_me(current_user)


# --- USER CRUD & SEARCH ---
@users_router.get("", response_model=PaginatedResponse[UserRead])
def list_users(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search by name or email"),
    status: Optional[AccountStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UserController.list_users(db, params, search=search, status=status)


@users_router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
):
    # Self-access is always allowed; otherwise require university admin.
    if current_user.id != user_id and not tenant.has_role("university_admin"):
        raise ForbiddenError("Access to another user's profile requires university admin role")
    return UserController.get_user(db, user_id)


@users_router.put("/{user_id}", response_model=UserRead)
@users_router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
):
    if current_user.id != user_id and not tenant.has_role("university_admin"):
        raise ForbiddenError("Updating another user's profile requires university admin role")
    return UserController.update_user(db, user_id, data)


@users_router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UserController.delete_user(db, user_id)


# --- ROLES & PERMISSIONS ---
@roles_router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return RoleController.create_role(db, data)


@roles_router.get("", response_model=PaginatedResponse[RoleRead])
def list_roles(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return RoleController.list_roles(db, params, search=search, is_active=is_active)


# Permissions (declared before /{role_id} so the static path is not shadowed)
@roles_router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
def create_permission(
    data: PermissionCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return PermissionController.create_permission(db, data)


@roles_router.get("/permissions", response_model=PaginatedResponse[PermissionRead])
def list_permissions(
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return PermissionController.list_permissions(db, params, search=search)


@roles_router.post("/permissions/assign", response_model=RolePermissionRead, status_code=status.HTTP_201_CREATED)
def assign_role_permission(
    data: RolePermissionCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return PermissionController.assign_role_permission(db, data)


@roles_router.delete("/permissions/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
def remove_role_permission(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return PermissionController.remove_role_permission(db, assignment_id)


@roles_router.get("/{role_id}", response_model=RoleRead)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return RoleController.get_role(db, role_id)


@roles_router.put("/{role_id}", response_model=RoleRead)
@roles_router.patch("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return RoleController.update_role(db, role_id, data)


@roles_router.delete("/{role_id}", status_code=status.HTTP_200_OK)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return RoleController.delete_role(db, role_id)


# --- USER ROLES (TENANT SCOPED) ---
@user_roles_router.post("", response_model=UserRoleRead, status_code=status.HTTP_201_CREATED)
def assign_user_role(
    data: UserRoleCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UserRoleController.assign_role(db, tenant, data)


@user_roles_router.get("", response_model=PaginatedResponse[UserRoleRead])
def list_user_roles(
    params: PaginationParams = Depends(),
    user_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return UserRoleController.list_user_roles(
        db, tenant, params, user_id=user_id, role_id=role_id, active_only=active_only
    )


@user_roles_router.post("/{user_role_id}/revoke", response_model=UserRoleRead)
def revoke_user_role(
    user_role_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UserRoleController.revoke_role(db, tenant, user_role_id)


@user_roles_router.delete("/{user_role_id}", status_code=status.HTTP_200_OK)
def delete_user_role(
    user_role_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("university_admin")),
):
    return UserRoleController.delete_user_role(db, tenant, user_role_id)
