"""FastAPI routes for stored files, document attachments, audit logs, and retention policies."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.files_audit_retention import (
    AuditLogController,
    DocumentAttachmentController,
    RetentionPolicyController,
    StoredFileController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.files_audit_retention import (
    AuditLogCreate,
    AuditLogRead,
    DocumentAttachmentCreate,
    DocumentAttachmentRead,
    RetentionPolicyCreate,
    RetentionPolicyRead,
    RetentionPolicyUpdate,
    StoredFileCreate,
    StoredFileRead,
    StoredFileUpdate,
)

stored_files_router = APIRouter(prefix="/stored-files", tags=["Stored Files"])
attachments_router = APIRouter(prefix="/document-attachments", tags=["Document Attachments"])
audit_logs_router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])
retention_policies_router = APIRouter(prefix="/retention-policies", tags=["Retention Policies"])


# --- STORED FILES ---
@stored_files_router.post("", response_model=StoredFileRead, status_code=status.HTTP_201_CREATED)
def create_file(
    data: StoredFileCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StoredFileController.create_file(db, tenant, data)


@stored_files_router.get("", response_model=PaginatedResponse[StoredFileRead])
def list_files(
    params: PaginationParams = Depends(),
    uploader_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StoredFileController.list_files(
        db,
        tenant,
        params,
        uploader_id=uploader_id,
        search=search,
        include_deleted=include_deleted,
    )


@stored_files_router.get("/{file_id}", response_model=StoredFileRead)
def get_file(
    file_id: uuid.UUID,
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StoredFileController.get_file(
        db, tenant, file_id, include_deleted=include_deleted
    )


@stored_files_router.patch("/{file_id}", response_model=StoredFileRead)
def update_file(
    file_id: uuid.UUID,
    data: StoredFileUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StoredFileController.update_file(db, tenant, file_id, data)


@stored_files_router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(
    file_id: uuid.UUID,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StoredFileController.delete_file(db, tenant, file_id, hard_delete=hard_delete)


# --- DOCUMENT ATTACHMENTS ---
@attachments_router.post("", response_model=DocumentAttachmentRead, status_code=status.HTTP_201_CREATED)
def create_attachment(
    data: DocumentAttachmentCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DocumentAttachmentController.create_attachment(db, tenant, data)


@attachments_router.get("", response_model=PaginatedResponse[DocumentAttachmentRead])
def list_attachments(
    params: PaginationParams = Depends(),
    stored_file_id: Optional[uuid.UUID] = Query(None),
    proposal_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    progress_report_id: Optional[uuid.UUID] = Query(None),
    grant_application_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DocumentAttachmentController.list_attachments(
        db,
        tenant,
        params,
        stored_file_id=stored_file_id,
        proposal_id=proposal_id,
        project_id=project_id,
        progress_report_id=progress_report_id,
        grant_application_id=grant_application_id,
    )


@attachments_router.get("/{attachment_id}", response_model=DocumentAttachmentRead)
def get_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DocumentAttachmentController.get_attachment(db, tenant, attachment_id)


@attachments_router.delete("/{attachment_id}", status_code=status.HTTP_200_OK)
def delete_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return DocumentAttachmentController.delete_attachment(db, tenant, attachment_id)


# --- AUDIT LOGS ---
@audit_logs_router.post("", response_model=AuditLogRead, status_code=status.HTTP_201_CREATED)
def create_log(
    data: AuditLogCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return AuditLogController.create_log(db, tenant, data)


@audit_logs_router.get("", response_model=PaginatedResponse[AuditLogRead])
def list_logs(
    params: PaginationParams = Depends(),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    acting_user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AuditLogController.list_logs(
        db,
        tenant,
        params,
        entity_type=entity_type,
        action=action,
        acting_user_id=acting_user_id,
        search=search,
    )


@audit_logs_router.get("/{log_id}", response_model=AuditLogRead)
def get_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AuditLogController.get_log(db, tenant, log_id)


@audit_logs_router.put("/{log_id}")
@audit_logs_router.patch("/{log_id}")
def update_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    AuditLogController.update_log(db, tenant, log_id)


@audit_logs_router.delete("/{log_id}")
def delete_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    AuditLogController.delete_log(db, tenant, log_id)


# --- RETENTION POLICIES ---
@retention_policies_router.post("", response_model=RetentionPolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    data: RetentionPolicyCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return RetentionPolicyController.create_policy(db, tenant, data)


@retention_policies_router.get("", response_model=PaginatedResponse[RetentionPolicyRead])
def list_policies(
    params: PaginationParams = Depends(),
    record_category: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    is_enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return RetentionPolicyController.list_policies(
        db,
        tenant,
        params,
        record_category=record_category,
        department_id=department_id,
        is_enabled=is_enabled,
    )


@retention_policies_router.get("/{policy_id}", response_model=RetentionPolicyRead)
def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return RetentionPolicyController.get_policy(db, tenant, policy_id)


@retention_policies_router.patch("/{policy_id}", response_model=RetentionPolicyRead)
def update_policy(
    policy_id: uuid.UUID,
    data: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return RetentionPolicyController.update_policy(db, tenant, policy_id, data)


@retention_policies_router.delete("/{policy_id}", status_code=status.HTTP_200_OK)
def delete_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("research_admin", "university_admin")),
):
    return RetentionPolicyController.delete_policy(db, tenant, policy_id)

