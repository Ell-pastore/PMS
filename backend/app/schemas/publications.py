"""Pydantic schemas for publications, authors, project links, and reviews."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- PUBLICATION ---
class PublicationBase(BaseModel):
    title: str = Field(..., max_length=500)
    publication_type: str = Field(..., max_length=64)
    abstract: Optional[str] = None
    doi: Optional[str] = Field(None, max_length=255)
    journal: Optional[str] = Field(None, max_length=255)
    publisher: Optional[str] = Field(None, max_length=255)
    publication_date: Optional[date] = None
    volume: Optional[str] = Field(None, max_length=64)
    issue: Optional[str] = Field(None, max_length=64)
    page_range: Optional[str] = Field(None, max_length=64)
    url: Optional[str] = Field(None, max_length=2048)


class PublicationCreate(PublicationBase):
    pass


class PublicationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    publication_type: Optional[str] = Field(None, max_length=64)
    abstract: Optional[str] = None
    doi: Optional[str] = Field(None, max_length=255)
    journal: Optional[str] = Field(None, max_length=255)
    publisher: Optional[str] = Field(None, max_length=255)
    publication_date: Optional[date] = None
    volume: Optional[str] = Field(None, max_length=64)
    issue: Optional[str] = Field(None, max_length=64)
    page_range: Optional[str] = Field(None, max_length=64)
    url: Optional[str] = Field(None, max_length=2048)
    verification_status: Optional[str] = Field(None, max_length=32)


class PublicationRead(PublicationBase):
    id: uuid.UUID
    university_id: uuid.UUID
    normalized_doi: Optional[str] = None
    verification_status: str
    submitter_id: int
    verifier_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PUBLICATION AUTHORS ---
class PublicationAuthorCreate(BaseModel):
    internal_user_id: Optional[int] = None
    external_author_name: Optional[str] = Field(None, max_length=255)
    external_affiliation: Optional[str] = Field(None, max_length=255)
    author_order: int = Field(..., gt=0)
    is_corresponding: bool = False

    @model_validator(mode="after")
    def validate_xor_identity(self) -> PublicationAuthorCreate:
        has_internal = self.internal_user_id is not None
        has_external = self.external_author_name is not None
        if has_internal == has_external:
            raise ValueError("Must specify either internal_user_id OR external_author_name, but not both")
        return self


class PublicationAuthorRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    publication_id: uuid.UUID
    internal_user_id: Optional[int] = None
    external_author_name: Optional[str] = None
    external_affiliation: Optional[str] = None
    author_order: int
    is_corresponding: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PUBLICATION PROJECTS ---
class PublicationProjectCreate(BaseModel):
    project_id: uuid.UUID


class PublicationProjectRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    publication_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PUBLICATION REVIEWS ---
class PublicationReviewCreate(BaseModel):
    decision: str = Field(..., max_length=32, pattern="^(verified|rejected|revision_requested|commented)$")
    comments: Optional[str] = None


class PublicationReviewRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    publication_id: uuid.UUID
    reviewer_id: int
    decision: str
    comments: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

