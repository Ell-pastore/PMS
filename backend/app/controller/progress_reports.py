"""Controllers for progress reports, reviews, comments, and student activity."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
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
from ..services.progress_reports import (
    ProgressReportReviewService,
    ProgressReportService,
    ProjectCommentService,
    StudentActivityService,
)


class ProgressReportController:
    @staticmethod
    def create_report(
        db: Session,
        tenant: TenantContext,
        data: ProgressReportCreate,
    ) -> ProgressReportRead:
        report = ProgressReportService.create_report(db, tenant.university_id, data, tenant.user.id)
        return ProgressReportRead.model_validate(report)

    @staticmethod
    def get_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> ProgressReportRead:
        report = ProgressReportService.get_report(db, tenant.university_id, report_id)
        return ProgressReportRead.model_validate(report)

    @staticmethod
    def list_reports(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        project_id: Optional[uuid.UUID] = None,
        milestone_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ProgressReportRead]:
        items, total, total_pages = ProgressReportService.list_reports(
            db,
            tenant.university_id,
            params,
            project_id=project_id,
            milestone_id=milestone_id,
            status=status,
            search=search,
        )
        return PaginatedResponse(
            items=[ProgressReportRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
        data: ProgressReportUpdate,
    ) -> ProgressReportRead:
        report = ProgressReportService.update_report(db, tenant.university_id, report_id, data)
        return ProgressReportRead.model_validate(report)

    @staticmethod
    def delete_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> dict[str, str]:
        ProgressReportService.delete_report(db, tenant.university_id, report_id)
        return {"status": "success", "message": f"Progress report {report_id} deleted"}

    @staticmethod
    def submit_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> ProgressReportRead:
        report = ProgressReportService.submit_report(db, tenant.university_id, report_id)
        return ProgressReportRead.model_validate(report)


class ProgressReportReviewController:
    @staticmethod
    def create_review(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
        data: ProgressReportReviewCreate,
    ) -> ProgressReportReviewRead:
        review = ProgressReportReviewService.create_review(
            db, tenant.university_id, report_id, data, tenant.user.id
        )
        return ProgressReportReviewRead.model_validate(review)

    @staticmethod
    def list_reviews(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> list[ProgressReportReviewRead]:
        items = ProgressReportReviewService.list_reviews(db, tenant.university_id, report_id)
        return [ProgressReportReviewRead.model_validate(item) for item in items]


class ProjectCommentController:
    @staticmethod
    def create_comment(
        db: Session,
        tenant: TenantContext,
        data: ProjectCommentCreate,
    ) -> ProjectCommentRead:
        comment = ProjectCommentService.create_comment(db, tenant.university_id, data, tenant.user.id)
        return ProjectCommentRead.model_validate(comment)

    @staticmethod
    def get_comment(
        db: Session,
        tenant: TenantContext,
        comment_id: uuid.UUID,
    ) -> ProjectCommentRead:
        comment = ProjectCommentService.get_comment(db, tenant.university_id, comment_id)
        return ProjectCommentRead.model_validate(comment)

    @staticmethod
    def list_comments(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        project_id: Optional[uuid.UUID] = None,
        milestone_id: Optional[uuid.UUID] = None,
        progress_report_id: Optional[uuid.UUID] = None,
    ) -> PaginatedResponse[ProjectCommentRead]:
        items, total, total_pages = ProjectCommentService.list_comments(
            db,
            tenant.university_id,
            params,
            project_id=project_id,
            milestone_id=milestone_id,
            progress_report_id=progress_report_id,
        )
        return PaginatedResponse(
            items=[ProjectCommentRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_comment(
        db: Session,
        tenant: TenantContext,
        comment_id: uuid.UUID,
        data: ProjectCommentUpdate,
    ) -> ProjectCommentRead:
        comment = ProjectCommentService.update_comment(db, tenant.university_id, comment_id, data)
        return ProjectCommentRead.model_validate(comment)

    @staticmethod
    def delete_comment(
        db: Session,
        tenant: TenantContext,
        comment_id: uuid.UUID,
    ) -> dict[str, str]:
        ProjectCommentService.delete_comment(db, tenant.university_id, comment_id)
        return {"status": "success", "message": f"Comment {comment_id} deleted"}


class StudentActivityController:
    @staticmethod
    def record_activity(
        db: Session,
        tenant: TenantContext,
        data: StudentActivityCreate,
    ) -> StudentActivityRead:
        activity = StudentActivityService.record_activity(db, tenant.university_id, data)
        return StudentActivityRead.model_validate(activity)

    @staticmethod
    def get_activity(
        db: Session,
        tenant: TenantContext,
        activity_id: uuid.UUID,
    ) -> StudentActivityRead:
        act = StudentActivityService.get_activity(db, tenant.university_id, activity_id)
        return StudentActivityRead.model_validate(act)

    @staticmethod
    def list_activities(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        student_id: Optional[int] = None,
        project_id: Optional[uuid.UUID] = None,
        activity_type: Optional[str] = None,
    ) -> PaginatedResponse[StudentActivityRead]:
        items, total, total_pages = StudentActivityService.list_activities(
            db,
            tenant.university_id,
            params,
            student_id=student_id,
            project_id=project_id,
            activity_type=activity_type,
        )
        return PaginatedResponse(
            items=[StudentActivityRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_activity(
        db: Session,
        tenant: TenantContext,
        activity_id: uuid.UUID,
    ) -> dict[str, str]:
        StudentActivityService.delete_activity(db, tenant.university_id, activity_id)
        return {"status": "success", "message": f"Activity {activity_id} deleted"}

