"""PMS SQLAlchemy models for this domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin


def _uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class StoredFile(Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        ForeignKeyConstraint(["uploader_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_stored_files_uploader_membership"),
        UniqueConstraint("id", "university_id", name="uq_stored_files_id_university"),
        CheckConstraint("file_size_bytes >= 0", name="ck_stored_files_size"),
        Index("ix_stored_files_uploader_created", "uploader_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    uploader: Mapped["User"] = relationship()
    attachments: Mapped[list["DocumentAttachment"]] = relationship(back_populates="stored_file", passive_deletes=True, overlaps="proposal,project,progress_report,grant_application")

class DocumentAttachment(Base):
    __tablename__ = "document_attachments"
    __table_args__ = (
        ForeignKeyConstraint(["stored_file_id", "university_id"], ["stored_files.id", "stored_files.university_id"], ondelete="RESTRICT", name="fk_document_attachments_file_university"),
        ForeignKeyConstraint(["proposal_id", "university_id"], ["research_proposals.id", "research_proposals.university_id"], ondelete="RESTRICT", name="fk_document_attachments_proposal_university"),
        ForeignKeyConstraint(["project_id", "university_id"], ["research_projects.id", "research_projects.university_id"], ondelete="RESTRICT", name="fk_document_attachments_project_university"),
        ForeignKeyConstraint(["progress_report_id", "university_id"], ["progress_reports.id", "progress_reports.university_id"], ondelete="RESTRICT", name="fk_document_attachments_report_university"),
        ForeignKeyConstraint(["grant_application_id", "university_id"], ["grant_applications.id", "grant_applications.university_id"], ondelete="RESTRICT", name="fk_document_attachments_application_university"),
        ForeignKeyConstraint(["uploader_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_document_attachments_uploader_membership"),
        CheckConstraint("num_nonnulls(proposal_id, project_id, progress_report_id, grant_application_id) = 1", name="ck_document_attachments_one_target"),
        Index("ix_document_attachments_target_proposal", "proposal_id"),
        Index("ix_document_attachments_target_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    stored_file_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    proposal_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    progress_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    grant_application_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    stored_file: Mapped["StoredFile"] = relationship(back_populates="attachments", overlaps="proposal,project,progress_report,grant_application")
    proposal: Mapped[Optional["ResearchProposal"]] = relationship(overlaps="stored_file,attachments,project,progress_report,grant_application")
    project: Mapped[Optional["ResearchProject"]] = relationship(overlaps="stored_file,attachments,proposal,progress_report,grant_application")
    progress_report: Mapped[Optional["ProgressReport"]] = relationship(overlaps="stored_file,attachments,proposal,project,grant_application")
    grant_application: Mapped[Optional["GrantApplication"]] = relationship(overlaps="stored_file,attachments,proposal,project,progress_report")
    uploader: Mapped["User"] = relationship()
