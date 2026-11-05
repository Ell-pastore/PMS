"""Custom PMS exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class PMSException(Exception):
    """Base exception for all PMS business and HTTP exceptions."""

    def __init__(
        self,
        detail: str = "An error occurred",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code


class NotFoundError(PMSException):
    """Resource not found in database or tenant scope."""

    def __init__(
        self,
        detail: str = "Resource not found",
        error_code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
        )


class DuplicateResourceError(PMSException):
    """Resource violates a unique constraint or already exists."""

    def __init__(
        self,
        detail: str = "Resource already exists",
        error_code: str = "DUPLICATE_RESOURCE",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
        )


class ForeignKeyViolationError(PMSException):
    """Referenced foreign key does not exist or belongs to another tenant."""

    def __init__(
        self,
        detail: str = "Invalid foreign key reference or relation violation",
        error_code: str = "FOREIGN_KEY_VIOLATION",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
        )


class InvalidInputError(PMSException):
    """Supplied payload or parameters are logically invalid."""

    def __init__(
        self,
        detail: str = "Invalid input provided",
        error_code: str = "INVALID_INPUT",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
        )


class UnauthorizedError(PMSException):
    """Authentication required or credential validation failed."""

    def __init__(
        self,
        detail: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
        )


class ForbiddenError(PMSException):
    """Operation is forbidden or cross-tenant boundary was crossed."""

    def __init__(
        self,
        detail: str = "Access forbidden",
        error_code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
        )


class DatabaseError(PMSException):
    """Unexpected database error occurred."""

    def __init__(
        self,
        detail: str = "A database error occurred",
        error_code: str = "DATABASE_ERROR",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
        )


class SpecializedOperationError(PMSException):
    """Specialized model lifecycle or immutability rule violated."""

    def __init__(
        self,
        detail: str = "Operation not allowed by model rules",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "RESTRICTED_OPERATION",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status_code,
            error_code=error_code,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach structured error handlers to the FastAPI application."""

    @app.exception_handler(PMSException)
    async def pms_exception_handler(
        _request: Request,
        exc: PMSException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
                "error": type(exc).__name__,
            },
        )

    @app.exception_handler(IntegrityError)
    async def sqlalchemy_integrity_handler(
        _request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        logger.warning("Database integrity error: %s", exc)
        # Parse PostgreSQL SQLSTATE if available
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
            getattr(exc, "orig", None), "pgcode", None
        )

        if sqlstate == "23505":  # unique_violation
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "A record with these unique details already exists.",
                    "error_code": "DUPLICATE_RESOURCE",
                },
            )
        elif sqlstate == "23503":  # foreign_key_violation
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Referenced entity does not exist or relation is invalid.",
                    "error_code": "FOREIGN_KEY_VIOLATION",
                },
            )
        elif sqlstate == "23514":  # check_violation
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Supplied values violate domain validation constraints.",
                    "error_code": "CHECK_CONSTRAINT_VIOLATION",
                },
            )
        elif sqlstate == "23502":  # not_null_violation
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "A required database field was not provided.",
                    "error_code": "NOT_NULL_VIOLATION",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": "Database integrity constraint violation.",
                "error_code": "INTEGRITY_ERROR",
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_general_handler(
        _request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.error("Database error occurred: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal database error occurred.",
                "error_code": "DATABASE_ERROR",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected server error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )

