# PMS API Reference

## Overview

PMS exposes a RESTful JSON API under the `/api/v1` prefix. There are 37 routers organized into 12 domains, yielding approximately 120 OpenAPI paths. FastAPI auto-generates OpenAPI documentation.

## Base URL

- Development: `http://localhost:8000/api/v1` (via `uvicorn backend.app.main:app --reload`)
- Health check: `GET /health` (returns `{"status": "ok"}`)

## Authentication

### Token Auth

Most endpoints require authentication via one of two headers (checked in order):

1. `Authorization: Bearer <access_token>` — custom HMAC-SHA256 JWT-compatible token.
2. `X-User-Id: <user_id>` — direct user ID header (fallback).

Tokens are created by `security.create_access_token()` and verified by `security.decode_access_token()`. Token expiry is 24 hours.

Users must have `status == active`; otherwise requests receive `403 ForbiddenError`.

### Tenant Context

University-scoped endpoints require `X-University-ID: <uuid>` header (or `university_id` query parameter). The `get_tenant_context` dependency validates the university, loads the user's roles for that university, and verifies active membership.

Cross-tenant resource access returns **404** (not 403) to avoid leaking resource existence.

### Authorization

Global administrative routes require the `university_admin` role via `require_roles("university_admin")`. Domain mutations are gated by their matching domain role:

| Route Group | Required Role |
|-------------|---------------|
| Users list/delete, roles, permissions, universities, memberships, settings, user-role assignments | `university_admin` |
| Faculties mutations | `university_admin` |
| Departments + department leadership mutations | `department_head` or `university_admin` |
| Research topics, duplicate-candidate review, approval workflows/versions/steps, audit logs, retention policies, milestone templates | `research_admin` or `university_admin` |
| Grant opportunities, awards, allocations, expenditures | `grant_admin` or `university_admin` |

The `superadmin` role bypasses every role check. It is seeded as reference data (granted to no one) and must be manually assigned to take effect.

Reads and collaborative research routes (proposals, projects, milestones, progress reports, publications, grant applications, notifications, files, profiles) are open to any active tenant member. See [`USER_ROLES.md`](../product/USER_ROLES.md) for the full access matrix.

Self-access to one's own user profile (`GET/PATCH /users/{id}`) is allowed without the admin role.

### Delete Guards

Deleting an entity that still has user-created child data returns **400** `SpecializedOperationError` (`RESTRICTED_OPERATION`) listing the blockers, instead of leaking a raw database integrity error. Machine-derived bookkeeping rows (status history, draft approval-workflow versions and steps, account verification tokens) are cascaded in the same transaction. Draft proposals, draft grant applications, and unused leaf entities remain deletable.

## Error Response Format

All errors return JSON with a consistent shape:

```json
{
  "detail": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "error": "ExceptionClassName"
}
```

### HTTP Status Codes

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 200 | Success | GET, PUT, PATCH, DELETE |
| 201 | Created | POST |
| 400 | Bad request | Invalid input, FK violation, check constraint |
| 401 | Unauthorized | Missing/invalid token, user not found |
| 403 | Forbidden | Insufficient role, inactive account, inactive tenant, no membership |
| 404 | Not found | Resource missing OR cross-tenant access (existence not leaked) |
| 409 | Conflict | Duplicate resource, unique constraint violation |
| 422 | Unprocessable | Pydantic/schema validation error |

## Pagination

All list endpoints use a standardized paginated envelope:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

Query parameters:
- `page` (default 1, min 1)
- `page_size` (default 20, min 1, max 100)

## Domain Endpoints

### 1. Users & Authentication

**Auth** (`/auth`):
- `POST /auth/register` — Register a new user (201)
- `POST /auth/login` — Authenticate and receive a token (200)
- `GET /auth/me` — Get current user profile (200, requires auth)

**Users** (`/users`):
- `GET /users` — List users (paginated, requires `university_admin`)
- `GET /users/{user_id}` — Get user (200; self or `university_admin`)
- `PATCH/PUT /users/{user_id}` — Update user (200; self or `university_admin`)
- `DELETE /users/{user_id}` — Delete user (200, requires `university_admin`; blocked if memberships, role assignments, or profiles exist)

**Roles** (`/roles`):
- `POST /roles` — Create role (201, requires `university_admin`)
- `GET /roles` — List roles (paginated, requires `university_admin`)
- `GET /roles/{role_id}` — Get role (200, requires `university_admin`)
- `PATCH/PUT /roles/{role_id}` — Update role (200, requires `university_admin`)
- `DELETE /roles/{role_id}` — Delete role (200, requires `university_admin`; blocked if user role or permission assignments exist)

**Permissions** (`/roles/permissions`):
- `POST /roles/permissions` — Create permission (201, requires `university_admin`)
- `GET /roles/permissions` — List permissions (paginated, requires `university_admin`)
- `POST /roles/permissions/assign` — Assign permission to role (201, requires `university_admin`)
- `DELETE /roles/permissions/assignments/{assignment_id}` — Remove assignment (200, requires `university_admin`)

> **Note**: `/roles/permissions` is declared before `/{role_id}` to avoid route shadowing.

**User Roles (Tenant)** (`/user-roles`):
- `POST /user-roles` — Assign role to user in university (201, requires `university_admin`)
- `GET /user-roles` — List user roles (paginated; filter by `user_id`, `role_id`, `active_only`)
- `POST /user-roles/{user_role_id}/revoke` — Revoke a user role (200, requires `university_admin`)
- `DELETE /user-roles/{user_role_id}` — Delete user role assignment (200, requires `university_admin`)

### 2. Universities & Settings

**Universities** (`/universities`):
- `POST /universities` — Create university (201, requires `university_admin`)
- `GET /universities` — List universities (paginated; filter `search`, `is_active`; requires `university_admin`)
- `GET /universities/{university_id}` — Get university (200, requires `university_admin`)
- `PATCH/PUT /universities/{university_id}` — Update university (200, requires `university_admin`)
- `DELETE /universities/{university_id}` — Delete university (200, requires `university_admin`; blocked if members, faculties, departments, or settings exist)

**University Memberships** (`/university-memberships`):
- `POST /university-memberships` — Add membership (201, requires `university_admin`)
- `GET /university-memberships` — List memberships (paginated; filter `user_id`, `is_active`)
- `GET /university-memberships/{membership_id}` — Get membership (200)
- `PATCH/PUT /university-memberships/{membership_id}` — Update membership (200, requires `university_admin`)
- `DELETE /university-memberships/{membership_id}` — Delete membership (200, requires `university_admin`; blocked if role assignments or profiles exist)

**Settings** (`/settings`):
- `GET /settings/university` — University settings (mutations require `university_admin`)
- `GET/PATCH /settings/departments/{department_id}` — Department settings (mutations require `university_admin`)
- `POST/GET/PATCH/DELETE /settings/system/{setting_key}` — System settings (key-value JSON store; mutations require `university_admin`)

### 3. Organization

**Faculties** (`/faculties`):
- `POST /faculties` — Create faculty (201, requires `university_admin`)
- `GET /faculties` — List faculties (paginated; filter `search`, `is_active`)
- `GET /faculties/{faculty_id}` — Get faculty (200)
- `PATCH/PUT /faculties/{faculty_id}` — Update faculty (200, requires `university_admin`)
- `DELETE /faculties/{faculty_id}` — Delete faculty (200, requires `university_admin`; blocked if departments exist)

**Departments** (`/departments`):
- `POST /departments` — Create department (201, requires `department_head` or `university_admin`)
- `GET /departments` — List departments (paginated; filter `faculty_id`, `search`, `is_active`)
- `GET /departments/{department_id}` — Get department (200)
- `PATCH/PUT /departments/{department_id}` — Update department (200, requires `department_head` or `university_admin`)
- `DELETE /departments/{department_id}` — Delete department (200, requires `department_head` or `university_admin`; blocked if referenced by proposals/projects/profiles/leadership)

**Department Leadership** (`/department-leadership`):
- `POST /department-leadership` — Appoint leadership (201, requires `department_head` or `university_admin`)
- `GET /department-leadership` — List leadership (paginated; filter `department_id`, `active_only`)
- `GET /department-leadership/{leadership_id}` — Get leadership (200)
- `POST /department-leadership/{leadership_id}/end` — End leadership (200, requires `department_head` or `university_admin`)
- `DELETE /department-leadership/{leadership_id}` — Delete leadership (200, requires `department_head` or `university_admin`)

**Staff Profiles** (`/staff-profiles`):
- `POST /staff-profiles` — Create staff profile (201)
- `GET /staff-profiles` — List staff profiles (paginated; filter `department_id`, `search`)
- `GET /staff-profiles/{profile_id}` — Get staff profile (200)
- `PATCH/PUT /staff-profiles/{profile_id}` — Update staff profile (200)
- `DELETE /staff-profiles/{profile_id}` — Delete staff profile (200; blocked if supervisor or leadership assignments exist)

**Student Profiles** (`/student-profiles`):
- `POST /student-profiles` — Create student profile (201)
- `GET /student-profiles` — List student profiles (paginated; filter `department_id`, `search`, `status`)
- `GET /student-profiles/{profile_id}` — Get student profile (200)
- `PATCH/PUT /student-profiles/{profile_id}` — Update student profile (200)
- `DELETE /student-profiles/{profile_id}` — Delete student profile (200; blocked if participant assignments exist)

### 4. Research Topics

**Topics** (`/research-topics`):
- `POST /research-topics` — Create topic (201, requires `research_admin` or `university_admin`)
- `GET /research-topics` — List topics (paginated; filter `department_id`, `search`, `is_active`)
- `GET /research-topics/{topic_id}` — Get topic (200)
- `PATCH/PUT /research-topics/{topic_id}` — Update topic (200, requires `research_admin` or `university_admin`)
- `DELETE /research-topics/{topic_id}` — Delete topic (200, requires `research_admin` or `university_admin`; blocked if proposals reference it)

**Duplicate Candidates** (`/research-topics/duplicates`):
- `POST /research-topics/duplicates` — Create duplicate candidate (201)
- `GET /research-topics/duplicates` — List candidates (paginated; filter `review_status`)
- `GET /research-topics/duplicates/{candidate_id}` — Get candidate (200)
- `POST /research-topics/duplicates/{candidate_id}/review` — Review candidate (200, requires `research_admin` or `university_admin`)
- `DELETE /research-topics/duplicates/{candidate_id}` — Delete candidate (200)

### 5. Research Proposals

**Proposals** (`/research-proposals`):
- `POST /research-proposals` — Create proposal (201)
- `GET /research-proposals` — List proposals (paginated; filter `department_id`, `topic_id`, `submitting_user_id`, `status`, `search`)
- `GET /research-proposals/{proposal_id}` — Get proposal (200)
- `PATCH/PUT /research-proposals/{proposal_id}` — Update proposal (200; only draft/revision_requested)
- `DELETE /research-proposals/{proposal_id}` — Delete proposal (200; only draft, and blocked if revisions/participants/supervisors/reviews/projects exist)
- `POST /research-proposals/{proposal_id}/submit` — Submit proposal (200; draft/revision_requested → submitted)
- `POST /research-proposals/{proposal_id}/status` — Transition status (200)

**Participants** (`/research-proposals/{proposal_id}/participants`):
- `POST` — Add participant (201)
- `GET` — List participants
- `DELETE /{participant_id}` — Remove participant (200)

**Supervisors** (`/research-proposals/{proposal_id}/supervisors`):
- `POST` — Assign supervisor (201)
- `GET` — List supervisors (filter `active_only`)
- `POST /{supervisor_id}/end` — End supervision (200)

**Revisions** (`/research-proposals/{proposal_id}/revisions`):
- `POST` — Create revision (201)
- `GET` — List revisions

**Reviews** (`/research-proposals/{proposal_id}/reviews`):
- `POST` — Create review (201)
- `GET` — List reviews

### 6. Research Projects

**Projects** (`/research-projects`):
- `POST /research-projects` — Create project (201; from approved proposal, one per proposal)
- `GET /research-projects` — List projects (paginated; filter `department_id`, `proposal_id`, `status`, `search`)
- `GET /research-projects/{project_id}` — Get project (200)
- `PATCH/PUT /research-projects/{project_id}` — Update project (200)
- `DELETE /research-projects/{project_id}` — Delete project (200; blocked if milestones/participants/supervisors/reports/comments/publication or grant links exist)
- `POST /research-projects/{project_id}/status` — Transition status (200)

**Participants** (`/research-projects/{project_id}/participants`):
- `POST` — Add participant (201)
- `GET` — List participants (filter `active_only`)
- `POST /{participant_id}/end` — End participation (200)
- `DELETE /{participant_id}` — Remove participant (200)

**Supervisors** (`/research-projects/{project_id}/supervisors`):
- `POST` — Assign supervisor (201)
- `GET` — List supervisors (filter `active_only`)
- `POST /{supervisor_id}/end` — End supervision (200)

**Milestone Templates** (`/milestone-templates`):
- `POST` — Create template (201, requires `research_admin` or `university_admin`)
- `GET` — List templates (paginated; filter `department_id`, `search`, `is_active`)
- `GET /{template_id}` — Get template (200)
- `PATCH/PUT /{template_id}` — Update template (200, requires `research_admin` or `university_admin`)
- `DELETE /{template_id}` — Delete template (200, requires `research_admin` or `university_admin`; blocked if milestones reference it)

**Project Milestones** (`/project-milestones`):
- `POST /research-projects/{project_id}/milestones` — Create milestone (201)
- `GET /research-projects/{project_id}/milestones` — List milestones (paginated; filter `status`)
- `GET /project-milestones/{milestone_id}` — Get milestone (200)
- `PATCH/PUT /project-milestones/{milestone_id}` — Update milestone (200)
- `DELETE /project-milestones/{milestone_id}` — Delete milestone (200; blocked if progress reports or comments reference it)

### 7. Progress Reports & Activity

**Reports** (`/progress-reports`):
- `POST /progress-reports` — Create report (201)
- `GET /progress-reports` — List reports (paginated)
- `GET /progress-reports/{report_id}` — Get report (200)
- `PATCH/PUT /progress-reports/{report_id}` — Update report (200)
- `DELETE /progress-reports/{report_id}` — Delete report (200; only draft, and blocked if reviews or comments exist)

**Comments** (`/project-comments`):
- `POST` — Create comment (201)
- `GET` — List comments
- `GET /{comment_id}` — Get comment (200)
- `PATCH/PUT /{comment_id}` — Update comment (200)
- `DELETE /{comment_id}` — Delete comment (200)

**Activity** (`/student-activity`):
- `POST` — Record activity (201)
- `GET` — List activity

### 8. Grants

**Opportunities** (`/grant-opportunities`):
- `POST /grant-opportunities` — Create opportunity (201, requires `grant_admin` or `university_admin`)
- `GET /grant-opportunities` — List opportunities (paginated; filter `status`, `search`)
- `GET /grant-opportunities/{opportunity_id}` — Get opportunity (200)
- `PATCH/PUT /grant-opportunities/{opportunity_id}` — Update opportunity (200, requires `grant_admin` or `university_admin`)
- `DELETE /grant-opportunities/{opportunity_id}` — Delete opportunity (200, requires `grant_admin` or `university_admin`; blocked if applications exist)

**Applications** (`/grant-applications`):
- `POST /grant-applications` — Create application (201)
- `GET /grant-applications` — List applications (paginated; filter `opportunity_id`, `applicant_id`, `status`, `search`)
- `GET /grant-applications/{application_id}` — Get application (200)
- `PATCH/PUT /grant-applications/{application_id}` — Update application (200; only draft)
- `DELETE /grant-applications/{application_id}` — Delete application (200; only draft, and blocked if awards/participants/reviews exist)
- `POST /grant-applications/{application_id}/submit` — Submit application (200; draft → submitted)

**Participants** (`/grant-applications/{application_id}/participants`):
- `POST` — Add participant (201)
- `GET` — List participants
- `DELETE /{participant_id}` — Remove participant (200)

**Reviews** (`/grant-applications/{application_id}/reviews`):
- `POST` — Create review (201)
- `GET` — List reviews

**Awards** (`/grant-awards`):
- `POST /grant-awards` — Create award (201, requires `grant_admin` or `university_admin`; application → approved, one award per application)
- `GET /grant-awards` — List awards (paginated; filter `application_id`, `status`, `search`)
- `GET /grant-awards/{award_id}` — Get award (200)
- `PATCH/PUT /grant-awards/{award_id}` — Update award (200, requires `grant_admin` or `university_admin`)
- `DELETE /grant-awards/{award_id}` — Delete award (200, requires `grant_admin` or `university_admin`; blocked if expenditures/allocations/reports exist)

**Allocations** (`/grant-awards/{award_id}/allocations`):
- `POST` — Create allocation (201, requires `grant_admin` or `university_admin`)
- `GET` — List allocations
- `DELETE /{allocation_id}` — Delete allocation (200, requires `grant_admin` or `university_admin`)

**Expenditures** (`/grant-expenditures` and `/grant-awards/{award_id}/expenditures`):
- `POST /grant-awards/{award_id}/expenditures` — Record expenditure (201, requires `grant_admin` or `university_admin`)
- `GET /grant-awards/{award_id}/expenditures` — List expenditures (paginated; filter `status`)
- `GET /grant-expenditures/{expenditure_id}` — Get expenditure (200)
- `PATCH/PUT /grant-expenditures/{expenditure_id}` — Update expenditure (200, requires `grant_admin` or `university_admin`)
- `DELETE /grant-expenditures/{expenditure_id}` — Delete expenditure (200, requires `grant_admin` or `university_admin`)

**Progress Reports** (`/grant-awards/{award_id}/reports` and `/grant-progress-reports`):
- `POST /grant-awards/{award_id}/reports` — Create report (201)
- `GET /grant-awards/{award_id}/reports` — List reports (paginated)
- `GET /grant-progress-reports/{report_id}` — Get report (200)
- `PATCH/PUT /grant-progress-reports/{report_id}` — Update report (200)
- `DELETE /grant-progress-reports/{report_id}` — Delete report (200)

### 9. Publications

**Publications** (`/publications`):
- `POST /publications` — Create publication (201)
- `GET /publications` — List publications (paginated)
- `GET /publications/{publication_id}` — Get publication (200)
- `PATCH/PUT /publications/{publication_id}` — Update publication (200)
- `DELETE /publications/{publication_id}` — Delete publication (200; blocked if authors, project links, or reviews exist)

Related: publication_authors, publication_projects, publication_reviews sub-resources.

### 10. Approvals

**Workflows** (`/approval-workflows`):
- `POST /approval-workflows` — Create workflow (201, requires `research_admin` or `university_admin`)
- `GET /approval-workflows` — List workflows (paginated; filter `workflow_type`, `department_id`)
- `GET /approval-workflows/{workflow_id}` — Get workflow (200)
- `PATCH/PUT /approval-workflows/{workflow_id}` — Update workflow (200, requires `research_admin` or `university_admin`)
- `DELETE /approval-workflows/{workflow_id}` — Delete workflow (200, requires `research_admin` or `university_admin`; blocked if instances exist)

**Versions** (`/approval-workflows/{workflow_id}/versions`):
- `POST` — Create version (201, requires `research_admin` or `university_admin`; initial version created with workflow)
- `GET` — List versions
- `GET /{version_id}` — Get version (200)
- `POST /{version_id}/publish` — Publish version (200, requires `research_admin` or `university_admin`; immutable once published)
- `DELETE /{version_id}` — Delete version (200, requires `research_admin` or `university_admin`; not if published)

**Steps** (`/approval-workflows/{workflow_id}/versions/{version_id}/steps`):
- `POST` — Add step (201, requires `research_admin` or `university_admin`; not if published)
- `GET` — List steps
- `GET /{step_id}` — Get step (200)
- `PATCH/PUT /{step_id}` — Update step (200, requires `research_admin` or `university_admin`; not if published)
- `DELETE /{step_id}` — Delete step (200, requires `research_admin` or `university_admin`; not if published)

**Instances** (`/approval-instances`):
- `POST /approval-instances` — Create instance (201; requires active published version)
- `GET /approval-instances` — List instances (paginated; filter `workflow_id`, `target_entity_type`, `status`)
- `GET /approval-instances/{instance_id}` — Get instance (200)

**Actions** (`/approval-instances/{instance_id}/actions`):
- `POST` — Record action (201; verifies actor role if step requires one)
- `GET` — List actions

### 11. Notifications & Alerts

**Notifications** (`/notifications`):
- `POST /notifications` — Create notification (201)
- `GET /notifications` — List notifications (paginated)
- `GET /notifications/{notification_id}` — Get notification (200)
- `PATCH/PUT /notifications/{notification_id}` — Update notification (200)
- `DELETE /notifications/{notification_id}` — Delete notification (200)

**Preferences** (`/notification-preferences`):
- `POST` — Create preference (201)
- `GET` — List preferences
- `GET /{preference_id}` — Get preference (200)
- `PATCH/PUT /{preference_id}` — Update preference (200)
- `DELETE /{preference_id}` — Delete preference (200)

**Alert Rules** (`/alert-rules`):
- `POST /alert-rules` — Create rule (201)
- `GET /alert-rules` — List rules (paginated)
- `GET /alert-rules/{rule_id}` — Get rule (200)
- `PATCH/PUT /alert-rules/{rule_id}` — Update rule (200)
- `DELETE /alert-rules/{rule_id}` — Delete rule (200; blocked if alert events exist)

**Alert Events** (`/alert-events`):
- `POST /alert-events` — Create event (201)
- `GET /alert-events` — List events (paginated)
- `GET /alert-events/{event_id}` — Get event (200)
- `PATCH/PUT /alert-events/{event_id}` — Update event (200)
- `DELETE /alert-events/{event_id}` — Delete event (200)

### 12. Files, Audit & Retention

**Stored Files** (`/stored-files`):
- `POST /stored-files` — Create file record (201)
- `GET /stored-files` — List files (paginated)
- `GET /stored-files/{file_id}` — Get file (200)
- `PATCH/PUT /stored-files/{file_id}` — Update file (200)
- `DELETE /stored-files/{file_id}` — Soft-delete file (200); `?hard_delete=true` purges the row (blocked if document attachments exist)

**Document Attachments** (`/document-attachments`):
- `POST /document-attachments` — Create attachment (201; exactly one target: proposal/project/report/application)
- `GET /document-attachments` — List attachments (paginated)
- `GET /document-attachments/{attachment_id}` — Get attachment (200)
- `PATCH/PUT /document-attachments/{attachment_id}` — Update attachment (200)
- `DELETE /document-attachments/{attachment_id}` — Delete attachment (200)

**Audit Logs** (`/audit-logs`):
- `POST /audit-logs` — Create audit log (201, requires `research_admin` or `university_admin`)
- `GET /audit-logs` — List audit logs (paginated)
- `GET /audit-logs/{log_id}` — Get audit log (200)
- `DELETE /audit-logs/{log_id}` — Delete audit log (requires `research_admin` or `university_admin`)

**Retention Policies** (`/retention-policies`):
- `POST /retention-policies` — Create policy (201, requires `research_admin` or `university_admin`)
- `GET /retention-policies` — List policies (paginated)
- `GET /retention-policies/{policy_id}` — Get policy (200)
- `PATCH/PUT /retention-policies/{policy_id}` — Update policy (200, requires `research_admin` or `university_admin`)
- `DELETE /retention-policies/{policy_id}` — Delete policy (200, requires `research_admin` or `university_admin`)

## Route Registration

All routers are aggregated in `backend/app/routes/api.py` with prefix `/api/v1`. New routers must be added there to be mounted.

## Route Ordering Rule

Static routes must be declared **before** dynamic parameterized routes on the same router to avoid path shadowing (e.g., `/permissions` before `/{role_id}`).

## Related Documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — API architecture section
- [`ARCHITECTURE_ESSENTIALS.md`](ARCHITECTURE_ESSENTIALS.md) — API conventions
- [`AGENTS.md`](../AGENTS.md) — API development conventions
- [`PRD.md`](../PRD.md) — Functional requirements
