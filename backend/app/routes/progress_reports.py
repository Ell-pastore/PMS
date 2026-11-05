"""FastAPI routes for progress reports, reviews, comments, and student activity."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.progress_reports import (
    ProgressReportController,
    ProgressReportReviewController,
    ProjectCommentController,
    StudentActivityController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.progress_reports import (
    ProgressReportCreate,
    ProgressReportRead,
    ProgressReportReviewCreate,
    ProgressReportReviewRead,
    ProgressReportUpdate,
    ProjectCommentCreate,
    ProjectCommentRead,
    ProjectCommentUpdate,
    StudentActivityCreate,
    StudentActivityRead,
)

reports_router = APIRouter(prefix="/progress-reports", tags=["Progress Reports"])
comments_router = APIRouter(prefix="/project-comments", tags=["Project Comments"])
activity_router = APIRouter(prefix="/student-activity", tags=["Student Activity"])


# --- PROGRESS REPORTS ---
@reports_router.post("", response_model=ProgressReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    data: ProgressReportCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.create_report(db, tenant, data)


@reports_router.get("", response_model=PaginatedResponse[ProgressReportRead])
def list_reports(
    params: PaginationParams = Depends(),
    project_id: Optional[uuid.UUID] = Query(None),
    milestone_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.list_reports(
        db,
        tenant,
        params,
        project_id=project_id,
        milestone_id=milestone_id,
        status=status,
        search=search,
    )


@reports_router.get("/{report_id}", response_model=ProgressReportRead)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.get_report(db, tenant, report_id)


@reports_router.patch("/{report_id}", response_model=ProgressReportRead)
@reports_router.put("/{report_id}", response_model=ProgressReportRead)
def update_report(
    report_id: uuid.UUID,
    data: ProgressReportUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.update_report(db, tenant, report_id, data)


@reports_router.delete("/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.delete_report(db, tenant, report_id)


@reports_router.post("/{report_id}/submit", response_model=ProgressReportRead)
def submit_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportController.submit_report(db, tenant, report_id)


# Reviews
@reports_router.post("/{report_id}/reviews", response_model=ProgressReportReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    report_id: uuid.UUID,
    data: ProgressReportReviewCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportReviewController.create_review(db, tenant, report_id, data)


@reports_router.get("/{report_id}/reviews", response_model=list[ProgressReportReviewRead])
def list_reviews(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProgressReportReviewController.list_reviews(db, tenant, report_id)


# --- COMMENTS ---
@comments_router.post("", response_model=ProjectCommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    data: ProjectCommentCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectCommentController.create_comment(db, tenant, data)


@comments_router.get("", response_model=PaginatedResponse[ProjectCommentRead])
def list_comments(
    params: PaginationParams = Depends(),
    project_id: Optional[uuid.UUID] = Query(None),
    milestone_id: Optional[uuid.UUID] = Query(None),
    progress_report_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectCommentController.list_comments(
        db,
        tenant,
        params,
        project_id=project_id,
        milestone_id=milestone_id,
        progress_report_id=progress_report_id,
    )


@comments_router.get("/{comment_id}", response_model=ProjectCommentRead)
def get_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectCommentController.get_comment(db, tenant, comment_id)


@comments_router.patch("/{comment_id}", response_model=ProjectCommentRead)
@comments_router.put("/{comment_id}", response_model=ProjectCommentRead)
def update_comment(
    comment_id: uuid.UUID,
    data: ProjectCommentUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectCommentController.update_comment(db, tenant, comment_id, data)


@comments_router.delete("/{comment_id}", status_code=status.HTTP_200_OK)
def delete_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return ProjectCommentController.delete_comment(db, tenant, comment_id)


# --- STUDENT ACTIVITY ---
@activity_router.post("", response_model=StudentActivityRead, status_code=status.HTTP_201_CREATED)
def record_activity(
    data: StudentActivityCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentActivityController.record_activity(db, tenant, data)


@activity_router.get("", response_model=PaginatedResponse[StudentActivityRead])
def list_activities(
    params: PaginationParams = Depends(),
    student_id: Optional[int] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    activity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentActivityController.list_activities(
        db,
        tenant,
        params,
        student_id=student_id,
        project_id=project_id,
        activity_type=activity_type,
    )


@activity_router.get("/{activity_id}", response_model=StudentActivityRead)
def get_activity(
    activity_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentActivityController.get_activity(db, tenant, activity_id)


@activity_router.delete("/{activity_id}", status_code=status.HTTP_200_OK)
def delete_activity(
    activity_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return StudentActivityController.delete_activity(db, tenant, activity_id)

