"""Controllers for stored files, document attachments, audit logs, and retention policies."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
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
from ..services.files_audit_retention import (
    AuditLogService,
    DocumentAttachmentService,
    RetentionPolicyService,
    StoredFileService,
)


class StoredFileController:
    @staticmethod
    def create_file(
        db: Session,
        tenant: TenantContext,
        data: StoredFileCreate,
    ) -> StoredFileRead:
        file_obj = StoredFileService.create_file(db, tenant.university_id, data, tenant.user.id)
        return StoredFileRead.model_validate(file_obj)

    @staticmethod
    def get_file(
        db: Session,
        tenant: TenantContext,
        file_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> StoredFileRead:
        file_obj = StoredFileService.get_file(
            db, tenant.university_id, file_id, include_deleted=include_deleted
        )
        return StoredFileRead.model_validate(file_obj)

    @staticmethod
    def list_files(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        uploader_id: Optional[int] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
    ) -> PaginatedResponse[StoredFileRead]:
        items, total, total_pages = StoredFileService.list_files(
            db,
            tenant.university_id,
            params,
            uploader_id=uploader_id,
            search=search,
            include_deleted=include_deleted,
        )
        return PaginatedResponse(
            items=[StoredFileRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_file(
        db: Session,
        tenant: TenantContext,
        file_id: uuid.UUID,
        data: StoredFileUpdate,
    ) -> StoredFileRead:
        file_obj = StoredFileService.update_file(db, tenant.university_id, file_id, data)
        return StoredFileRead.model_validate(file_obj)

    @staticmethod
    def delete_file(
        db: Session,
        tenant: TenantContext,
        file_id: uuid.UUID,
        hard_delete: bool = False,
    ) -> dict[str, str]:
        StoredFileService.delete_file(db, tenant.university_id, file_id, hard_delete=hard_delete)
        action_desc = "hard deleted" if hard_delete else "soft deleted"
        return {"status": "success", "message": f"Stored file {file_id} {action_desc}"}


class DocumentAttachmentController:
    @staticmethod
    def create_attachment(
        db: Session,
        tenant: TenantContext,
        data: DocumentAttachmentCreate,
    ) -> DocumentAttachmentRead:
        att = DocumentAttachmentService.create_attachment(
            db, tenant.university_id, data, tenant.user.id
        )
        return DocumentAttachmentRead.model_validate(att)

    @staticmethod
    def get_attachment(
        db: Session,
        tenant: TenantContext,
        attachment_id: uuid.UUID,
    ) -> DocumentAttachmentRead:
        att = DocumentAttachmentService.get_attachment(db, tenant.university_id, attachment_id)
        return DocumentAttachmentRead.model_validate(att)

    @staticmethod
    def list_attachments(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        stored_file_id: Optional[uuid.UUID] = None,
        proposal_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        progress_report_id: Optional[uuid.UUID] = None,
        grant_application_id: Optional[uuid.UUID] = None,
    ) -> PaginatedResponse[DocumentAttachmentRead]:
        items, total, total_pages = DocumentAttachmentService.list_attachments(
            db,
            tenant.university_id,
            params,
            stored_file_id=stored_file_id,
            proposal_id=proposal_id,
            project_id=project_id,
            progress_report_id=progress_report_id,
            grant_application_id=grant_application_id,
        )
        return PaginatedResponse(
            items=[DocumentAttachmentRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_attachment(
        db: Session,
        tenant: TenantContext,
        attachment_id: uuid.UUID,
    ) -> dict[str, str]:
        DocumentAttachmentService.delete_attachment(db, tenant.university_id, attachment_id)
        return {"status": "success", "message": f"Document attachment {attachment_id} deleted"}


class AuditLogController:
    @staticmethod
    def create_log(
        db: Session,
        tenant: TenantContext,
        data: AuditLogCreate,
    ) -> AuditLogRead:
        log = AuditLogService.create_log(db, tenant.university_id, data, tenant.user.id)
        return AuditLogRead.model_validate(log)

    @staticmethod
    def get_log(
        db: Session,
        tenant: TenantContext,
        log_id: uuid.UUID,
    ) -> AuditLogRead:
        log = AuditLogService.get_log(db, tenant.university_id, log_id)
        return AuditLogRead.model_validate(log)

    @staticmethod
    def list_logs(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        acting_user_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[AuditLogRead]:
        items, total, total_pages = AuditLogService.list_logs(
            db,
            tenant.university_id,
            params,
            entity_type=entity_type,
            action=action,
            acting_user_id=acting_user_id,
            search=search,
        )
        return PaginatedResponse(
            items=[AuditLogRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_log(
        db: Session,
        tenant: TenantContext,
        log_id: uuid.UUID,
    ) -> None:
        AuditLogService.update_log(db, tenant.university_id, log_id)

    @staticmethod
    def delete_log(
        db: Session,
        tenant: TenantContext,
        log_id: uuid.UUID,
    ) -> None:
        AuditLogService.delete_log(db, tenant.university_id, log_id)


class RetentionPolicyController:
    @staticmethod
    def create_policy(
        db: Session,
        tenant: TenantContext,
        data: RetentionPolicyCreate,
    ) -> RetentionPolicyRead:
        policy = RetentionPolicyService.create_policy(
            db, tenant.university_id, data, tenant.user.id
        )
        return RetentionPolicyRead.model_validate(policy)

    @staticmethod
    def get_policy(
        db: Session,
        tenant: TenantContext,
        policy_id: uuid.UUID,
    ) -> RetentionPolicyRead:
        policy = RetentionPolicyService.get_policy(db, tenant.university_id, policy_id)
        return RetentionPolicyRead.model_validate(policy)

    @staticmethod
    def list_policies(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        record_category: Optional[str] = None,
        department_id: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> PaginatedResponse[RetentionPolicyRead]:
        items, total, total_pages = RetentionPolicyService.list_policies(
            db,
            tenant.university_id,
            params,
            record_category=record_category,
            department_id=department_id,
            is_enabled=is_enabled,
        )
        return PaginatedResponse(
            items=[RetentionPolicyRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_policy(
        db: Session,
        tenant: TenantContext,
        policy_id: uuid.UUID,
        data: RetentionPolicyUpdate,
    ) -> RetentionPolicyRead:
        policy = RetentionPolicyService.update_policy(db, tenant.university_id, policy_id, data)
        return RetentionPolicyRead.model_validate(policy)

    @staticmethod
    def delete_policy(
        db: Session,
        tenant: TenantContext,
        policy_id: uuid.UUID,
    ) -> dict[str, str]:
        RetentionPolicyService.delete_policy(db, tenant.university_id, policy_id)
        return {"status": "success", "message": f"Retention policy {policy_id} deleted"}

