"""FastAPI dependencies for database session, authentication, and tenant context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models import AccountStatus, Role, University, UniversityMembership, User, UserRole
from .exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from .security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)


@dataclass
class TenantContext:
    """Current authenticated user and tenant scope."""

    user: User
    university_id: uuid.UUID
    roles: list[str]

    def has_role(self, *role_codes: str) -> bool:
        """Check if user has any of the given role codes or is superadmin."""
        if "superadmin" in self.roles:
            return True
        return any(rc in self.roles for rc in role_codes)


def get_current_user(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_user_id: Optional[int] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the currently authenticated user via Bearer token or X-User-Id header."""
    user_id: Optional[int] = None

    if auth_creds and auth_creds.credentials:
        payload = decode_access_token(auth_creds.credentials)
        if not payload:
            raise UnauthorizedError("Invalid or expired authentication token")
        sub = payload.get("sub")
        if sub is not None:
            try:
                user_id = int(sub)
            except ValueError:
                raise UnauthorizedError("Malformed subject in token")

    if user_id is None and x_user_id is not None:
        user_id = x_user_id

    if user_id is None:
        raise UnauthorizedError("Authentication credentials missing")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise UnauthorizedError("User account not found")

    if user.status != AccountStatus.ACTIVE:
        raise ForbiddenError(f"User account is {user.status.value}")

    return user


def get_tenant_context(
    current_user: User = Depends(get_current_user),
    x_university_id: Optional[str] = Header(None, alias="X-University-ID"),
    university_id_query: Optional[str] = Query(None, alias="university_id"),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Resolve the active university tenant and verify active membership and roles."""
    raw_univ_id = x_university_id or university_id_query
    if not raw_univ_id:
        raise ForbiddenError("X-University-ID header is required for university-scoped operations")

    try:
        univ_uuid = uuid.UUID(str(raw_univ_id))
    except ValueError:
        raise ForbiddenError("Invalid X-University-ID UUID format")

    # Verify university exists
    university = db.scalar(select(University).where(University.id == univ_uuid))
    if not university:
        raise NotFoundError("University tenant not found")
    if not university.is_active:
        raise ForbiddenError("University tenant is inactive")

    # Load active user roles for this university
    stmt = (
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.university_id == univ_uuid,
            UserRole.user_id == current_user.id,
            UserRole.revoked_at.is_(None),
            Role.is_active.is_(True),
        )
    )
    user_roles = list(db.scalars(stmt).all())

    # Check for superadmin (can operate anywhere)
    global_superadmin = db.scalar(
        select(UserRole.id)
        .join(Role, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == current_user.id,
            Role.code == "superadmin",
            UserRole.revoked_at.is_(None),
        )
    )
    if global_superadmin and "superadmin" not in user_roles:
        user_roles.append("superadmin")

    # Check university membership
    membership = db.scalar(
        select(UniversityMembership).where(
            UniversityMembership.university_id == univ_uuid,
            UniversityMembership.user_id == current_user.id,
        )
    )

    if not membership or not membership.is_active:
        if "superadmin" not in user_roles:
            raise ForbiddenError("User is not an active member of this university")

    return TenantContext(
        user=current_user,
        university_id=univ_uuid,
        roles=user_roles,
    )


def require_roles(*allowed_roles: str) -> Callable[[TenantContext], TenantContext]:
    """Dependency factory ensuring user has at least one required role."""

    def role_checker(tenant: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not tenant.has_role(*allowed_roles):
            raise ForbiddenError(
                f"Action requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return tenant

    return role_checker

