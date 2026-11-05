"""Pydantic schemas for stored files, document attachments, audit logs, and retention policies."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- STORED FILE ---
class StoredFileBase(BaseModel):
    storage_key: str = Field(..., max_length=1024)
    original_filename: str = Field(..., max_length=512)
    content_type: str = Field(..., max_length=255)
    file_size_bytes: int = Field(..., ge=0)
    checksum: Optional[str] = Field(None, max_length=128)


class StoredFileCreate(StoredFileBase):
    pass


class StoredFileUpdate(BaseModel):
    original_filename: Optional[str] = Field(None, max_length=512)
    content_type: Optional[str] = Field(None, max_length=255)
    checksum: Optional[str] = Field(None, max_length=128)


class StoredFileRead(StoredFileBase):
    id: uuid.UUID
    university_id: uuid.UUID
    uploader_id: int
    created_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- DOCUMENT ATTACHMENTS ---
class DocumentAttachmentBase(BaseModel):
    stored_file_id: uuid.UUID
    proposal_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    progress_report_id: Optional[uuid.UUID] = None
    grant_application_id: Optional[uuid.UUID] = None
    document_type: str = Field(..., max_length=64)


class DocumentAttachmentCreate(DocumentAttachmentBase):
    pass


class DocumentAttachmentRead(DocumentAttachmentBase):
    id: uuid.UUID
    university_id: uuid.UUID
    uploader_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- AUDIT LOGS ---
class AuditLogCreate(BaseModel):
    action: str = Field(..., max_length=128)
    entity_type: str = Field(..., max_length=128)
    entity_uuid: Optional[uuid.UUID] = None
    entity_integer: Optional[int] = None
    request_id: Optional[str] = Field(None, max_length=128)
    audit_metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    acting_user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_uuid: Optional[uuid.UUID] = None
    entity_integer: Optional[int] = None
    event_at: datetime
    request_id: Optional[str] = None
    audit_metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


# --- RETENTION POLICIES ---
class RetentionPolicyBase(BaseModel):
    record_category: str = Field(..., max_length=128)
    retention_days: int = Field(..., gt=0)
    post_retention_action: str = Field("review", pattern="^(review|archive|anonymize|delete)$")
    department_id: Optional[int] = None
    is_enabled: bool = True


class RetentionPolicyCreate(RetentionPolicyBase):
    pass


class RetentionPolicyUpdate(BaseModel):
    retention_days: Optional[int] = Field(None, gt=0)
    post_retention_action: Optional[str] = Field(None, pattern="^(review|archive|anonymize|delete)$")
    department_id: Optional[int] = None
    is_enabled: Optional[bool] = None


class RetentionPolicyRead(RetentionPolicyBase):
    id: uuid.UUID
    university_id: uuid.UUID
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

