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


class Publication(TimestampMixin, Base):
    __tablename__ = "publications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["submitter_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_publications_submitter_membership",
        ),
        ForeignKeyConstraint(
            ["verifier_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_publications_verifier_membership",
        ),
        UniqueConstraint("id", "university_id", name="uq_publications_id_university"),
        CheckConstraint("verification_status IN ('draft', 'submitted', 'under_verification', 'verified', 'rejected', 'withdrawn')", name="ck_publications_status"),
        Index("uq_publications_normalized_doi", "normalized_doi", unique=True, postgresql_where=text("normalized_doi IS NOT NULL")),
        Index("ix_publications_status_date", "verification_status", "publication_date"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publication_type: Mapped[str] = mapped_column(String(64), nullable=False)
    doi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_doi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    journal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    issue: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    page_range: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    verifier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    submitter: Mapped["User"] = relationship(foreign_keys=[submitter_id])
    verifier: Mapped[Optional["User"]] = relationship(foreign_keys=[verifier_id])
    authors: Mapped[list["PublicationAuthor"]] = relationship(back_populates="publication", passive_deletes=True)
    projects: Mapped[list["PublicationProject"]] = relationship(back_populates="publication", passive_deletes=True, overlaps="project")
    reviews: Mapped[list["PublicationReview"]] = relationship(back_populates="publication", passive_deletes=True)

class PublicationAuthor(Base):
    __tablename__ = "publication_authors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["publication_id", "university_id"],
            ["publications.id", "publications.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_authors_publication_university",
        ),
        ForeignKeyConstraint(
            ["internal_user_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_authors_internal_user_membership",
        ),
        UniqueConstraint("publication_id", "author_order", name="uq_publication_authors_order"),
        Index("uq_publication_authors_corresponding", "publication_id", unique=True, postgresql_where=text("is_corresponding = true")),
        CheckConstraint(
            "(internal_user_id IS NOT NULL AND external_author_name IS NULL) OR (internal_user_id IS NULL AND external_author_name IS NOT NULL)",
            name="ck_publication_authors_identity",
        ),
        CheckConstraint("author_order > 0", name="ck_publication_authors_order_positive"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    internal_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    external_author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_affiliation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_corresponding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    publication: Mapped["Publication"] = relationship(back_populates="authors")
    internal_user: Mapped[Optional["User"]] = relationship(foreign_keys=[internal_user_id])

class PublicationProject(Base):
    __tablename__ = "publication_projects"
    __table_args__ = (
        ForeignKeyConstraint(
            ["publication_id", "university_id"],
            ["publications.id", "publications.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_projects_publication_university",
        ),
        ForeignKeyConstraint(
            ["project_id", "university_id"],
            ["research_projects.id", "research_projects.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_projects_project_university",
        ),
        UniqueConstraint("publication_id", "project_id", name="uq_publication_projects_publication_project"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    publication: Mapped["Publication"] = relationship(back_populates="projects", overlaps="project,publications")
    project: Mapped["ResearchProject"] = relationship(back_populates="publications", overlaps="publication,projects")

class PublicationReview(Base):
    __tablename__ = "publication_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["publication_id", "university_id"],
            ["publications.id", "publications.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_reviews_publication_university",
        ),
        ForeignKeyConstraint(
            ["reviewer_id", "university_id"],
            ["university_memberships.user_id", "university_memberships.university_id"],
            ondelete="RESTRICT",
            name="fk_publication_reviews_reviewer_membership",
        ),
        CheckConstraint("decision IN ('verified', 'rejected', 'revision_requested', 'commented')", name="ck_publication_reviews_decision"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    publication: Mapped["Publication"] = relationship(back_populates="reviews")
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])
