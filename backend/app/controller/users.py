"""Controller for user, authentication, role, and permission operations."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..core.security import create_access_token
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
from ..services.users import PermissionService, RoleService, UserRoleService, UserService


class UserController:
    @staticmethod
    def register(db: Session, data: UserCreate) -> UserRead:
        user = UserService.create_user(db, data)
        return UserRead.model_validate(user)

    @staticmethod
    def login(db: Session, data: LoginRequest) -> TokenResponse:
        user = UserService.authenticate(db, data.email, data.password)
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )

    @staticmethod
    def get_me(current_user: User) -> UserRead:
        return UserRead.model_validate(current_user)

    @staticmethod
    def get_user(db: Session, user_id: int) -> UserRead:
        user = UserService.get_user_by_id(db, user_id)
        return UserRead.model_validate(user)

    @staticmethod
    def list_users(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        status: Optional[AccountStatus] = None,
    ) -> PaginatedResponse[UserRead]:
        items, total, total_pages = UserService.list_users(db, params, search=search, status=status)
        return PaginatedResponse(
            items=[UserRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_user(db: Session, user_id: int, data: UserUpdate) -> UserRead:
        user = UserService.update_user(db, user_id, data)
        return UserRead.model_validate(user)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict[str, str]:
        UserService.delete_user(db, user_id)
        return {"status": "success", "message": f"User {user_id} deleted successfully"}


class RoleController:
    @staticmethod
    def create_role(db: Session, data: RoleCreate) -> RoleRead:
        role = RoleService.create_role(db, data)
        return RoleRead.model_validate(role)

    @staticmethod
    def get_role(db: Session, role_id: int) -> RoleRead:
        role = RoleService.get_role(db, role_id)
        return RoleRead.model_validate(role)

    @staticmethod
    def list_roles(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[RoleRead]:
        items, total, total_pages = RoleService.list_roles(db, params, search=search, is_active=is_active)
        return PaginatedResponse(
            items=[RoleRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_role(db: Session, role_id: int, data: RoleUpdate) -> RoleRead:
        role = RoleService.update_role(db, role_id, data)
        return RoleRead.model_validate(role)

    @staticmethod
    def delete_role(db: Session, role_id: int) -> dict[str, str]:
        RoleService.delete_role(db, role_id)
        return {"status": "success", "message": f"Role {role_id} deleted"}


class PermissionController:
    @staticmethod
    def create_permission(db: Session, data: PermissionCreate) -> PermissionRead:
        perm = PermissionService.create_permission(db, data)
        return PermissionRead.model_validate(perm)

    @staticmethod
    def get_permission(db: Session, perm_id: uuid.UUID) -> PermissionRead:
        perm = PermissionService.get_permission(db, perm_id)
        return PermissionRead.model_validate(perm)

    @staticmethod
    def list_permissions(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
    ) -> PaginatedResponse[PermissionRead]:
        items, total, total_pages = PermissionService.list_permissions(db, params, search=search)
        return PaginatedResponse(
            items=[PermissionRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def assign_role_permission(db: Session, data: RolePermissionCreate) -> RolePermissionRead:
        rp = PermissionService.assign_role_permission(db, data)
        return RolePermissionRead.model_validate(rp)

    @staticmethod
    def remove_role_permission(db: Session, role_permission_id: uuid.UUID) -> dict[str, str]:
        PermissionService.remove_role_permission(db, role_permission_id)
        return {"status": "success", "message": f"Role permission {role_permission_id} removed"}


class UserRoleController:
    @staticmethod
    def assign_role(db: Session, tenant: TenantContext, data: UserRoleCreate) -> UserRoleRead:
        ur = UserRoleService.assign_user_role(
            db=db,
            university_id=tenant.university_id,
            data=data,
            assigner_id=tenant.user.id,
        )
        return UserRoleRead.model_validate(ur)

    @staticmethod
    def revoke_role(db: Session, tenant: TenantContext, user_role_id: int) -> UserRoleRead:
        ur = UserRoleService.revoke_user_role(
            db=db,
            university_id=tenant.university_id,
            user_role_id=user_role_id,
        )
        return UserRoleRead.model_validate(ur)

    @staticmethod
    def list_user_roles(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        user_id: Optional[int] = None,
        role_id: Optional[int] = None,
        active_only: bool = True,
    ) -> PaginatedResponse[UserRoleRead]:
        items, total, total_pages = UserRoleService.list_user_roles(
            db=db,
            university_id=tenant.university_id,
            params=params,
            user_id=user_id,
            role_id=role_id,
            active_only=active_only,
        )
        return PaginatedResponse(
            items=[UserRoleRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_user_role(db: Session, tenant: TenantContext, user_role_id: int) -> dict[str, str]:
        UserRoleService.delete_user_role(db, tenant.university_id, user_role_id)
        return {"status": "success", "message": f"User role {user_role_id} deleted"}

