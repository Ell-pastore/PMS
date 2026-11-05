"""Controllers for grant opportunities, applications, awards, expenditures, and reports."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.grants import (
    GrantAllocationCreate,
    GrantAllocationRead,
    GrantApplicationCreate,
    GrantApplicationParticipantCreate,
    GrantApplicationParticipantRead,
    GrantApplicationRead,
    GrantApplicationReviewCreate,
    GrantApplicationReviewRead,
    GrantApplicationUpdate,
    GrantAwardCreate,
    GrantAwardRead,
    GrantAwardUpdate,
    GrantExpenditureCreate,
    GrantExpenditureRead,
    GrantExpenditureUpdate,
    GrantOpportunityCreate,
    GrantOpportunityRead,
    GrantOpportunityUpdate,
    GrantProgressReportCreate,
    GrantProgressReportRead,
    GrantProgressReportUpdate,
)
from ..services.grants import (
    GrantAllocationService,
    GrantApplicationService,
    GrantAwardService,
    GrantExpenditureService,
    GrantOpportunityService,
    GrantProgressReportService,
)


class GrantOpportunityController:
    @staticmethod
    def create_opportunity(
        db: Session,
        tenant: TenantContext,
        data: GrantOpportunityCreate,
    ) -> GrantOpportunityRead:
        opp = GrantOpportunityService.create_opportunity(db, tenant.university_id, data, tenant.user.id)
        return GrantOpportunityRead.model_validate(opp)

    @staticmethod
    def get_opportunity(
        db: Session,
        tenant: TenantContext,
        opportunity_id: uuid.UUID,
    ) -> GrantOpportunityRead:
        opp = GrantOpportunityService.get_opportunity(db, tenant.university_id, opportunity_id)
        return GrantOpportunityRead.model_validate(opp)

    @staticmethod
    def list_opportunities(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[GrantOpportunityRead]:
        items, total, total_pages = GrantOpportunityService.list_opportunities(
            db, tenant.university_id, params, status=status, search=search
        )
        return PaginatedResponse(
            items=[GrantOpportunityRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_opportunity(
        db: Session,
        tenant: TenantContext,
        opportunity_id: uuid.UUID,
        data: GrantOpportunityUpdate,
    ) -> GrantOpportunityRead:
        opp = GrantOpportunityService.update_opportunity(db, tenant.university_id, opportunity_id, data)
        return GrantOpportunityRead.model_validate(opp)

    @staticmethod
    def delete_opportunity(
        db: Session,
        tenant: TenantContext,
        opportunity_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantOpportunityService.delete_opportunity(db, tenant.university_id, opportunity_id)
        return {"status": "success", "message": f"Grant opportunity {opportunity_id} deleted"}


class GrantApplicationController:
    @staticmethod
    def create_application(
        db: Session,
        tenant: TenantContext,
        data: GrantApplicationCreate,
    ) -> GrantApplicationRead:
        app = GrantApplicationService.create_application(db, tenant.university_id, data, tenant.user.id)
        return GrantApplicationRead.model_validate(app)

    @staticmethod
    def get_application(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
    ) -> GrantApplicationRead:
        app = GrantApplicationService.get_application(db, tenant.university_id, application_id)
        return GrantApplicationRead.model_validate(app)

    @staticmethod
    def list_applications(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        opportunity_id: Optional[uuid.UUID] = None,
        applicant_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[GrantApplicationRead]:
        items, total, total_pages = GrantApplicationService.list_applications(
            db,
            tenant.university_id,
            params,
            opportunity_id=opportunity_id,
            applicant_id=applicant_id,
            status=status,
            search=search,
        )
        return PaginatedResponse(
            items=[GrantApplicationRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_application(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
        data: GrantApplicationUpdate,
    ) -> GrantApplicationRead:
        app = GrantApplicationService.update_application(db, tenant.university_id, application_id, data)
        return GrantApplicationRead.model_validate(app)

    @staticmethod
    def delete_application(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantApplicationService.delete_application(db, tenant.university_id, application_id)
        return {"status": "success", "message": f"Application {application_id} deleted"}

    @staticmethod
    def submit_application(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
    ) -> GrantApplicationRead:
        app = GrantApplicationService.submit_application(db, tenant.university_id, application_id, tenant.user.id)
        return GrantApplicationRead.model_validate(app)

    # Participants
    @staticmethod
    def add_participant(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
        data: GrantApplicationParticipantCreate,
    ) -> GrantApplicationParticipantRead:
        part = GrantApplicationService.add_participant(db, tenant.university_id, application_id, data)
        return GrantApplicationParticipantRead.model_validate(part)

    @staticmethod
    def list_participants(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
    ) -> list[GrantApplicationParticipantRead]:
        items = GrantApplicationService.list_participants(db, tenant.university_id, application_id)
        return [GrantApplicationParticipantRead.model_validate(item) for item in items]

    @staticmethod
    def remove_participant(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantApplicationService.remove_participant(db, tenant.university_id, application_id, participant_id)
        return {"status": "success", "message": f"Participant {participant_id} removed"}

    # Reviews
    @staticmethod
    def create_review(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
        data: GrantApplicationReviewCreate,
    ) -> GrantApplicationReviewRead:
        review = GrantApplicationService.create_review(db, tenant.university_id, application_id, data, tenant.user.id)
        return GrantApplicationReviewRead.model_validate(review)

    @staticmethod
    def list_reviews(
        db: Session,
        tenant: TenantContext,
        application_id: uuid.UUID,
    ) -> list[GrantApplicationReviewRead]:
        items = GrantApplicationService.list_reviews(db, tenant.university_id, application_id)
        return [GrantApplicationReviewRead.model_validate(item) for item in items]


class GrantAwardController:
    @staticmethod
    def create_award(
        db: Session,
        tenant: TenantContext,
        data: GrantAwardCreate,
    ) -> GrantAwardRead:
        award = GrantAwardService.create_award(db, tenant.university_id, data, tenant.user.id)
        return GrantAwardRead.model_validate(award)

    @staticmethod
    def get_award(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
    ) -> GrantAwardRead:
        award = GrantAwardService.get_award(db, tenant.university_id, award_id)
        return GrantAwardRead.model_validate(award)

    @staticmethod
    def list_awards(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        application_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[GrantAwardRead]:
        items, total, total_pages = GrantAwardService.list_awards(
            db, tenant.university_id, params, application_id=application_id, status=status, search=search
        )
        return PaginatedResponse(
            items=[GrantAwardRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_award(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        data: GrantAwardUpdate,
    ) -> GrantAwardRead:
        award = GrantAwardService.update_award(db, tenant.university_id, award_id, data)
        return GrantAwardRead.model_validate(award)

    @staticmethod
    def delete_award(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantAwardService.delete_award(db, tenant.university_id, award_id)
        return {"status": "success", "message": f"Grant award {award_id} deleted"}


class GrantAllocationController:
    @staticmethod
    def create_allocation(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        data: GrantAllocationCreate,
    ) -> GrantAllocationRead:
        alloc = GrantAllocationService.create_allocation(db, tenant.university_id, award_id, data, tenant.user.id)
        return GrantAllocationRead.model_validate(alloc)

    @staticmethod
    def list_allocations(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
    ) -> list[GrantAllocationRead]:
        items = GrantAllocationService.list_allocations(db, tenant.university_id, award_id)
        return [GrantAllocationRead.model_validate(item) for item in items]

    @staticmethod
    def delete_allocation(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        allocation_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantAllocationService.delete_allocation(db, tenant.university_id, award_id, allocation_id)
        return {"status": "success", "message": f"Allocation {allocation_id} deleted"}


class GrantExpenditureController:
    @staticmethod
    def record_expenditure(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        data: GrantExpenditureCreate,
    ) -> GrantExpenditureRead:
        exp = GrantExpenditureService.record_expenditure(db, tenant.university_id, award_id, data, tenant.user.id)
        return GrantExpenditureRead.model_validate(exp)

    @staticmethod
    def get_expenditure(
        db: Session,
        tenant: TenantContext,
        expenditure_id: uuid.UUID,
    ) -> GrantExpenditureRead:
        exp = GrantExpenditureService.get_expenditure(db, tenant.university_id, expenditure_id)
        return GrantExpenditureRead.model_validate(exp)

    @staticmethod
    def list_expenditures(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        params: PaginationParams,
        status: Optional[str] = None,
    ) -> PaginatedResponse[GrantExpenditureRead]:
        items, total, total_pages = GrantExpenditureService.list_expenditures(
            db, tenant.university_id, award_id, params, status=status
        )
        return PaginatedResponse(
            items=[GrantExpenditureRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_expenditure(
        db: Session,
        tenant: TenantContext,
        expenditure_id: uuid.UUID,
        data: GrantExpenditureUpdate,
    ) -> GrantExpenditureRead:
        exp = GrantExpenditureService.update_expenditure(db, tenant.university_id, expenditure_id, data)
        return GrantExpenditureRead.model_validate(exp)

    @staticmethod
    def delete_expenditure(
        db: Session,
        tenant: TenantContext,
        expenditure_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantExpenditureService.delete_expenditure(db, tenant.university_id, expenditure_id)
        return {"status": "success", "message": f"Expenditure {expenditure_id} deleted"}


class GrantProgressReportController:
    @staticmethod
    def create_report(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        data: GrantProgressReportCreate,
    ) -> GrantProgressReportRead:
        rep = GrantProgressReportService.create_report(db, tenant.university_id, award_id, data, tenant.user.id)
        return GrantProgressReportRead.model_validate(rep)

    @staticmethod
    def get_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> GrantProgressReportRead:
        rep = GrantProgressReportService.get_report(db, tenant.university_id, report_id)
        return GrantProgressReportRead.model_validate(rep)

    @staticmethod
    def list_reports(
        db: Session,
        tenant: TenantContext,
        award_id: uuid.UUID,
        params: PaginationParams,
    ) -> PaginatedResponse[GrantProgressReportRead]:
        items, total, total_pages = GrantProgressReportService.list_reports(
            db, tenant.university_id, award_id, params
        )
        return PaginatedResponse(
            items=[GrantProgressReportRead.model_validate(item) for item in items],
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
        data: GrantProgressReportUpdate,
    ) -> GrantProgressReportRead:
        rep = GrantProgressReportService.update_report(db, tenant.university_id, report_id, data)
        return GrantProgressReportRead.model_validate(rep)

    @staticmethod
    def delete_report(
        db: Session,
        tenant: TenantContext,
        report_id: uuid.UUID,
    ) -> dict[str, str]:
        GrantProgressReportService.delete_report(db, tenant.university_id, report_id)
        return {"status": "success", "message": f"Grant report {report_id} deleted"}

