"""Service layer for stored files, document attachments, audit logs, and retention policies."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForbiddenError,
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    AuditLog,
    Department,
    DocumentAttachment,
    GrantApplication,
    ProgressReport,
    ResearchProject,
    ResearchProposal,
    RetentionPolicy,
    StoredFile,
    UniversityMembership,
)
from ..schemas.files_audit_retention import (
    AuditLogCreate,
    DocumentAttachmentCreate,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    StoredFileCreate,
    StoredFileUpdate,
)

INTEGER_PK_ENTITIES = {
    "users",
    "roles",
    "user_roles",
    "faculties",
    "departments",
    "student_profiles",
    "staff_profiles",
}


class StoredFileService:
    @staticmethod
    def create_file(
        db: Session,
        university_id: uuid.UUID,
        data: StoredFileCreate,
        user_id: int,
    ) -> StoredFile:
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        existing_key = db.scalar(select(StoredFile).where(StoredFile.storage_key == data.storage_key.strip()))
        if existing_key:
            raise DuplicateResourceError(f"File with storage key '{data.storage_key}' already exists")

        file_obj = StoredFile(
            university_id=university_id,
            uploader_id=user_id,
            storage_key=data.storage_key.strip(),
            original_filename=data.original_filename.strip(),
            content_type=data.content_type.strip(),
            file_size_bytes=data.file_size_bytes,
            checksum=data.checksum,
        )
        db.add(file_obj)
        db.commit()
        db.refresh(file_obj)
        return file_obj

    @staticmethod
    def get_file(
        db: Session,
        university_id: uuid.UUID,
        file_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> StoredFile:
        query = select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.university_id == university_id,
        )
        if not include_deleted:
            query = query.where(StoredFile.deleted_at.is_(None))

        file_obj = db.scalar(query)
        if not file_obj:
            raise NotFoundError(f"Stored file {file_id} not found in this university")
        return file_obj

    @staticmethod
    def list_files(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        uploader_id: Optional[int] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[StoredFile], int, int]:
        query = select(StoredFile).where(StoredFile.university_id == university_id).order_by(StoredFile.created_at.desc())
        if not include_deleted:
            query = query.where(StoredFile.deleted_at.is_(None))
        if uploader_id:
            query = query.where(StoredFile.uploader_id == uploader_id)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(StoredFile.original_filename.ilike(s), StoredFile.content_type.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_file(
        db: Session,
        university_id: uuid.UUID,
        file_id: uuid.UUID,
        data: StoredFileUpdate,
    ) -> StoredFile:
        file_obj = StoredFileService.get_file(db, university_id, file_id)
        if data.original_filename is not None:
            file_obj.original_filename = data.original_filename.strip()
        if data.content_type is not None:
            file_obj.content_type = data.content_type.strip()
        if data.checksum is not None:
            file_obj.checksum = data.checksum

        db.commit()
        db.refresh(file_obj)
        return file_obj

    @staticmethod
    def delete_file(
        db: Session,
        university_id: uuid.UUID,
        file_id: uuid.UUID,
        hard_delete: bool = False,
    ) -> None:
        file_obj = StoredFileService.get_file(db, university_id, file_id, include_deleted=True)
        if hard_delete:
            db.delete(file_obj)
        else:
            file_obj.deleted_at = datetime.now(timezone.utc)
        db.commit()


class DocumentAttachmentService:
    @staticmethod
    def create_attachment(
        db: Session,
        university_id: uuid.UUID,
        data: DocumentAttachmentCreate,
        user_id: int,
    ) -> DocumentAttachment:
        StoredFileService.get_file(db, university_id, data.stored_file_id)

        targets = [data.proposal_id, data.project_id, data.progress_report_id, data.grant_application_id]
        non_null_count = sum(1 for t in targets if t is not None)
        if non_null_count != 1:
            raise InvalidInputError("Exactly one target must be provided: proposal_id, project_id, progress_report_id, or grant_application_id")

        if data.proposal_id:
            prop = db.scalar(select(ResearchProposal).where(ResearchProposal.id == data.proposal_id, ResearchProposal.university_id == university_id))
            if not prop:
                raise ForeignKeyViolationError(f"Proposal {data.proposal_id} not found in this university")

        if data.project_id:
            proj = db.scalar(select(ResearchProject).where(ResearchProject.id == data.project_id, ResearchProject.university_id == university_id))
            if not proj:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        if data.progress_report_id:
            rep = db.scalar(select(ProgressReport).where(ProgressReport.id == data.progress_report_id, ProgressReport.university_id == university_id))
            if not rep:
                raise ForeignKeyViolationError(f"Progress report {data.progress_report_id} not found in this university")

        if data.grant_application_id:
            gapp = db.scalar(select(GrantApplication).where(GrantApplication.id == data.grant_application_id, GrantApplication.university_id == university_id))
            if not gapp:
                raise ForeignKeyViolationError(f"Grant application {data.grant_application_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        att = DocumentAttachment(
            university_id=university_id,
            stored_file_id=data.stored_file_id,
            proposal_id=data.proposal_id,
            project_id=data.project_id,
            progress_report_id=data.progress_report_id,
            grant_application_id=data.grant_application_id,
            document_type=data.document_type.strip(),
            uploader_id=user_id,
        )
        db.add(att)
        db.commit()
        db.refresh(att)
        return att

    @staticmethod
    def get_attachment(
        db: Session,
        university_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> DocumentAttachment:
        att = db.scalar(
            select(DocumentAttachment).where(
                DocumentAttachment.id == attachment_id,
                DocumentAttachment.university_id == university_id,
            )
        )
        if not att:
            raise NotFoundError(f"Document attachment {attachment_id} not found in this university")
        return att

    @staticmethod
    def list_attachments(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        stored_file_id: Optional[uuid.UUID] = None,
        proposal_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        progress_report_id: Optional[uuid.UUID] = None,
        grant_application_id: Optional[uuid.UUID] = None,
    ) -> tuple[Sequence[DocumentAttachment], int, int]:
        query = select(DocumentAttachment).where(DocumentAttachment.university_id == university_id).order_by(DocumentAttachment.created_at.desc())
        if stored_file_id:
            query = query.where(DocumentAttachment.stored_file_id == stored_file_id)
        if proposal_id:
            query = query.where(DocumentAttachment.proposal_id == proposal_id)
        if project_id:
            query = query.where(DocumentAttachment.project_id == project_id)
        if progress_report_id:
            query = query.where(DocumentAttachment.progress_report_id == progress_report_id)
        if grant_application_id:
            query = query.where(DocumentAttachment.grant_application_id == grant_application_id)
        return paginate(query, db, params)

    @staticmethod
    def delete_attachment(
        db: Session,
        university_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> None:
        att = DocumentAttachmentService.get_attachment(db, university_id, attachment_id)
        db.delete(att)
        db.commit()


class AuditLogService:
    @staticmethod
    def create_log(
        db: Session,
        university_id: uuid.UUID,
        data: AuditLogCreate,
        user_id: Optional[int] = None,
    ) -> AuditLog:
        # Validate entity identifier constraint
        if data.entity_type in INTEGER_PK_ENTITIES:
            if data.entity_integer is None or data.entity_uuid is not None:
                raise InvalidInputError(
                    f"Entity type '{data.entity_type}' uses integer primary keys: entity_integer must be provided and entity_uuid must be None"
                )
        elif data.entity_uuid is not None:
            if data.entity_integer is not None:
                raise InvalidInputError(
                    f"Entity type '{data.entity_type}' uses UUID primary keys: entity_integer must be None"
                )

        if user_id:
            membership = db.scalar(
                select(UniversityMembership).where(
                    UniversityMembership.university_id == university_id,
                    UniversityMembership.user_id == user_id,
                )
            )
            if not membership:
                raise ForeignKeyViolationError(f"Acting user {user_id} has no membership in this university")

        log = AuditLog(
            university_id=university_id,
            acting_user_id=user_id,
            action=data.action.strip(),
            entity_type=data.entity_type.strip(),
            entity_uuid=data.entity_uuid,
            entity_integer=data.entity_integer,
            request_id=data.request_id,
            audit_metadata=data.audit_metadata,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_log(db: Session, university_id: uuid.UUID, log_id: uuid.UUID) -> AuditLog:
        log = db.scalar(
            select(AuditLog).where(
                AuditLog.id == log_id,
                AuditLog.university_id == university_id,
            )
        )
        if not log:
            raise NotFoundError(f"Audit log {log_id} not found in this university")
        return log

    @staticmethod
    def list_logs(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        acting_user_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[AuditLog], int, int]:
        query = select(AuditLog).where(AuditLog.university_id == university_id).order_by(AuditLog.event_at.desc())
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if action:
            query = query.where(AuditLog.action.ilike(f"%{action.strip()}%"))
        if acting_user_id:
            query = query.where(AuditLog.acting_user_id == acting_user_id)
        if search:
            query = query.where(or_(AuditLog.action.ilike(f"%{search}%"), AuditLog.entity_type.ilike(f"%{search}%")))
        return paginate(query, db, params)

    @staticmethod
    def update_log(db: Session, university_id: uuid.UUID, log_id: uuid.UUID) -> None:
        raise ForbiddenError("Audit logs cannot be updated; records are immutable.")

    @staticmethod
    def delete_log(db: Session, university_id: uuid.UUID, log_id: uuid.UUID) -> None:
        raise ForbiddenError("Audit logs cannot be deleted; records are immutable.")


class RetentionPolicyService:
    @staticmethod
    def create_policy(
        db: Session,
        university_id: uuid.UUID,
        data: RetentionPolicyCreate,
        user_id: int,
    ) -> RetentionPolicy:
        if data.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        # Unique scope check
        if data.department_id is not None:
            existing = db.scalar(
                select(RetentionPolicy).where(
                    RetentionPolicy.university_id == university_id,
                    RetentionPolicy.record_category == data.record_category.strip(),
                    RetentionPolicy.department_id == data.department_id,
                )
            )
        else:
            existing = db.scalar(
                select(RetentionPolicy).where(
                    RetentionPolicy.university_id == university_id,
                    RetentionPolicy.record_category == data.record_category.strip(),
                    RetentionPolicy.department_id.is_(None),
                )
            )
        if existing:
            raise DuplicateResourceError(f"Retention policy for '{data.record_category}' already exists in this scope")

        policy = RetentionPolicy(
            university_id=university_id,
            record_category=data.record_category.strip(),
            retention_days=data.retention_days,
            post_retention_action=data.post_retention_action,
            department_id=data.department_id,
            is_enabled=data.is_enabled,
            created_by_id=user_id,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def get_policy(db: Session, university_id: uuid.UUID, policy_id: uuid.UUID) -> RetentionPolicy:
        policy = db.scalar(
            select(RetentionPolicy).where(
                RetentionPolicy.id == policy_id,
                RetentionPolicy.university_id == university_id,
            )
        )
        if not policy:
            raise NotFoundError(f"Retention policy {policy_id} not found in this university")
        return policy

    @staticmethod
    def list_policies(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        record_category: Optional[str] = None,
        department_id: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> tuple[Sequence[RetentionPolicy], int, int]:
        query = select(RetentionPolicy).where(RetentionPolicy.university_id == university_id).order_by(RetentionPolicy.created_at.desc())
        if record_category:
            query = query.where(RetentionPolicy.record_category.ilike(f"%{record_category.strip()}%"))
        if department_id:
            query = query.where(RetentionPolicy.department_id == department_id)
        if is_enabled is not None:
            query = query.where(RetentionPolicy.is_enabled == is_enabled)
        return paginate(query, db, params)

    @staticmethod
    def update_policy(
        db: Session,
        university_id: uuid.UUID,
        policy_id: uuid.UUID,
        data: RetentionPolicyUpdate,
    ) -> RetentionPolicy:
        policy = RetentionPolicyService.get_policy(db, university_id, policy_id)
        if data.department_id is not None and data.department_id != policy.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            policy.department_id = data.department_id

        if data.retention_days is not None:
            policy.retention_days = data.retention_days
        if data.post_retention_action is not None:
            policy.post_retention_action = data.post_retention_action
        if data.is_enabled is not None:
            policy.is_enabled = data.is_enabled

        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def delete_policy(db: Session, university_id: uuid.UUID, policy_id: uuid.UUID) -> None:
        policy = RetentionPolicyService.get_policy(db, university_id, policy_id)
        db.delete(policy)
        db.commit()

