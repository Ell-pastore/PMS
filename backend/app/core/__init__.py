"""Core application components: config, security, exceptions, pagination, and dependencies."""

from .config import settings
from .dependencies import TenantContext, get_current_user, get_tenant_context, require_roles
from .exceptions import (
    DatabaseError,
    DuplicateResourceError,
    ForbiddenError,
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
    PMSException,
    SpecializedOperationError,
    UnauthorizedError,
    register_exception_handlers,
)
from .pagination import PaginatedResponse, PaginationParams, paginate
from .security import create_access_token, decode_access_token, hash_password, verify_password

__all__ = [
    "DatabaseError",
    "DuplicateResourceError",
    "ForbiddenError",
    "ForeignKeyViolationError",
    "InvalidInputError",
    "NotFoundError",
    "PMSException",
    "PaginatedResponse",
    "PaginationParams",
    "SpecializedOperationError",
    "TenantContext",
    "UnauthorizedError",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_tenant_context",
    "hash_password",
    "paginate",
    "register_exception_handlers",
    "require_roles",
    "settings",
    "verify_password",
]
