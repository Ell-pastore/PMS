"""Pagination utilities and response models."""

from __future__ import annotations

import math
from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

T = TypeVar("T")


class PaginationParams:
    """Dependency for extracting and validating pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number starting from 1"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated envelope returned by list endpoints."""

    items: list[T]
    total: int = Field(..., description="Total matching records count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Records per page")
    total_pages: int = Field(..., description="Total pages available")


def paginate(
    query: Select,
    db: Session,
    params: PaginationParams,
) -> tuple[Sequence[Any], int, int]:
    """Execute pagination on a SQLAlchemy Select query.

    Returns:
        (items, total_count, total_pages)
    """
    # Count total records using subquery to support arbitrary group by / joins
    count_subquery = query.order_by(None).subquery()
    count_stmt = select(func.count()).select_from(count_subquery)
    total = db.scalar(count_stmt) or 0

    total_pages = math.ceil(total / params.page_size) if total > 0 else 0

    paginated_stmt = query.offset(params.offset).limit(params.limit)
    items = db.scalars(paginated_stmt).all()

    return items, total, total_pages

