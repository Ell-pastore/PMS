"""Service layer for grant opportunities, applications, awards, expenditures, and reports."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import delete, func, or_, select
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
    GrantApplication,
    GrantApplicationParticipant,
    GrantApplicationReview,
    GrantApplicationStatusHistory,
    GrantAward,
    GrantExpenditure,
    GrantOpportunity,
    GrantProgressReport,
    GrantProjectAllocation,
    ResearchProject,
    UniversityMembership,
    User,
)
from ..schemas.grants import (
    GrantAllocationCreate,
    GrantApplicationCreate,
    GrantApplicationParticipantCreate,
    GrantApplicationReviewCreate,
    GrantApplicationUpdate,
    GrantAwardCreate,
    GrantAwardUpdate,
    GrantExpenditureCreate,
    GrantExpenditureUpdate,
    GrantOpportunityCreate,
    GrantOpportunityUpdate,
    GrantProgressReportCreate,
    GrantProgressReportUpdate,
)


class GrantOpportunityService:
    @staticmethod
    def create_opportunity(
        db: Session,
        university_id: uuid.UUID,
        data: GrantOpportunityCreate,
        user_id: int,
    ) -> GrantOpportunity:
        if data.application_closes_at < data.application_opens_at:
            raise InvalidInputError("Application close time must be on or after open time")
        if data.max_funding_amount is not None and data.max_funding_amount < data.min_funding_amount:
            raise InvalidInputError("Max funding amount must be on or greater than min funding amount")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        opp = GrantOpportunity(
            university_id=university_id,
            title=data.title.strip(),
            description=data.description,
            funding_organization=data.funding_organization.strip(),
            eligibility_criteria=data.eligibility_criteria,
            application_opens_at=data.application_opens_at,
            application_closes_at=data.application_closes_at,
            min_funding_amount=data.min_funding_amount,
            max_funding_amount=data.max_funding_amount,
            currency=data.currency.upper(),
            status=data.status or "draft",
            created_by_id=user_id,
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)
        return opp

    @staticmethod
    def get_opportunity(db: Session, university_id: uuid.UUID, opportunity_id: uuid.UUID) -> GrantOpportunity:
        opp = db.scalar(
            select(GrantOpportunity).where(
                GrantOpportunity.id == opportunity_id,
                GrantOpportunity.university_id == university_id,
            )
        )
        if not opp:
            raise NotFoundError(f"Grant opportunity {opportunity_id} not found in this university")
        return opp

    @staticmethod
    def list_opportunities(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[GrantOpportunity], int, int]:
        query = select(GrantOpportunity).where(GrantOpportunity.university_id == university_id).order_by(GrantOpportunity.created_at.desc())
        if status:
            query = query.where(GrantOpportunity.status == status)
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(GrantOpportunity.title.ilike(s), GrantOpportunity.funding_organization.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def update_opportunity(
        db: Session,
        university_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        data: GrantOpportunityUpdate,
    ) -> GrantOpportunity:
        opp = GrantOpportunityService.get_opportunity(db, university_id, opportunity_id)

        target_opens = data.application_opens_at or opp.application_opens_at
        target_closes = data.application_closes_at or opp.application_closes_at
        if target_closes < target_opens:
            raise InvalidInputError("Application close time must be on or after open time")

        target_min = data.min_funding_amount if data.min_funding_amount is not None else opp.min_funding_amount
        target_max = data.max_funding_amount if data.max_funding_amount is not None else opp.max_funding_amount
        if target_max is not None and target_max < target_min:
            raise InvalidInputError("Max funding amount must be on or greater than min funding amount")

        if data.title is not None:
            opp.title = data.title.strip()
        if data.description is not None:
            opp.description = data.description
        if data.funding_organization is not None:
            opp.funding_organization = data.funding_organization.strip()
        if data.eligibility_criteria is not None:
            opp.eligibility_criteria = data.eligibility_criteria
        if data.application_opens_at is not None:
            opp.application_opens_at = data.application_opens_at
        if data.application_closes_at is not None:
            opp.application_closes_at = data.application_closes_at
        if data.min_funding_amount is not None:
            opp.min_funding_amount = data.min_funding_amount
        if data.max_funding_amount is not None:
            opp.max_funding_amount = data.max_funding_amount
        if data.currency is not None:
            opp.currency = data.currency.upper()
        if data.status is not None:
            opp.status = data.status

        db.commit()
        db.refresh(opp)
        return opp

    @staticmethod
    def delete_opportunity(db: Session, university_id: uuid.UUID, opportunity_id: uuid.UUID) -> None:
        opp = GrantOpportunityService.get_opportunity(db, university_id, opportunity_id)
        referenced = db.scalar(
            select(GrantApplication.id).where(GrantApplication.opportunity_id == opportunity_id).limit(1)
        )
        if referenced:
            raise SpecializedOperationError(
                "Cannot delete grant opportunity: grant applications reference it. "
                "Delete or reassign the applications first."
            )
        db.delete(opp)
        db.commit()


class GrantApplicationService:
    @staticmethod
    def create_application(
        db: Session,
        university_id: uuid.UUID,
        data: GrantApplicationCreate,
        user_id: int,
    ) -> GrantApplication:
        GrantOpportunityService.get_opportunity(db, university_id, data.opportunity_id)

        if data.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        app = GrantApplication(
            university_id=university_id,
            opportunity_id=data.opportunity_id,
            applicant_id=user_id,
            project_id=data.project_id,
            title=data.title.strip(),
            proposal=data.proposal,
            requested_amount=data.requested_amount,
            currency=data.currency.upper(),
            status="draft",
        )
        db.add(app)
        db.flush()

        history = GrantApplicationStatusHistory(
            university_id=university_id,
            application_id=app.id,
            previous_status=None,
            new_status="draft",
            actor_id=user_id,
            reason="Application created",
        )
        db.add(history)
        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def get_application(db: Session, university_id: uuid.UUID, application_id: uuid.UUID) -> GrantApplication:
        app = db.scalar(
            select(GrantApplication).where(
                GrantApplication.id == application_id,
                GrantApplication.university_id == university_id,
            )
        )
        if not app:
            raise NotFoundError(f"Grant application {application_id} not found in this university")
        return app

    @staticmethod
    def list_applications(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        opportunity_id: Optional[uuid.UUID] = None,
        applicant_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[GrantApplication], int, int]:
        query = select(GrantApplication).where(GrantApplication.university_id == university_id).order_by(GrantApplication.created_at.desc())
        if opportunity_id:
            query = query.where(GrantApplication.opportunity_id == opportunity_id)
        if applicant_id:
            query = query.where(GrantApplication.applicant_id == applicant_id)
        if status:
            query = query.where(GrantApplication.status == status)
        if search:
            query = query.where(GrantApplication.title.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_application(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
        data: GrantApplicationUpdate,
    ) -> GrantApplication:
        app = GrantApplicationService.get_application(db, university_id, application_id)
        if app.status != "draft":
            raise SpecializedOperationError(f"Cannot update grant application in status '{app.status}'. Only draft applications can be edited.")

        if data.project_id is not None and data.project_id != app.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")
            app.project_id = data.project_id

        if data.title is not None:
            app.title = data.title.strip()
        if data.proposal is not None:
            app.proposal = data.proposal
        if data.requested_amount is not None:
            app.requested_amount = data.requested_amount
        if data.currency is not None:
            app.currency = data.currency.upper()

        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def delete_application(db: Session, university_id: uuid.UUID, application_id: uuid.UUID) -> None:
        app = GrantApplicationService.get_application(db, university_id, application_id)
        if app.status != "draft":
            raise SpecializedOperationError(f"Cannot delete grant application in status '{app.status}'. Only draft applications can be deleted.")

        # Guard against deleting an application that still has user-created
        # data or has been awarded (RESTRICT foreign keys would otherwise
        # surface as a raw integrity error).
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(GrantAward).where(GrantAward.application_id == app.id)):
            blockers.append("an award")
        if db.scalar(select(func.count()).select_from(GrantApplicationParticipant).where(GrantApplicationParticipant.application_id == app.id)):
            blockers.append("participants")
        if db.scalar(select(func.count()).select_from(GrantApplicationReview).where(GrantApplicationReview.application_id == app.id)):
            blockers.append("reviews")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete grant application with existing {', '.join(blockers)}. Remove them first."
            )

        # Cascade the application's own status history rows (written
        # automatically at creation), then delete in a single transaction.
        db.execute(
            delete(GrantApplicationStatusHistory).where(GrantApplicationStatusHistory.application_id == app.id)
        )
        db.delete(app)
        db.commit()

    @staticmethod
    def submit_application(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
        user_id: int,
    ) -> GrantApplication:
        app = GrantApplicationService.get_application(db, university_id, application_id)
        if app.status != "draft":
            raise SpecializedOperationError(f"Cannot submit application currently in '{app.status}' state.")

        prev_status = app.status
        app.status = "submitted"
        app.submitted_at = datetime.now(timezone.utc)

        history = GrantApplicationStatusHistory(
            university_id=university_id,
            application_id=app.id,
            previous_status=prev_status,
            new_status="submitted",
            actor_id=user_id,
            reason="Application submitted",
        )
        db.add(history)
        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def add_participant(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
        data: GrantApplicationParticipantCreate,
    ) -> GrantApplicationParticipant:
        GrantApplicationService.get_application(db, university_id, application_id)

        user_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.user_id,
            )
        )
        if not user_membership:
            raise ForeignKeyViolationError(f"User {data.user_id} has no membership in this university")

        existing = db.scalar(
            select(GrantApplicationParticipant).where(
                GrantApplicationParticipant.application_id == application_id,
                GrantApplicationParticipant.user_id == data.user_id,
            )
        )
        if existing:
            raise DuplicateResourceError(f"User {data.user_id} is already a participant on this application")

        part = GrantApplicationParticipant(
            university_id=university_id,
            application_id=application_id,
            user_id=data.user_id,
            participation_role=data.participation_role,
        )
        db.add(part)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def remove_participant(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> None:
        part = db.scalar(
            select(GrantApplicationParticipant).where(
                GrantApplicationParticipant.id == participant_id,
                GrantApplicationParticipant.application_id == application_id,
                GrantApplicationParticipant.university_id == university_id,
            )
        )
        if not part:
            raise NotFoundError(f"Participant {participant_id} not found on this grant application")
        db.delete(part)
        db.commit()

    @staticmethod
    def list_participants(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> Sequence[GrantApplicationParticipant]:
        GrantApplicationService.get_application(db, university_id, application_id)
        return db.scalars(
            select(GrantApplicationParticipant).where(
                GrantApplicationParticipant.application_id == application_id,
                GrantApplicationParticipant.university_id == university_id,
            )
        ).all()

    @staticmethod
    def create_review(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
        data: GrantApplicationReviewCreate,
        reviewer_id: int,
    ) -> GrantApplicationReview:
        app = GrantApplicationService.get_application(db, university_id, application_id)

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == reviewer_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"Reviewer {reviewer_id} has no membership in this university")

        review = GrantApplicationReview(
            university_id=university_id,
            application_id=application_id,
            reviewer_id=reviewer_id,
            decision=data.decision,
            recommended_amount=data.recommended_amount,
            comments=data.comments,
        )
        db.add(review)

        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "revision_requested": "under_review",
        }
        if data.decision in status_map:
            prev_status = app.status
            app.status = status_map[data.decision]
            history = GrantApplicationStatusHistory(
                university_id=university_id,
                application_id=app.id,
                previous_status=prev_status,
                new_status=app.status,
                actor_id=reviewer_id,
                reason=f"Review decision: {data.decision}",
            )
            db.add(history)

        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_reviews(
        db: Session,
        university_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> Sequence[GrantApplicationReview]:
        GrantApplicationService.get_application(db, university_id, application_id)
        return db.scalars(
            select(GrantApplicationReview)
            .where(
                GrantApplicationReview.application_id == application_id,
                GrantApplicationReview.university_id == university_id,
            )
            .order_by(GrantApplicationReview.reviewed_at.desc())
        ).all()


class GrantAwardService:
    @staticmethod
    def create_award(
        db: Session,
        university_id: uuid.UUID,
        data: GrantAwardCreate,
        approver_id: int,
    ) -> GrantAward:
        app = GrantApplicationService.get_application(db, university_id, data.application_id)

        existing_app_award = db.scalar(
            select(GrantAward).where(GrantAward.application_id == data.application_id)
        )
        if existing_app_award:
            raise DuplicateResourceError(f"Award already issued for application {data.application_id}")

        existing_ref = db.scalar(
            select(GrantAward).where(GrantAward.award_reference == data.award_reference.strip())
        )
        if existing_ref:
            raise DuplicateResourceError(f"Award reference '{data.award_reference}' already exists")

        if data.award_end_date < data.award_start_date:
            raise InvalidInputError("Award end date must be on or after start date")

        approver_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == approver_id,
            )
        )
        if not approver_membership:
            raise ForeignKeyViolationError(f"Approver {approver_id} has no membership in this university")

        award = GrantAward(
            university_id=university_id,
            application_id=data.application_id,
            award_reference=data.award_reference.strip(),
            awarded_amount=data.awarded_amount,
            currency=data.currency.upper(),
            award_start_date=data.award_start_date,
            award_end_date=data.award_end_date,
            status=data.status or "active",
            approved_by_id=approver_id,
        )
        db.add(award)
        app.status = "approved"

        db.commit()
        db.refresh(award)
        return award

    @staticmethod
    def get_award(db: Session, university_id: uuid.UUID, award_id: uuid.UUID) -> GrantAward:
        award = db.scalar(
            select(GrantAward).where(
                GrantAward.id == award_id,
                GrantAward.university_id == university_id,
            )
        )
        if not award:
            raise NotFoundError(f"Grant award {award_id} not found in this university")
        return award

    @staticmethod
    def list_awards(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        application_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[GrantAward], int, int]:
        query = select(GrantAward).where(GrantAward.university_id == university_id).order_by(GrantAward.created_at.desc())
        if application_id:
            query = query.where(GrantAward.application_id == application_id)
        if status:
            query = query.where(GrantAward.status == status)
        if search:
            query = query.where(GrantAward.award_reference.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_award(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        data: GrantAwardUpdate,
    ) -> GrantAward:
        award = GrantAwardService.get_award(db, university_id, award_id)

        target_start = data.award_start_date or award.award_start_date
        target_end = data.award_end_date or award.award_end_date
        if target_end < target_start:
            raise InvalidInputError("Award end date must be on or after start date")

        if data.award_reference is not None and data.award_reference.strip() != award.award_reference:
            existing = db.scalar(
                select(GrantAward).where(
                    GrantAward.award_reference == data.award_reference.strip(),
                    GrantAward.id != award.id,
                )
            )
            if existing:
                raise DuplicateResourceError(f"Award reference '{data.award_reference}' already exists")
            award.award_reference = data.award_reference.strip()

        if data.awarded_amount is not None:
            award.awarded_amount = data.awarded_amount
        if data.currency is not None:
            award.currency = data.currency.upper()
        if data.award_start_date is not None:
            award.award_start_date = data.award_start_date
        if data.award_end_date is not None:
            award.award_end_date = data.award_end_date
        if data.status is not None:
            award.status = data.status

        db.commit()
        db.refresh(award)
        return award

    @staticmethod
    def delete_award(db: Session, university_id: uuid.UUID, award_id: uuid.UUID) -> None:
        award = GrantAwardService.get_award(db, university_id, award_id)
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(GrantExpenditure).where(GrantExpenditure.award_id == award.id)):
            blockers.append("expenditures")
        if db.scalar(select(func.count()).select_from(GrantProjectAllocation).where(GrantProjectAllocation.award_id == award.id)):
            blockers.append("project allocations")
        if db.scalar(select(func.count()).select_from(GrantProgressReport).where(GrantProgressReport.award_id == award.id)):
            blockers.append("progress reports")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete grant award with existing {', '.join(blockers)}. Remove them first."
            )
        db.delete(award)
        db.commit()


class GrantAllocationService:
    @staticmethod
    def create_allocation(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        data: GrantAllocationCreate,
        user_id: int,
    ) -> GrantProjectAllocation:
        GrantAwardService.get_award(db, university_id, award_id)

        project = db.scalar(
            select(ResearchProject).where(
                ResearchProject.id == data.project_id,
                ResearchProject.university_id == university_id,
            )
        )
        if not project:
            raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        existing = db.scalar(
            select(GrantProjectAllocation).where(
                GrantProjectAllocation.award_id == award_id,
                GrantProjectAllocation.project_id == data.project_id,
            )
        )
        if existing:
            raise DuplicateResourceError(f"Project {data.project_id} already has allocation on this award")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        alloc = GrantProjectAllocation(
            university_id=university_id,
            award_id=award_id,
            project_id=data.project_id,
            allocated_amount=data.allocated_amount,
            currency=data.currency.upper(),
            created_by_id=user_id,
        )
        db.add(alloc)
        db.commit()
        db.refresh(alloc)
        return alloc

    @staticmethod
    def list_allocations(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
    ) -> Sequence[GrantProjectAllocation]:
        GrantAwardService.get_award(db, university_id, award_id)
        return db.scalars(
            select(GrantProjectAllocation).where(
                GrantProjectAllocation.award_id == award_id,
                GrantProjectAllocation.university_id == university_id,
            )
        ).all()

    @staticmethod
    def delete_allocation(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        allocation_id: uuid.UUID,
    ) -> None:
        alloc = db.scalar(
            select(GrantProjectAllocation).where(
                GrantProjectAllocation.id == allocation_id,
                GrantProjectAllocation.award_id == award_id,
                GrantProjectAllocation.university_id == university_id,
            )
        )
        if not alloc:
            raise NotFoundError(f"Allocation {allocation_id} not found on this grant award")
        db.delete(alloc)
        db.commit()


class GrantExpenditureService:
    @staticmethod
    def record_expenditure(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        data: GrantExpenditureCreate,
        user_id: int,
    ) -> GrantExpenditure:
        GrantAwardService.get_award(db, university_id, award_id)

        if data.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        exp = GrantExpenditure(
            university_id=university_id,
            award_id=award_id,
            project_id=data.project_id,
            description=data.description.strip(),
            amount=data.amount,
            currency=data.currency.upper(),
            expenditure_date=data.expenditure_date,
            reference_number=data.reference_number,
            status=data.status or "draft",
            recorded_by_id=user_id,
        )
        db.add(exp)
        db.commit()
        db.refresh(exp)
        return exp

    @staticmethod
    def get_expenditure(
        db: Session,
        university_id: uuid.UUID,
        expenditure_id: uuid.UUID,
    ) -> GrantExpenditure:
        exp = db.scalar(
            select(GrantExpenditure).where(
                GrantExpenditure.id == expenditure_id,
                GrantExpenditure.university_id == university_id,
            )
        )
        if not exp:
            raise NotFoundError(f"Expenditure {expenditure_id} not found in this university")
        return exp

    @staticmethod
    def list_expenditures(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
    ) -> tuple[Sequence[GrantExpenditure], int, int]:
        GrantAwardService.get_award(db, university_id, award_id)
        query = select(GrantExpenditure).where(
            GrantExpenditure.award_id == award_id,
            GrantExpenditure.university_id == university_id,
        ).order_by(GrantExpenditure.expenditure_date.desc())
        if status:
            query = query.where(GrantExpenditure.status == status)
        return paginate(query, db, params)

    @staticmethod
    def update_expenditure(
        db: Session,
        university_id: uuid.UUID,
        expenditure_id: uuid.UUID,
        data: GrantExpenditureUpdate,
    ) -> GrantExpenditure:
        exp = GrantExpenditureService.get_expenditure(db, university_id, expenditure_id)
        if data.project_id is not None and data.project_id != exp.project_id:
            project = db.scalar(
                select(ResearchProject).where(
                    ResearchProject.id == data.project_id,
                    ResearchProject.university_id == university_id,
                )
            )
            if not project:
                raise ForeignKeyViolationError(f"Project {data.project_id} not found in this university")
            exp.project_id = data.project_id

        if data.description is not None:
            exp.description = data.description.strip()
        if data.amount is not None:
            exp.amount = data.amount
        if data.currency is not None:
            exp.currency = data.currency.upper()
        if data.expenditure_date is not None:
            exp.expenditure_date = data.expenditure_date
        if data.reference_number is not None:
            exp.reference_number = data.reference_number
        if data.status is not None:
            exp.status = data.status

        db.commit()
        db.refresh(exp)
        return exp

    @staticmethod
    def delete_expenditure(
        db: Session,
        university_id: uuid.UUID,
        expenditure_id: uuid.UUID,
    ) -> None:
        exp = GrantExpenditureService.get_expenditure(db, university_id, expenditure_id)
        db.delete(exp)
        db.commit()


class GrantProgressReportService:
    @staticmethod
    def create_report(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        data: GrantProgressReportCreate,
        user_id: int,
    ) -> GrantProgressReport:
        GrantAwardService.get_award(db, university_id, award_id)

        if data.period_end < data.period_start:
            raise InvalidInputError("Period end date must be on or after start date")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        rep = GrantProgressReport(
            university_id=university_id,
            award_id=award_id,
            period_start=data.period_start,
            period_end=data.period_end,
            narrative=data.narrative,
            financial_summary=data.financial_summary,
            submitter_id=user_id,
            status="draft",
        )
        db.add(rep)
        db.commit()
        db.refresh(rep)
        return rep

    @staticmethod
    def get_report(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> GrantProgressReport:
        rep = db.scalar(
            select(GrantProgressReport).where(
                GrantProgressReport.id == report_id,
                GrantProgressReport.university_id == university_id,
            )
        )
        if not rep:
            raise NotFoundError(f"Grant progress report {report_id} not found in this university")
        return rep

    @staticmethod
    def list_reports(
        db: Session,
        university_id: uuid.UUID,
        award_id: uuid.UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[GrantProgressReport], int, int]:
        GrantAwardService.get_award(db, university_id, award_id)
        query = select(GrantProgressReport).where(
            GrantProgressReport.award_id == award_id,
            GrantProgressReport.university_id == university_id,
        ).order_by(GrantProgressReport.period_start.desc())
        return paginate(query, db, params)

    @staticmethod
    def update_report(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
        data: GrantProgressReportUpdate,
    ) -> GrantProgressReport:
        rep = GrantProgressReportService.get_report(db, university_id, report_id)

        target_start = data.period_start or rep.period_start
        target_end = data.period_end or rep.period_end
        if target_end < target_start:
            raise InvalidInputError("Period end date must be on or after start date")

        if data.period_start is not None:
            rep.period_start = data.period_start
        if data.period_end is not None:
            rep.period_end = data.period_end
        if data.narrative is not None:
            rep.narrative = data.narrative
        if data.financial_summary is not None:
            rep.financial_summary = data.financial_summary
        if data.status is not None:
            rep.status = data.status

        db.commit()
        db.refresh(rep)
        return rep

    @staticmethod
    def delete_report(
        db: Session,
        university_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> None:
        rep = GrantProgressReportService.get_report(db, university_id, report_id)
        db.delete(rep)
        db.commit()

