"""FastAPI routes for publications, authors, project links, and reviews."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.publications import (
    PublicationAuthorController,
    PublicationController,
    PublicationProjectController,
    PublicationReviewController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context
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

publications_router = APIRouter(prefix="/publications", tags=["Publications"])


# --- PUBLICATIONS ---
@publications_router.post("", response_model=PublicationRead, status_code=status.HTTP_201_CREATED)
def create_publication(
    data: PublicationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.create_publication(db, tenant, data)


@publications_router.get("", response_model=PaginatedResponse[PublicationRead])
def list_publications(
    params: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.list_publications(db, tenant, params, status=status, search=search)


@publications_router.get("/{publication_id}", response_model=PublicationRead)
def get_publication(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.get_publication(db, tenant, publication_id)


@publications_router.patch("/{publication_id}", response_model=PublicationRead)
@publications_router.put("/{publication_id}", response_model=PublicationRead)
def update_publication(
    publication_id: uuid.UUID,
    data: PublicationUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.update_publication(db, tenant, publication_id, data)


@publications_router.delete("/{publication_id}", status_code=status.HTTP_200_OK)
def delete_publication(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.delete_publication(db, tenant, publication_id)


@publications_router.post("/{publication_id}/verify", response_model=PublicationRead)
def verify_publication(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationController.verify_publication(db, tenant, publication_id)


# --- AUTHORS ---
@publications_router.post("/{publication_id}/authors", response_model=PublicationAuthorRead, status_code=status.HTTP_201_CREATED)
def add_author(
    publication_id: uuid.UUID,
    data: PublicationAuthorCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationAuthorController.add_author(db, tenant, publication_id, data)


@publications_router.get("/{publication_id}/authors", response_model=list[PublicationAuthorRead])
def list_authors(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationAuthorController.list_authors(db, tenant, publication_id)


@publications_router.delete("/{publication_id}/authors/{author_id}", status_code=status.HTTP_200_OK)
def remove_author(
    publication_id: uuid.UUID,
    author_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationAuthorController.remove_author(db, tenant, publication_id, author_id)


# --- PROJECTS ---
@publications_router.post("/{publication_id}/projects", response_model=PublicationProjectRead, status_code=status.HTTP_201_CREATED)
def link_project(
    publication_id: uuid.UUID,
    data: PublicationProjectCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationProjectController.link_project(db, tenant, publication_id, data)


@publications_router.get("/{publication_id}/projects", response_model=list[PublicationProjectRead])
def list_projects(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationProjectController.list_projects(db, tenant, publication_id)


@publications_router.delete("/{publication_id}/projects/{project_id}", status_code=status.HTTP_200_OK)
def unlink_project(
    publication_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationProjectController.unlink_project(db, tenant, publication_id, project_id)


# --- REVIEWS ---
@publications_router.post("/{publication_id}/reviews", response_model=PublicationReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    publication_id: uuid.UUID,
    data: PublicationReviewCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationReviewController.create_review(db, tenant, publication_id, data)


@publications_router.get("/{publication_id}/reviews", response_model=list[PublicationReviewRead])
def list_reviews(
    publication_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return PublicationReviewController.list_reviews(db, tenant, publication_id)

