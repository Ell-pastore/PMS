"""Service layer for progress reports, reviews, comments, and student activity."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    ForeignKeyViolationError,
    InvalidInputError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    ProgressReport,
    ProgressReportReview,
    ProjectComment,
    ProjectMilestone,
    ResearchProject,
    StudentActivity,
    StudentProfile,
    UniversityMembership,
)
from ..schemas.progress_reports import (
    ProgressReportCreate,
    ProgressReportReviewCreate,
    ProgressReportUpdate,
    ProjectCommentCreate,
    ProjectCommentUpdate,
    StudentActivityCreate,
)


class ProgressReportService:
    @staticmethod
    def create_report(
        db: Session,
        university_id: uuid.UUID,
        data: ProgressReportCreate,
        user_id: int,
    ) -> ProgressReport:
        if data.period_end < data.period_start:
            raise InvalidInputError("Period end date must be on or after period start date")

        project = db.scalar(
            select(ResearchProject).where(
                ResearchProject.id == data.project_id,
                ResearchProject.university_id == university_id,
            )
        )
        if not project:
            raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        if data.milestone_id:
            milestone = db.scalar(
                select(ProjectMilestone).where(
                    ProjectMilestone.id == data.milestone_id,
                    ProjectMilestone.project_id == data.project_id,
                    ProjectMilestone.university_id == university_id,
                )
            )
            if not milestone:
                raise ForeignKeyViolationError(
                    f"Milestone {data.milestone_id} does not belong to project {data.project_id} in this university"
                )

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        report = ProgressReport(
            university_id=university_id,
            project_id=data.project_id,
            milestone_id=data.milestone_id,
            submitter_id=user_id,
            period_start=data.period_start,
            period_end=data.period_end,
            title=data.title.strip(),
            content=data.content,
            challenges=data.challenges,
            next_steps=data.next_steps,
            status="draft",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_report(db: Session, university_id: uuid.UUID, report_id: uuid.UUID) -> ProgressReport:
        report = db.scalar(
            select(ProgressReport).where(
                ProgressReport.id == report_id,
                ProgressReport.university_id == university_id,
            )
        )
        if not report:
            raise NotFoundError(f"Progress report {report_id} not found in this university")
        return report

    @staticmethod
    def list_reports(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        project_id: Optional[uuid.UUID] = None,
        milestone_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[ProgressReport], int, int]:
        query = select(ProgressReport).where(ProgressReport.university_id == university_id).order_by(ProgressReport.created_at.desc())
        if project_id:
            query = query.where(ProgressReport.project_id == project_id)
        if milestone_id:
            query = query.where(ProgressReport.milestone_id == milestone_id)
        if status:
            query = query.where(ProgressReport.status == status)
        if search:
            query = query.where(ProgressReport.title.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_report(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
        data: ProgressReportUpdate,
    ) -> ProgressReport:
        report = ProgressReportService.get_report(db, university_id, report_id)
        if report.status not in ("draft", "revision_requested"):
            raise SpecializedOperationError(
                f"Cannot update progress report in status '{report.status}'. Only draft or revision requested reports can be edited."
            )

        target_start = data.period_start or report.period_start
        target_end = data.period_end or report.period_end
        if target_end < target_start:
            raise InvalidInputError("Period end date must be on or after period start date")

        if data.milestone_id is not None and data.milestone_id != report.milestone_id:
            milestone = db.scalar(
                select(ProjectMilestone).where(
                    ProjectMilestone.id == data.milestone_id,
                    ProjectMilestone.project_id == report.project_id,
                    ProjectMilestone.university_id == university_id,
                )
            )
            if not milestone:
                raise ForeignKeyViolationError(
                    f"Milestone {data.milestone_id} does not belong to project {report.project_id} in this university"
                )
            report.milestone_id = data.milestone_id

        if data.period_start is not None:
            report.period_start = data.period_start
        if data.period_end is not None:
            report.period_end = data.period_end
        if data.title is not None:
            report.title = data.title.strip()
        if data.content is not None:
            report.content = data.content
        if data.challenges is not None:
            report.challenges = data.challenges
        if data.next_steps is not None:
            report.next_steps = data.next_steps

        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def delete_report(db: Session, university_id: uuid.UUID, report_id: uuid.UUID) -> None:
        report = ProgressReportService.get_report(db, university_id, report_id)
        if report.status != "draft":
            raise SpecializedOperationError(f"Cannot delete progress report in status '{report.status}'. Only draft reports can be deleted.")
        db.delete(report)
        db.commit()

    @staticmethod
    def submit_report(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> ProgressReport:
        report = ProgressReportService.get_report(db, university_id, report_id)
        if report.status not in ("draft", "revision_requested"):
            raise SpecializedOperationError(f"Cannot submit progress report currently in '{report.status}' state.")

        report.status = "submitted"
        report.submitted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)
        return report


class ProgressReportReviewService:
    @staticmethod
    def create_review(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
        data: ProgressReportReviewCreate,
        reviewer_id: int,
    ) -> ProgressReportReview:
        report = ProgressReportService.get_report(db, university_id, report_id)

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == reviewer_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"Reviewer {reviewer_id} has no membership in this university")

        review = ProgressReportReview(
            university_id=university_id,
            report_id=report_id,
            reviewer_id=reviewer_id,
            decision=data.decision,
            feedback=data.feedback,
        )
        db.add(review)

        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "revision_requested": "revision_requested",
        }
        if data.decision in status_map:
            report.status = status_map[data.decision]

        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_reviews(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> Sequence[ProgressReportReview]:
        ProgressReportService.get_report(db, university_id, report_id)
        return db.scalars(
            select(ProgressReportReview)
            .where(
                ProgressReportReview.report_id == report_id,
                ProgressReportReview.university_id == university_id,
            )
            .order_by(ProgressReportReview.reviewed_at.desc())
        ).all()


class ProjectCommentService:
    @staticmethod
    def create_comment(
        db: Session,
        university_id: uuid.UUID,
        data: ProjectCommentCreate,
        author_id: int,
    ) -> ProjectComment:
        targets = [data.project_id, data.milestone_id, data.progress_report_id]
        non_null_count = sum(1 for t in targets if t is not None)
        if non_null_count != 1:
            raise InvalidInputError("Exactly one target must be provided: project_id, milestone_id, or progress_report_id")

        if data.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        if data.milestone_id:
            milestone = db.scalar(
                select(ProjectMilestone).where(
                    ProjectMilestone.id == data.milestone_id,
                    ProjectMilestone.university_id == university_id,
                )
            )
            if not milestone:
                raise ForeignKeyViolationError(f"Milestone {data.milestone_id} not found in this university")

        if data.progress_report_id:
            report = db.scalar(
                select(ProgressReport).where(
                    ProgressReport.id == data.progress_report_id,
                    ProgressReport.university_id == university_id,
                )
            )
            if not report:
                raise ForeignKeyViolationError(f"Progress report {data.progress_report_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == author_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"Author {author_id} has no membership in this university")

        comment = ProjectComment(
            university_id=university_id,
            project_id=data.project_id,
            milestone_id=data.milestone_id,
            progress_report_id=data.progress_report_id,
            author_id=author_id,
            body=data.body.strip(),
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def get_comment(db: Session, university_id: uuid.UUID, comment_id: uuid.UUID) -> ProjectComment:
        comment = db.scalar(
            select(ProjectComment).where(
                ProjectComment.id == comment_id,
                ProjectComment.university_id == university_id,
            )
        )
        if not comment:
            raise NotFoundError(f"Comment {comment_id} not found in this university")
        return comment

    @staticmethod
    def list_comments(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        project_id: Optional[uuid.UUID] = None,
        milestone_id: Optional[uuid.UUID] = None,
        progress_report_id: Optional[uuid.UUID] = None,
    ) -> tuple[Sequence[ProjectComment], int, int]:
        query = select(ProjectComment).where(ProjectComment.university_id == university_id).order_by(ProjectComment.created_at.desc())
        if project_id:
            query = query.where(ProjectComment.project_id == project_id)
        if milestone_id:
            query = query.where(ProjectComment.milestone_id == milestone_id)
        if progress_report_id:
            query = query.where(ProjectComment.progress_report_id == progress_report_id)
        return paginate(query, db, params)

    @staticmethod
    def update_comment(
        db: Session,
        university_id: uuid.UUID,
        comment_id: uuid.UUID,
        data: ProjectCommentUpdate,
    ) -> ProjectComment:
        comment = ProjectCommentService.get_comment(db, university_id, comment_id)
        comment.body = data.body.strip()
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def delete_comment(db: Session, university_id: uuid.UUID, comment_id: uuid.UUID) -> None:
        comment = ProjectCommentService.get_comment(db, university_id, comment_id)
        db.delete(comment)
        db.commit()


class StudentActivityService:
    @staticmethod
    def record_activity(
        db: Session,
        university_id: uuid.UUID,
        data: StudentActivityCreate,
    ) -> StudentActivity:
        student = db.scalar(
            select(StudentProfile).where(
                StudentProfile.id == data.student_id,
                StudentProfile.university_id == university_id,
            )
        )
        if not student:
            raise ForeignKeyViolationError(f"Student profile {data.student_id} not found in this university")

        if data.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        activity = StudentActivity(
            university_id=university_id,
            student_id=data.student_id,
            project_id=data.project_id,
            activity_type=data.activity_type,
            activity_metadata=data.activity_metadata,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def list_activities(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        student_id: Optional[int] = None,
        project_id: Optional[uuid.UUID] = None,
        activity_type: Optional[str] = None,
    ) -> tuple[Sequence[StudentActivity], int, int]:
        query = select(StudentActivity).where(StudentActivity.university_id == university_id).order_by(StudentActivity.recorded_at.desc())
        if student_id:
            query = query.where(StudentActivity.student_id == student_id)
        if project_id:
            query = query.where(StudentActivity.project_id == project_id)
        if activity_type:
            query = query.where(StudentActivity.activity_type == activity_type)
        return paginate(query, db, params)

    @staticmethod
    def get_activity(db: Session, university_id: uuid.UUID, activity_id: uuid.UUID) -> StudentActivity:
        act = db.scalar(
            select(StudentActivity).where(
                StudentActivity.id == activity_id,
                StudentActivity.university_id == university_id,
            )
        )
        if not act:
            raise NotFoundError(f"Student activity {activity_id} not found in this university")
        return act

    @staticmethod
    def delete_activity(db: Session, university_id: uuid.UUID, activity_id: uuid.UUID) -> None:
        act = StudentActivityService.get_activity(db, university_id, activity_id)
        db.delete(act)
        db.commit()

