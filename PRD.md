# Product Requirements Document (PRD) — PMS

**Project:** Project Management System (PMS)  
**Status:** Implemented (backend)  
**Scope:** Confirmed requirements vs. proposed improvements are clearly distinguished throughout.

---

## 1. Product overview

PMS is a backend-only web API for managing academic research within a university. Each deployment serves **one university instance at a time**, though the data model supports multiple universities (multi-tenancy by `university_id`). The system currently focuses on four areas:

- Student Research Management
- Articles and Publications
- Grant Management
- Project Progress Monitoring

The application is a FastAPI service backed by PostgreSQL, with 60 database tables, 37 API routers under `/api/v1`, and roughly 120 OpenAPI paths. There is **no frontend** implemented.

## 2. Problem statement

Universities lack a unified system to track student research projects from topic proposal through grant funding to publication. Research proposals, projects, milestones, progress reports, grant applications/awards, and publications are managed in isolation (or on paper), making it difficult to:

- enforce tenant isolation between universities sharing the same deployment,
- track research status consistently across the proposal → project → publication pipeline,
- manage grant lifecycles (opportunity → application → award → expenditure → report),
- verify publications and link them to the research projects that produced them,
- enforce role-based access and approval workflows.

## 3. Product vision

A single, tenant-isolated platform that manages the full research lifecycle for one university at a time — from research topic and proposal, through project execution and progress monitoring, to grant funding and verified publication — with role-based access, approval workflows, audit logging, and retention controls.

## 4. Objectives

| # | Objective | Status |
|---|-----------|--------|
| O1 | Provide a REST API for university research administration | Implemented |
| O2 | Isolate all data by university (multi-tenancy, one instance per deployment) | Implemented |
| O3 | Manage users, roles, permissions, and university memberships | Implemented |
| O4 | Manage organizations: faculties, departments, staff, students | Implemented |
| O5 | Manage research topics, proposals, and projects | Implemented |
| O6 | Track project progress via milestones and progress reports | Implemented |
| O7 | Manage grant opportunities, applications, awards, expenditures | Implemented |
| O8 | Manage publications and verification workflow | Implemented |
| O9 | Enforce role-based access on administrative routes | Implemented (global admin routes plus domain-level RBAC) |
| O10 | Provide structured error handling and pagination | Implemented |

## 5. Target users and personas

| Persona | Description | Primary needs |
|---------|-------------|---------------|
| Student | Enrolled researcher affiliated with a department | Create/view proposals, join projects, submit progress reports |
| Supervisor / Staff | Academic staff member | Supervise proposals/projects, review progress, manage grants |
| Department Head | Leads a department | Department-level oversight, leadership assignments |
| Research Admin | Administers research administration | Topic/department setup, proposal review |
| Grant Admin | Manages grant lifecycle | Opportunities, applications, awards, expenditures |
| University Admin | University-level administrator | User/role/university management, global admin routes |
| Superadmin | Cross-tenant bypass role (seeded as reference data; assignment is manual) | Operate across universities (requires manual role assignment) |

## 6. User roles and permissions

Role codes seeded as reference data: `student`, `supervisor`, `department_head`, `research_admin`, `grant_admin`, `university_admin`, `superadmin`.

- Roles are assigned to users within a specific university (`user_roles`, scoped by `university_id`).
- `user_roles` has an active-assignment partial unique index on `(university_id, user_id, role_id)` where `revoked_at IS NULL`; roles can be revoked by setting `revoked_at`.
- Permissions (`permissions` table) are linked to roles via `role_permissions`.
- A `superadmin` role code is seeded with the other reference roles; the bypass in `TenantContext.has_role` and `get_tenant_context` activates only once the role is manually assigned to a user (seeding grants it to no one).
- Authorization is enforced through tenant scoping (`university_id`) on every service query plus route-level role checks: `require_roles("university_admin")` on global administrative routes, and domain-level gates on organizational and administrative mutations (see `docs/product/USER_ROLES.md` for the full access matrix). Collaborative domain work (proposals, projects, milestones, progress reports, publications, grant applications, notifications) remains open to any active tenant member.

See `docs/product/USER_ROLES.md` for details.

## 7. Core modules

| Module | Domains covered | Status |
|--------|----------------|--------|
| Users & Auth | registration, login, `/auth/me`, password hashing, account verification | Implemented |
| Roles & Permissions | roles, permissions, role-permission assignments, user-role assignments | Implemented |
| Universities | university CRUD, memberships, university settings | Implemented |
| Organization | faculties, departments, staff profiles, student profiles, department leadership | Implemented |
| Research Topics | topics, duplicate topic detection candidates | Implemented |
| Research Proposals | proposals, revisions, participants, supervisors, reviews, status history | Implemented |
| Research Projects | projects, milestones, supervisors, participants, comments, activity, status history | Implemented |
| Progress Reports | reports, reviews, comments, student activity | Implemented |
| Grants | opportunities, applications, awards, expenditures, grant progress reports, project allocations | Implemented |
| Publications | publications, authors, project links, reviews | Implemented |
| Approvals | workflows, versions, steps, instances, actions | Implemented |
| Notifications & Alerts | notifications, preferences, alert rules, alert events | Implemented |
| Files, Audit & Retention | stored files, document attachments, audit logs, retention policies | Implemented |

## 8. Functional requirements

### 8.1 Confirmed requirements (implemented)

**FR-1 (Auth)** Users can register, log in, and retrieve their own profile (`/auth/me`). Passwords are hashed with PBKDF2-HMAC-SHA256; tokens are HMAC-signed (24h expiry). An `X-User-Id` header can be used as an alternative to bearer tokens.

**FR-2 (Tenancy)** Every tenant-scoped request must supply `X-University-ID` (or `university_id` query). The tenant is verified: university must exist and be active; the user must have an active membership (superadmin bypasses membership check).

**FR-3 (RBAC on admin routes)** `require_roles("university_admin")` guards university, role, permission, user-list, membership, settings, and user-role assignment administration. `superadmin` bypasses all role checks. Self-access to one's own user record is preserved.

**FR-4 (Tenant isolation)** All service queries scope by `university_id`; composite foreign keys include `university_id`; indexes are `(id, university_id)` unique pairs. Cross-tenant access returns 404.

**FR-5 (Pagination)** List endpoints return `PaginatedResponse` envelope: `items`, `total`, `page`, `page_size`, `total_pages`. Default page 1, page size 20, max 100.

**FR-6 (Structured errors)** `PMSException` hierarchy (NotFoundError, DuplicateResourceError, ForeignKeyViolationError, InvalidInputError, UnauthorizedError, ForbiddenError, DatabaseError, SpecializedOperationError) returns JSON `{detail, error_code, error}`. SQLAlchemy IntegrityError is mapped by SQLSTATE (23505 → 409, 23503 → 400, etc.).

**FR-7 (Research lifecycle)** Topics → proposals (with revisions, participants, supervisors, reviews) → projects (with milestones, supervisors, participants, comments, activity) → progress reports → publications.

**FR-8 (Grant lifecycle)** Opportunities → applications → awards → expenditures → grant progress reports, with project allocations linking awards to projects.

**FR-9 (Delete guards)** `SpecializedOperationError` (400, `RESTRICTED_OPERATION`) raised when deleting an entity still referenced by user-created or cross-domain data: topics referenced by proposals, faculties with departments, departments with dependent profiles/proposals/projects/leadership, grant opportunities with applications, proposals (unless draft, and without projects/revisions/participants/supervisors/reviews), projects (without milestones/participants/supervisors/reports/comments/publication or grant links), grant applications (unless draft, and without awards/participants/reviews), grant awards (without expenditures/allocations/reports), publications (without authors/project links/reviews), milestones (without reports/comments), templates (without milestones), progress reports (unless draft, and without reviews/comments), alert rules (without events), stored files (hard delete with attachments), staff/student profiles (without supervisor/participant/leadership assignments), users (without memberships/role assignments/profiles), roles (without assignments), universities (without members/faculties/departments/settings), and memberships (without role assignments/profiles). Machine-derived bookkeeping rows (status history, draft workflow versions and steps, account verification tokens) are cascaded within the same transaction.

**FR-10 (Single-transaction creation)** Proposal, project, application, and approval-workflow creation flush then commit once, including initial status history/draft version.

**FR-11 (Status validation)** Pydantic `pattern` validation on proposal (`draft|submitted|under_review|revision_requested|approved|rejected|withdrawn`) and project (`active|on_hold|completed|cancelled|archived`) status transitions.

**FR-12 (Domain-level RBAC)** Mutations on organizational and administrative domain routes require the matching domain role via `require_roles(...)`: faculties/memberships/settings/user-role assignments require `university_admin`; departments and department leadership require `department_head` or `university_admin`; research topics, duplicate-candidate review, approval workflows/versions/steps, audit logs, retention policies, and milestone templates require `research_admin` or `university_admin`; grant opportunities, awards, expenditures, and allocations require `grant_admin` or `university_admin`. Reads and collaborative research work (proposals, projects, milestones, progress reports, publications, grant applications, notifications, files) remain open to any active member. `superadmin` bypasses all role checks.

**FR-13 (Superadmin seed)** `superadmin` is part of `INITIAL_ROLE_CODES` reference data so the bypass path can be activated by assigning the role; seeding grants it to no one.

### 8.2 Proposed improvements (NOT implemented — future work)

| ID | Requirement | Rationale | Status |
|----|-------------|-----------|--------|
| PF-4 | Soft deletes instead of hard `db.delete()` | Preserve history | Not implemented |
| PF-5 | Frontend application | User interface | Not implemented |
| PF-6 | Email/SMS notification channels | Multi-channel alerts | Not implemented (only `in_app` channel constrained) |
| PF-7 | OAuth / external identity providers | SSO | Not implemented |
| PF-8 | File storage backend integration (S3, etc.) | Persistent attachments | Not implemented (stored_files tracks metadata only) |

Previously proposed and now implemented: PF-1 (domain-level RBAC → FR-12), PF-2 (seeded `superadmin` → FR-13), PF-3 (delete guards on remaining domains → FR-9).

## 9. Non-functional requirements

| Requirement | Detail | Status |
|-------------|--------|--------|
| Performance | Pagination capped at 100 items/page; indexed tenant-scoped queries | Implemented |
| Reliability | Single-transaction creation flows; `pool_pre_ping` on engine | Implemented |
| Security | Password hashing, token expiration, structured errors without leakage, RESTRICT FKs | Implemented |
| Observability | `/health` endpoint, audit logs | Implemented |
| Maintainability | Layered routes → controllers → services; central exception handlers | Implemented |
| Portability | Settings via `.env` / environment variables; Alembic migrations | Implemented |

Non-functional requirements such as uptime SLA, backup/restore, rate limiting, and API versioning strategy are **not specified**.

## 10. Business rules

**BR-1 (Tenancy)** Every tenant-scoped table carries `university_id`; cross-tenant references are blocked by composite foreign keys and service-level `university_id` filters.

**BR-2 (Membership)** A user must have an active `university_membership` row for the target university to perform university-scoped operations (superadmin exempt).

**BR-3 (Role assignment)** Active role assignments are unique per `(university_id, user_id, role_id)` where `revoked_at IS NULL`. Revocation sets `revoked_at`.

**BR-4 (Proposal submission)** `submitted_at` must be NULL while status is `draft` (DB check `ck_research_proposals_submission`).

**BR-5 (Project dates)** `actual_end_date` and `expected_end_date` must be >= `start_date` when set.

**BR-6 (Milestone completion)** `completed_at` must be NULL unless status is `completed`.

**BR-7 (Grant amounts)** `requested_amount`, `awarded_amount`, `allocated_amount` must be >= 0; `award_end_date >= award_start_date`.

**BR-8 (Exclusive target)** `document_attachments` and `project_comments` each reference exactly one target (proposal/project/report/application via `num_nonnulls = 1`).

**BR-9 (Publication identity)** A publication author is either an internal user or an external author name, never both (`ck_publication_authors_identity`).

**BR-10 (Account status)** User status ∈ {active, inactive, suspended}; inactive/suspended accounts are forbidden from authenticated operations.

**BR-11 (One university per deployment)** Although the schema supports multiple universities, a deployment serves one university instance at a time (operational constraint, not enforced in code).

## 11. Important workflows

**W1 — Research proposal lifecycle**
1. Staff/student creates a research topic (linked to a department).
2. User submits a research proposal (status `draft`, initial status history written in the same transaction).
3. Proposal moves through `submitted → under_review → revision_requested → approved/rejected/withdrawn` via status transitions, each recorded in `proposal_status_history`.
4. An approved proposal becomes a `research_project` (one-to-one via `proposal_id` unique constraint).

**W2 — Project execution & monitoring**
1. Project created with milestones (from templates or ad hoc), supervisors, and participants.
2. Students submit progress reports per period; reviewers approve/reject/request revision.
3. Project status transitions (`active → on_hold → completed/cancelled/archived`) recorded in `project_status_history`.

**W3 — Grant lifecycle**
1. Grant admin creates a funding opportunity (open/closed/awarded/cancelled).
2. Applicant submits an application (linked optionally to a project).
3. Application reviewed; an award is created from an approved application (unique award per application).
4. Expenditures recorded against awards; grant progress reports submitted per period; project allocations link awards to projects.

**W4 — Publication workflow**
1. Publication submitted (status `draft`) with authors (internal or external) and linked projects.
2. Publication moves through verification (`submitted → under_verification → verified/rejected/withdrawn`).
3. Reviews record verification decisions.

**W5 — Approval workflow**
1. Workflow definition created with versions and steps (each step requires a role and number of approvals).
2. Workflow instance initiated against a target entity; approval actions recorded per step.

**W6 — User administration**
1. University admin creates users, roles, permissions.
2. Roles assigned to users within a university; permissions assigned to roles.
3. Self-access to own profile is always allowed; cross-user access requires `university_admin`.

## 12. System boundaries

- **In scope:** Backend REST API (`/api/v1`), PostgreSQL database, Alembic migrations, structured error handling, authentication (bearer token or `X-User-Id`), tenant isolation via `X-University-ID`.
- **Out of scope:** Frontend/UI, mobile clients, email/SMS delivery, file storage backend, OAuth/SSO, scheduled jobs/cron, search indexing, reporting/analytics exports, multi-region deployment.
- **External integrations:** None implemented. Stored files track metadata only (`storage_key`); no storage provider integration.

## 13. Out-of-scope functionality

The following are explicitly out of scope for the current release:
- Frontend application of any kind.
- Soft deletion (hard deletes with DB RESTRICT constraints, guarded by service-level checks, only).
- Real-time notifications, email, or push channels.
- Third-party identity providers.
- Scheduled background jobs.

## 14. Future improvements

See section 8.2 (proposed improvements) plus:
- API versioning strategy beyond `/api/v1`.
- Rate limiting and request throttling.
- OpenAPI client SDK generation.
- Database read replicas / connection pooling tuning.

---

**Conventions used in this document:** "Implemented" = present in code and covered by tests; "Partially implemented" = present but limited in scope; "Not implemented" = absent / intentional exclusion; "Unknown" = cannot be confirmed from the codebase.

**Related documents:** `AGENTS.md`, `docs/architecture/ARCHITECTURE.md`, `docs/product/USER_ROLES.md`, `docs/product/FEATURES.md`, `docs/product/WORKFLOWS.md`, `COMPLETION_REPORT.md`.
