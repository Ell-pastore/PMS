"""Service layer for publications, authors, project links, and reviews."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    Publication,
    PublicationAuthor,
    PublicationProject,
    PublicationReview,
    ResearchProject,
    UniversityMembership,
    User,
)
from ..schemas.publications import (
    PublicationAuthorCreate,
    PublicationCreate,
    PublicationProjectCreate,
    PublicationReviewCreate,
    PublicationUpdate,
)


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize DOI to canonical lowercase identifier."""
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.strip() or None


class PublicationService:
    @staticmethod
    def create_publication(
        db: Session,
        university_id: uuid.UUID,
        data: PublicationCreate,
        user_id: int,
    ) -> Publication:
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        norm_doi = normalize_doi(data.doi)
        if norm_doi:
            existing = db.scalar(
                select(Publication).where(Publication.normalized_doi == norm_doi)
            )
            if existing:
                raise DuplicateResourceError(f"A publication with DOI '{data.doi}' already exists")

        pub = Publication(
            university_id=university_id,
            title=data.title.strip(),
            abstract=data.abstract,
            publication_type=data.publication_type,
            doi=data.doi.strip() if data.doi else None,
            normalized_doi=norm_doi,
            journal=data.journal,
            publisher=data.publisher,
            publication_date=data.publication_date,
            volume=data.volume,
            issue=data.issue,
            page_range=data.page_range,
            url=data.url,
            verification_status="draft",
            submitter_id=user_id,
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def get_publication(db: Session, university_id: uuid.UUID, publication_id: uuid.UUID) -> Publication:
        pub = db.scalar(
            select(Publication).where(
                Publication.id == publication_id,
                Publication.university_id == university_id,
            )
        )
        if not pub:
            raise NotFoundError(f"Publication {publication_id} not found in this university")
        return pub

    @staticmethod
    def list_publications(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Publication], int, int]:
        query = select(Publication).where(Publication.university_id == university_id).order_by(Publication.created_at.desc())
        if status:
            query = query.where(Publication.verification_status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Publication.title.ilike(s),
                    Publication.journal.ilike(s),
                    Publication.doi.ilike(s),
                )
            )
        return paginate(query, db, params)

    @staticmethod
    def update_publication(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        data: PublicationUpdate,
    ) -> Publication:
        pub = PublicationService.get_publication(db, university_id, publication_id)

        if data.doi is not None:
            norm_doi = normalize_doi(data.doi)
            if norm_doi != pub.normalized_doi:
                if norm_doi:
                    existing = db.scalar(
                        select(Publication).where(
                            Publication.normalized_doi == norm_doi,
                            Publication.id != pub.id,
                        )
                    )
                    if existing:
                        raise DuplicateResourceError(f"A publication with DOI '{data.doi}' already exists")
                pub.doi = data.doi.strip() if data.doi else None
                pub.normalized_doi = norm_doi

        if data.title is not None:
            pub.title = data.title.strip()
        if data.abstract is not None:
            pub.abstract = data.abstract
        if data.publication_type is not None:
            pub.publication_type = data.publication_type
        if data.journal is not None:
            pub.journal = data.journal
        if data.publisher is not None:
            pub.publisher = data.publisher
        if data.publication_date is not None:
            pub.publication_date = data.publication_date
        if data.volume is not None:
            pub.volume = data.volume
        if data.issue is not None:
            pub.issue = data.issue
        if data.page_range is not None:
            pub.page_range = data.page_range
        if data.url is not None:
            pub.url = data.url
        if data.verification_status is not None:
            pub.verification_status = data.verification_status

        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def delete_publication(db: Session, university_id: uuid.UUID, publication_id: uuid.UUID) -> None:
        pub = PublicationService.get_publication(db, university_id, publication_id)
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(PublicationAuthor).where(PublicationAuthor.publication_id == pub.id)):
            blockers.append("authors")
        if db.scalar(select(func.count()).select_from(PublicationProject).where(PublicationProject.publication_id == pub.id)):
            blockers.append("linked projects")
        if db.scalar(select(func.count()).select_from(PublicationReview).where(PublicationReview.publication_id == pub.id)):
            blockers.append("reviews")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete publication with existing {', '.join(blockers)}. Remove them first."
            )
        db.delete(pub)
        db.commit()

    @staticmethod
    def verify_publication(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        verifier_id: int,
    ) -> Publication:
        pub = PublicationService.get_publication(db, university_id, publication_id)
        verifier_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == verifier_id,
            )
        )
        if not verifier_membership:
            raise ForeignKeyViolationError(f"Verifier {verifier_id} has no membership in this university")

        pub.verifier_id = verifier_id
        pub.verified_at = datetime.now(timezone.utc)
        pub.verification_status = "verified"
        db.commit()
        db.refresh(pub)
        return pub


class PublicationAuthorService:
    @staticmethod
    def add_author(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        data: PublicationAuthorCreate,
    ) -> PublicationAuthor:
        PublicationService.get_publication(db, university_id, publication_id)

        if data.internal_user_id:
            user_membership = db.scalar(
                select(UniversityMembership).where(
                    UniversityMembership.university_id == university_id,
                    UniversityMembership.user_id == data.internal_user_id,
                )
            )
            if not user_membership:
                raise ForeignKeyViolationError(f"Author user {data.internal_user_id} has no membership in this university")

        # Unique author order per publication
        existing_order = db.scalar(
            select(PublicationAuthor).where(
                PublicationAuthor.publication_id == publication_id,
                PublicationAuthor.author_order == data.author_order,
            )
        )
        if existing_order:
            raise DuplicateResourceError(f"Author with order {data.author_order} already exists on this publication")

        if data.is_corresponding:
            existing_corr = db.scalar(
                select(PublicationAuthor).where(
                    PublicationAuthor.publication_id == publication_id,
                    PublicationAuthor.is_corresponding.is_(True),
                )
            )
            if existing_corr:
                raise DuplicateResourceError("A corresponding author is already designated for this publication")

        author = PublicationAuthor(
            university_id=university_id,
            publication_id=publication_id,
            internal_user_id=data.internal_user_id,
            external_author_name=data.external_author_name,
            external_affiliation=data.external_affiliation,
            author_order=data.author_order,
            is_corresponding=data.is_corresponding,
        )
        db.add(author)
        db.commit()
        db.refresh(author)
        return author

    @staticmethod
    def list_authors(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
    ) -> Sequence[PublicationAuthor]:
        PublicationService.get_publication(db, university_id, publication_id)
        return db.scalars(
            select(PublicationAuthor)
            .where(
                PublicationAuthor.publication_id == publication_id,
                PublicationAuthor.university_id == university_id,
            )
            .order_by(PublicationAuthor.author_order.asc())
        ).all()

    @staticmethod
    def remove_author(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        author_id: uuid.UUID,
    ) -> None:
        author = db.scalar(
            select(PublicationAuthor).where(
                PublicationAuthor.id == author_id,
                PublicationAuthor.publication_id == publication_id,
                PublicationAuthor.university_id == university_id,
            )
        )
        if not author:
            raise NotFoundError(f"Author {author_id} not found on this publication")
        db.delete(author)
        db.commit()


class PublicationProjectService:
    @staticmethod
    def link_project(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        data: PublicationProjectCreate,
    ) -> PublicationProject:
        PublicationService.get_publication(db, university_id, publication_id)

        project = db.scalar(
            select(ResearchProject).where(
                ResearchProject.id == data.project_id,
                ResearchProject.university_id == university_id,
            )
        )
        if not project:
            raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        existing = db.scalar(
            select(PublicationProject).where(
                PublicationProject.publication_id == publication_id,
                PublicationProject.project_id == data.project_id,
            )
        )
        if existing:
            raise DuplicateResourceError("Publication is already linked to this research project")

        pp = PublicationProject(
            university_id=university_id,
            publication_id=publication_id,
            project_id=data.project_id,
        )
        db.add(pp)
        db.commit()
        db.refresh(pp)
        return pp

    @staticmethod
    def list_projects(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
    ) -> Sequence[PublicationProject]:
        PublicationService.get_publication(db, university_id, publication_id)
        return db.scalars(
            select(PublicationProject).where(
                PublicationProject.publication_id == publication_id,
                PublicationProject.university_id == university_id,
            )
        ).all()

    @staticmethod
    def unlink_project(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        link = db.scalar(
            select(PublicationProject).where(
                PublicationProject.publication_id == publication_id,
                PublicationProject.project_id == project_id,
                PublicationProject.university_id == university_id,
            )
        )
        if not link:
            raise NotFoundError(f"Project link {project_id} not found on this publication")
        db.delete(link)
        db.commit()


class PublicationReviewService:
    @staticmethod
    def create_review(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
        data: PublicationReviewCreate,
        reviewer_id: int,
    ) -> PublicationReview:
        pub = PublicationService.get_publication(db, university_id, publication_id)

        reviewer_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == reviewer_id,
            )
        )
        if not reviewer_membership:
            raise ForeignKeyViolationError(f"Reviewer {reviewer_id} has no membership in this university")

        rev = PublicationReview(
            university_id=university_id,
            publication_id=publication_id,
            reviewer_id=reviewer_id,
            decision=data.decision,
            comments=data.comments,
        )
        db.add(rev)

        if data.decision == "verified":
            pub.verification_status = "verified"
            pub.verifier_id = reviewer_id
            pub.verified_at = datetime.now(timezone.utc)
        elif data.decision == "rejected":
            pub.verification_status = "rejected"
        elif data.decision == "revision_requested":
            pub.verification_status = "revision_requested"

        db.commit()
        db.refresh(rev)
        return rev

    @staticmethod
    def list_reviews(
        db: Session,
        university_id: uuid.UUID,
        publication_id: uuid.UUID,
    ) -> Sequence[PublicationReview]:
        PublicationService.get_publication(db, university_id, publication_id)
        return db.scalars(
            select(PublicationReview)
            .where(
                PublicationReview.publication_id == publication_id,
                PublicationReview.university_id == university_id,
            )
            .order_by(PublicationReview.reviewed_at.desc())
        ).all()

