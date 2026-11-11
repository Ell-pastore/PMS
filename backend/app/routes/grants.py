"""FastAPI routes for grant opportunities, applications, awards, expenditures, and reports."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.grants import (
    GrantAllocationController,
    GrantApplicationController,
    GrantAwardController,
    GrantExpenditureController,
    GrantOpportunityController,
    GrantProgressReportController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context, require_roles
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

opportunities_router = APIRouter(prefix="/grant-opportunities", tags=["Grant Opportunities"])
applications_router = APIRouter(prefix="/grant-applications", tags=["Grant Applications"])
awards_router = APIRouter(prefix="/grant-awards", tags=["Grant Awards"])
expenditures_router = APIRouter(prefix="/grant-expenditures", tags=["Grant Expenditures"])
grant_reports_router = APIRouter(prefix="/grant-progress-reports", tags=["Grant Progress Reports"])


# --- GRANT OPPORTUNITIES ---
@opportunities_router.post("", response_model=GrantOpportunityRead, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    data: GrantOpportunityCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantOpportunityController.create_opportunity(db, tenant, data)


@opportunities_router.get("", response_model=PaginatedResponse[GrantOpportunityRead])
def list_opportunities(
    params: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantOpportunityController.list_opportunities(
        db, tenant, params, status=status, search=search
    )


@opportunities_router.get("/{opportunity_id}", response_model=GrantOpportunityRead)
def get_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantOpportunityController.get_opportunity(db, tenant, opportunity_id)


@opportunities_router.patch("/{opportunity_id}", response_model=GrantOpportunityRead)
@opportunities_router.put("/{opportunity_id}", response_model=GrantOpportunityRead)
def update_opportunity(
    opportunity_id: uuid.UUID,
    data: GrantOpportunityUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantOpportunityController.update_opportunity(db, tenant, opportunity_id, data)


@opportunities_router.delete("/{opportunity_id}", status_code=status.HTTP_200_OK)
def delete_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantOpportunityController.delete_opportunity(db, tenant, opportunity_id)


# --- GRANT APPLICATIONS ---
@applications_router.post("", response_model=GrantApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    data: GrantApplicationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.create_application(db, tenant, data)


@applications_router.get("", response_model=PaginatedResponse[GrantApplicationRead])
def list_applications(
    params: PaginationParams = Depends(),
    opportunity_id: Optional[uuid.UUID] = Query(None),
    applicant_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.list_applications(
        db, tenant, params, opportunity_id=opportunity_id, applicant_id=applicant_id, status=status, search=search
    )


@applications_router.get("/{application_id}", response_model=GrantApplicationRead)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.get_application(db, tenant, application_id)


@applications_router.patch("/{application_id}", response_model=GrantApplicationRead)
@applications_router.put("/{application_id}", response_model=GrantApplicationRead)
def update_application(
    application_id: uuid.UUID,
    data: GrantApplicationUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.update_application(db, tenant, application_id, data)


@applications_router.delete("/{application_id}", status_code=status.HTTP_200_OK)
def delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.delete_application(db, tenant, application_id)


@applications_router.post("/{application_id}/submit", response_model=GrantApplicationRead)
def submit_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.submit_application(db, tenant, application_id)


# Application Participants
@applications_router.post("/{application_id}/participants", response_model=GrantApplicationParticipantRead, status_code=status.HTTP_201_CREATED)
def add_application_participant(
    application_id: uuid.UUID,
    data: GrantApplicationParticipantCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.add_participant(db, tenant, application_id, data)


@applications_router.get("/{application_id}/participants", response_model=list[GrantApplicationParticipantRead])
def list_application_participants(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.list_participants(db, tenant, application_id)


@applications_router.delete("/{application_id}/participants/{participant_id}", status_code=status.HTTP_200_OK)
def remove_application_participant(
    application_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.remove_participant(db, tenant, application_id, participant_id)


# Application Reviews
@applications_router.post("/{application_id}/reviews", response_model=GrantApplicationReviewRead, status_code=status.HTTP_201_CREATED)
def create_application_review(
    application_id: uuid.UUID,
    data: GrantApplicationReviewCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.create_review(db, tenant, application_id, data)


@applications_router.get("/{application_id}/reviews", response_model=list[GrantApplicationReviewRead])
def list_application_reviews(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantApplicationController.list_reviews(db, tenant, application_id)


# --- GRANT AWARDS ---
@awards_router.post("", response_model=GrantAwardRead, status_code=status.HTTP_201_CREATED)
def create_award(
    data: GrantAwardCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantAwardController.create_award(db, tenant, data)


@awards_router.get("", response_model=PaginatedResponse[GrantAwardRead])
def list_awards(
    params: PaginationParams = Depends(),
    application_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantAwardController.list_awards(db, tenant, params, application_id=application_id, status=status, search=search)


@awards_router.get("/{award_id}", response_model=GrantAwardRead)
def get_award(
    award_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantAwardController.get_award(db, tenant, award_id)


@awards_router.patch("/{award_id}", response_model=GrantAwardRead)
@awards_router.put("/{award_id}", response_model=GrantAwardRead)
def update_award(
    award_id: uuid.UUID,
    data: GrantAwardUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantAwardController.update_award(db, tenant, award_id, data)


@awards_router.delete("/{award_id}", status_code=status.HTTP_200_OK)
def delete_award(
    award_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantAwardController.delete_award(db, tenant, award_id)


# Allocations
@awards_router.post("/{award_id}/allocations", response_model=GrantAllocationRead, status_code=status.HTTP_201_CREATED)
def create_allocation(
    award_id: uuid.UUID,
    data: GrantAllocationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantAllocationController.create_allocation(db, tenant, award_id, data)


@awards_router.get("/{award_id}/allocations", response_model=list[GrantAllocationRead])
def list_allocations(
    award_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantAllocationController.list_allocations(db, tenant, award_id)


@awards_router.delete("/{award_id}/allocations/{allocation_id}", status_code=status.HTTP_200_OK)
def delete_allocation(
    award_id: uuid.UUID,
    allocation_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantAllocationController.delete_allocation(db, tenant, award_id, allocation_id)


# Expenditures under award
@awards_router.post("/{award_id}/expenditures", response_model=GrantExpenditureRead, status_code=status.HTTP_201_CREATED)
def record_expenditure(
    award_id: uuid.UUID,
    data: GrantExpenditureCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantExpenditureController.record_expenditure(db, tenant, award_id, data)


@awards_router.get("/{award_id}/expenditures", response_model=PaginatedResponse[GrantExpenditureRead])
def list_expenditures(
    award_id: uuid.UUID,
    params: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantExpenditureController.list_expenditures(db, tenant, award_id, params, status=status)


@expenditures_router.get("/{expenditure_id}", response_model=GrantExpenditureRead)
def get_expenditure(
    expenditure_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantExpenditureController.get_expenditure(db, tenant, expenditure_id)


@expenditures_router.patch("/{expenditure_id}", response_model=GrantExpenditureRead)
@expenditures_router.put("/{expenditure_id}", response_model=GrantExpenditureRead)
def update_expenditure(
    expenditure_id: uuid.UUID,
    data: GrantExpenditureUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantExpenditureController.update_expenditure(db, tenant, expenditure_id, data)


@expenditures_router.delete("/{expenditure_id}", status_code=status.HTTP_200_OK)
def delete_expenditure(
    expenditure_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    _admin: TenantContext = Depends(require_roles("grant_admin", "university_admin")),
):
    return GrantExpenditureController.delete_expenditure(db, tenant, expenditure_id)


# Progress reports under award
@awards_router.post("/{award_id}/reports", response_model=GrantProgressReportRead, status_code=status.HTTP_201_CREATED)
def create_grant_report(
    award_id: uuid.UUID,
    data: GrantProgressReportCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantProgressReportController.create_report(db, tenant, award_id, data)


@awards_router.get("/{award_id}/reports", response_model=PaginatedResponse[GrantProgressReportRead])
def list_grant_reports(
    award_id: uuid.UUID,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantProgressReportController.list_reports(db, tenant, award_id, params)


@grant_reports_router.get("/{report_id}", response_model=GrantProgressReportRead)
def get_grant_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantProgressReportController.get_report(db, tenant, report_id)


@grant_reports_router.patch("/{report_id}", response_model=GrantProgressReportRead)
@grant_reports_router.put("/{report_id}", response_model=GrantProgressReportRead)
def update_grant_report(
    report_id: uuid.UUID,
    data: GrantProgressReportUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantProgressReportController.update_report(db, tenant, report_id, data)


@grant_reports_router.delete("/{report_id}", status_code=status.HTTP_200_OK)
def delete_grant_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return GrantProgressReportController.delete_report(db, tenant, report_id)

