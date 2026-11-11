"""User, authentication, role, and permission service layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForbiddenError,
    ForeignKeyViolationError,
    NotFoundError,
    SpecializedOperationError,
    UnauthorizedError,
)
from ..core.pagination import PaginationParams, paginate
from ..core.security import hash_password, verify_password
from ..models import (
    AccountStatus,
    AccountVerification,
    Permission,
    Role,
    RolePermission,
    StaffProfile,
    StudentProfile,
    UniversityMembership,
    User,
    UserRole,
)
from ..schemas.users import (
    AccountVerificationCreate,
    PermissionCreate,
    PermissionUpdate,
    RoleCreate,
    RolePermissionCreate,
    RoleUpdate,
    UserCreate,
    UserRoleCreate,
    UserUpdate,
)


class UserService:
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User:
        user = db.scalar(select(User).where(func.lower(User.email) == email.strip().casefold()))
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if user.status != AccountStatus.ACTIVE:
            raise ForbiddenError(f"Account is {user.status.value}")

        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_user(db: Session, data: UserCreate) -> User:
        existing = db.scalar(select(User).where(func.lower(User.email) == data.email.strip().casefold()))
        if existing:
            raise DuplicateResourceError(f"User with email '{data.email}' already exists")

        user = User(
            full_name=data.full_name,
            email=data.email,
            password_hash=hash_password(data.password),
            status=data.status or AccountStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    @staticmethod
    def list_users(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        status: Optional[AccountStatus] = None,
    ) -> tuple[Sequence[User], int, int]:
        query = select(User).order_by(User.id.desc())
        if status:
            query = query.where(User.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(User.full_name.ilike(s), User.email.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
        user = UserService.get_user_by_id(db, user_id)
        if data.email is not None and data.email.strip().casefold() != user.email:
            existing = db.scalar(select(User).where(func.lower(User.email) == data.email.strip().casefold()))
            if existing:
                raise DuplicateResourceError(f"User with email '{data.email}' already exists")
            user.email = data.email
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.password is not None:
            user.password_hash = hash_password(data.password)
        if data.status is not None:
            user.status = data.status

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> None:
        user = UserService.get_user_by_id(db, user_id)

        # Guard against deleting an account that still holds tenant data
        # (RESTRICT foreign keys would otherwise surface as a raw integrity
        # error). Historical activity such as audit log entries keeps the
        # account retained by design.
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(UniversityMembership).where(UniversityMembership.user_id == user.id)):
            blockers.append("university memberships")
        if db.scalar(select(func.count()).select_from(UserRole).where(or_(UserRole.user_id == user.id, UserRole.assigned_by_id == user.id))):
            blockers.append("role assignments")
        if db.scalar(select(func.count()).select_from(StaffProfile).where(StaffProfile.user_id == user.id)):
            blockers.append("staff profiles")
        if db.scalar(select(func.count()).select_from(StudentProfile).where(StudentProfile.user_id == user.id)):
            blockers.append("student profiles")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete user with existing {', '.join(blockers)}. Remove them first."
            )

        # Cascade machine-generated verification tokens, then delete the
        # account in a single transaction.
        db.execute(delete(AccountVerification).where(AccountVerification.user_id == user.id))
        db.delete(user)
        db.commit()


class RoleService:
    @staticmethod
    def create_role(db: Session, data: RoleCreate) -> Role:
        existing = db.scalar(select(Role).where(or_(Role.code == data.code, Role.name == data.name)))
        if existing:
            raise DuplicateResourceError(f"Role with code '{data.code}' or name '{data.name}' already exists")
        role = Role(
            code=data.code,
            name=data.name,
            description=data.description,
            is_active=data.is_active,
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def get_role(db: Session, role_id: int) -> Role:
        role = db.scalar(select(Role).where(Role.id == role_id))
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        return role

    @staticmethod
    def list_roles(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[Sequence[Role], int, int]:
        query = select(Role).order_by(Role.id.asc())
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Role.name.ilike(s), Role.code.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_role(db: Session, role_id: int, data: RoleUpdate) -> Role:
        role = RoleService.get_role(db, role_id)
        if data.name is not None and data.name != role.name:
            existing = db.scalar(select(Role).where(Role.name == data.name))
            if existing:
                raise DuplicateResourceError(f"Role with name '{data.name}' already exists")
            role.name = data.name
        if data.description is not None:
            role.description = data.description
        if data.is_active is not None:
            role.is_active = data.is_active
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role_id: int) -> None:
        role = RoleService.get_role(db, role_id)
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id)):
            blockers.append("user role assignments")
        if db.scalar(select(func.count()).select_from(RolePermission).where(RolePermission.role_id == role.id)):
            blockers.append("permission assignments")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete role with existing {', '.join(blockers)}. Remove them first."
            )
        db.delete(role)
        db.commit()


class PermissionService:
    @staticmethod
    def create_permission(db: Session, data: PermissionCreate) -> Permission:
        existing = db.scalar(select(Permission).where(Permission.code == data.code))
        if existing:
            raise DuplicateResourceError(f"Permission with code '{data.code}' already exists")
        perm = Permission(
            code=data.code,
            description=data.description,
            is_active=data.is_active,
        )
        db.add(perm)
        db.commit()
        db.refresh(perm)
        return perm

    @staticmethod
    def get_permission(db: Session, perm_id: uuid.UUID) -> Permission:
        perm = db.scalar(select(Permission).where(Permission.id == perm_id))
        if not perm:
            raise NotFoundError(f"Permission {perm_id} not found")
        return perm

    @staticmethod
    def list_permissions(
        db: Session,
        params: PaginationParams,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Permission], int, int]:
        query = select(Permission).order_by(Permission.created_at.desc())
        if search:
            query = query.where(Permission.code.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def assign_role_permission(db: Session, data: RolePermissionCreate) -> RolePermission:
        RoleService.get_role(db, data.role_id)
        PermissionService.get_permission(db, data.permission_id)
        existing = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == data.role_id,
                RolePermission.permission_id == data.permission_id,
            )
        )
        if existing:
            raise DuplicateResourceError("Permission already assigned to this role")
        rp = RolePermission(role_id=data.role_id, permission_id=data.permission_id)
        db.add(rp)
        db.commit()
        db.refresh(rp)
        return rp

    @staticmethod
    def remove_role_permission(db: Session, role_permission_id: uuid.UUID) -> None:
        rp = db.scalar(select(RolePermission).where(RolePermission.id == role_permission_id))
        if not rp:
            raise NotFoundError(f"Role permission {role_permission_id} not found")
        db.delete(rp)
        db.commit()


class UserRoleService:
    @staticmethod
    def assign_user_role(
        db: Session,
        university_id: uuid.UUID,
        data: UserRoleCreate,
        assigner_id: Optional[int] = None,
    ) -> UserRole:
        # Validate membership of user in this university
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {data.user_id} does not have membership in university {university_id}")

        # Validate assigner membership if provided
        if assigner_id:
            assigner_membership = db.scalar(
                select(UniversityMembership).where(
                    UniversityMembership.university_id == university_id,
                    UniversityMembership.user_id == assigner_id,
                )
            )
            if not assigner_membership:
                raise ForeignKeyViolationError(f"Assigner {assigner_id} does not have membership in university {university_id}")

        RoleService.get_role(db, data.role_id)

        # Check existing active assignment
        existing = db.scalar(
            select(UserRole).where(
                UserRole.university_id == university_id,
                UserRole.user_id == data.user_id,
                UserRole.role_id == data.role_id,
                UserRole.revoked_at.is_(None),
            )
        )
        if existing:
            raise DuplicateResourceError("User already has this role actively assigned in this university")

        ur = UserRole(
            university_id=university_id,
            user_id=data.user_id,
            role_id=data.role_id,
            assigned_by_id=assigner_id,
        )
        db.add(ur)
        db.commit()
        db.refresh(ur)
        return ur

    @staticmethod
    def revoke_user_role(db: Session, university_id: uuid.UUID, user_role_id: int) -> UserRole:
        ur = db.scalar(
            select(UserRole).where(
                UserRole.id == user_role_id,
                UserRole.university_id == university_id,
            )
        )
        if not ur:
            raise NotFoundError(f"User role assignment {user_role_id} not found in this university")
        if ur.revoked_at is not None:
            return ur

        ur.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ur)
        return ur

    @staticmethod
    def list_user_roles(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        user_id: Optional[int] = None,
        role_id: Optional[int] = None,
        active_only: bool = True,
    ) -> tuple[Sequence[UserRole], int, int]:
        query = select(UserRole).where(UserRole.university_id == university_id).order_by(UserRole.id.desc())
        if user_id:
            query = query.where(UserRole.user_id == user_id)
        if role_id:
            query = query.where(UserRole.role_id == role_id)
        if active_only:
            query = query.where(UserRole.revoked_at.is_(None))
        return paginate(query, db, params)

    @staticmethod
    def delete_user_role(db: Session, university_id: uuid.UUID, user_role_id: int) -> None:
        ur = db.scalar(
            select(UserRole).where(
                UserRole.id == user_role_id,
                UserRole.university_id == university_id,
            )
        )
        if not ur:
            raise NotFoundError(f"User role assignment {user_role_id} not found in this university")
        db.delete(ur)
        db.commit()

