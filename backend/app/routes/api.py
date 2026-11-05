"""API v1 Router aggregation."""

from fastapi import APIRouter

from .approvals import instances_router, workflows_router
from .files_audit_retention import (
    attachments_router,
    audit_logs_router,
    retention_policies_router,
    stored_files_router,
)
from .grants import (
    applications_router,
    awards_router,
    expenditures_router,
    grant_reports_router,
    opportunities_router,
)
from .notifications_alerts import (
    alert_events_router,
    alert_rules_router,
    notifications_router,
    preferences_router,
)
from .organization import (
    departments_router,
    faculties_router,
    leadership_router,
    staff_router,
    students_router,
)
from .progress_reports import activity_router, comments_router, reports_router
from .publications import publications_router
from .research_projects import milestones_router, projects_router, templates_router
from .research_proposals import proposals_router
from .research_topics import duplicates_router, topics_router
from .universities import memberships_router, settings_router, universities_router
from .users import auth_router, roles_router, user_roles_router, users_router

api_router = APIRouter(prefix="/api/v1")

# Users & Auth
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(user_roles_router)

# Universities & Settings
api_router.include_router(universities_router)
api_router.include_router(memberships_router)
api_router.include_router(settings_router)

# Organization
api_router.include_router(faculties_router)
api_router.include_router(departments_router)
api_router.include_router(leadership_router)
api_router.include_router(staff_router)
api_router.include_router(students_router)

# Research Topics
api_router.include_router(topics_router)
api_router.include_router(duplicates_router)

# Research Proposals
api_router.include_router(proposals_router)

# Research Projects
api_router.include_router(projects_router)
api_router.include_router(templates_router)
api_router.include_router(milestones_router)

# Progress Reports & Activity
api_router.include_router(reports_router)
api_router.include_router(comments_router)
api_router.include_router(activity_router)

# Grants
api_router.include_router(opportunities_router)
api_router.include_router(applications_router)
api_router.include_router(awards_router)
api_router.include_router(expenditures_router)
api_router.include_router(grant_reports_router)

# Publications
api_router.include_router(publications_router)

# Approvals
api_router.include_router(workflows_router)
api_router.include_router(instances_router)

# Notifications & Alerts
api_router.include_router(notifications_router)
api_router.include_router(preferences_router)
api_router.include_router(alert_rules_router)
api_router.include_router(alert_events_router)

# Files, Audit & Retention
api_router.include_router(stored_files_router)
api_router.include_router(attachments_router)
api_router.include_router(audit_logs_router)
api_router.include_router(retention_policies_router)

