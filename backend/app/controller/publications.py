"""Controllers for publications, authors, project links, and reviews."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.publications import (
    PublicationAuthorCreate,
    PublicationAuthorRead,
    PublicationCreate,
    PublicationProjectCreate,
    PublicationProjectRead,
    PublicationRead,
    PublicationReviewCreate,
    PublicationReviewRead,
    PublicationUpdate,
)
from ..services.publications import (
    PublicationAuthorService,
    PublicationProjectService,
    PublicationReviewService,
    PublicationService,
)


class PublicationController:
    @staticmethod
    def create_publication(
        db: Session,
        tenant: TenantContext,
        data: PublicationCreate,
    ) -> PublicationRead:
        pub = PublicationService.create_publication(db, tenant.university_id, data, tenant.user.id)
        return PublicationRead.model_validate(pub)

    @staticmethod
    def get_publication(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> PublicationRead:
        pub = PublicationService.get_publication(db, tenant.university_id, publication_id)
        return PublicationRead.model_validate(pub)

    @staticmethod
    def list_publications(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[PublicationRead]:
        items, total, total_pages = PublicationService.list_publications(
            db, tenant.university_id, params, status=status, search=search
        )
        return PaginatedResponse(
            items=[PublicationRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_publication(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        data: PublicationUpdate,
    ) -> PublicationRead:
        pub = PublicationService.update_publication(db, tenant.university_id, publication_id, data)
        return PublicationRead.model_validate(pub)

    @staticmethod
    def delete_publication(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> dict[str, str]:
        PublicationService.delete_publication(db, tenant.university_id, publication_id)
        return {"status": "success", "message": f"Publication {publication_id} deleted"}

    @staticmethod
    def verify_publication(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> PublicationRead:
        pub = PublicationService.verify_publication(db, tenant.university_id, publication_id, tenant.user.id)
        return PublicationRead.model_validate(pub)


class PublicationAuthorController:
    @staticmethod
    def add_author(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        data: PublicationAuthorCreate,
    ) -> PublicationAuthorRead:
        author = PublicationAuthorService.add_author(db, tenant.university_id, publication_id, data)
        return PublicationAuthorRead.model_validate(author)

    @staticmethod
    def list_authors(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> list[PublicationAuthorRead]:
        items = PublicationAuthorService.list_authors(db, tenant.university_id, publication_id)
        return [PublicationAuthorRead.model_validate(item) for item in items]

    @staticmethod
    def remove_author(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        author_id: uuid.UUID,
    ) -> dict[str, str]:
        PublicationAuthorService.remove_author(db, tenant.university_id, publication_id, author_id)
        return {"status": "success", "message": f"Author {author_id} removed"}


class PublicationProjectController:
    @staticmethod
    def link_project(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        data: PublicationProjectCreate,
    ) -> PublicationProjectRead:
        link = PublicationProjectService.link_project(db, tenant.university_id, publication_id, data)
        return PublicationProjectRead.model_validate(link)

    @staticmethod
    def list_projects(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> list[PublicationProjectRead]:
        items = PublicationProjectService.list_projects(db, tenant.university_id, publication_id)
        return [PublicationProjectRead.model_validate(item) for item in items]

    @staticmethod
    def unlink_project(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> dict[str, str]:
        PublicationProjectService.unlink_project(db, tenant.university_id, publication_id, project_id)
        return {"status": "success", "message": f"Project link {project_id} removed"}


class PublicationReviewController:
    @staticmethod
    def create_review(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
        data: PublicationReviewCreate,
    ) -> PublicationReviewRead:
        review = PublicationReviewService.create_review(
            db, tenant.university_id, publication_id, data, tenant.user.id
        )
        return PublicationReviewRead.model_validate(review)

    @staticmethod
    def list_reviews(
        db: Session,
        tenant: TenantContext,
        publication_id: uuid.UUID,
    ) -> list[PublicationReviewRead]:
        items = PublicationReviewService.list_reviews(db, tenant.university_id, publication_id)
        return [PublicationReviewRead.model_validate(item) for item in items]

