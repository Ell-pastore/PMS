# PMS Features

## Overview

PMS is a backend-only API for managing university research activities. Features are organized by domain. All features enforce multi-tenant isolation — every resource is scoped to a `university_id`, and cross-tenant access returns 404.

## Feature Categories

### 1. Users & Authentication

| Feature | Description | Status |
|---------|-------------|--------|
| User registration | Create a new account with email, full name, password | Implemented |
| User login | Authenticate via email/password; receive an access token | Implemented |
| Current user profile | `GET /auth/me` returns the authenticated user's profile | Implemented |
| Password hashing | PBKDF2-HMAC-SHA256, 100k iterations | Implemented |
| Token auth | Custom HMAC-SHA256 JWT-compatible tokens, 24-hour expiry | Implemented |
| Account status | active/inactive/suspended; inactive users rejected | Implemented |
| Email verification | `AccountVerification` model with token digest and expiry | Implemented (model + schema only) |
| User CRUD | Create, read, update, delete users (admin-restricted for list/delete) | Implemented |
| User pagination | List users with `page`, `page_size`, `total`, `total_pages` | Implemented |
| User search | Filter by name or email | Implemented |
| User status filter | Filter by active/inactive/suspended | Implemented |

### 2. Roles & Permissions

| Feature | Description | Status |
|---------|-------------|--------|
| Role CRUD | Create, read, update, delete roles (admin-restricted) | Implemented |
| Permission CRUD | Create, read permissions (admin-restricted) | Implemented |
| Role-permission assignment | Assign/remove permissions to/from roles | Implemented |
| Seeded role codes | student, supervisor, department_head, research_admin, grant_admin, university_admin | Defined in `seed.py` |
| `superadmin` bypass | Referenced in code but not seeded | Referenced only |

### 3. User Roles (Tenant)

| Feature | Description | Status |
|---------|-------------|--------|
| Role assignment | Assign a role to a user within a university | Implemented |
| Role revocation | Revoke (soft) or delete a user role assignment | Implemented |
| Role listing | List user roles with pagination; filter by user, role, active | Implemented |
| Membership validation | User must have active membership in the target university | Implemented |

### 4. Universities

| Feature | Description | Status |
|---------|-------------|--------|
| University CRUD | Create, read, update, delete universities (admin-restricted) | Implemented |
| University pagination | List with search and is_active filter | Implemented |
| University settings | Key-value JSON settings per university | Implemented |
| Department settings | Per-department configuration overrides | Implemented |

### 5. University Memberships

| Feature | Description | Status |
|---------|-------------|--------|
| Membership CRUD | Add, read, update, delete user-university affiliations | Implemented |
| Membership listing | Filter by user_id, is_active | Implemented |

### 6. Organization

| Feature | Description | Status |
|---------|-------------|--------|
| Faculty CRUD | Create, read, update, delete faculties | Implemented |
| Department CRUD | Create, read, update, delete departments | Implemented |
| Department leadership | Appoint/end department heads (one active leader per department) | Implemented |
| Staff profiles | Create, read, update, delete staff profiles | Implemented |
| Student profiles | Create, read, update, delete student profiles | Implemented |
| Delete guards | Faculty blocked if departments exist; department blocked if referenced | Implemented (4 domains) |

### 7. Research Topics

| Feature | Description | Status |
|---------|-------------|--------|
| Topic CRUD | Create, read, update, delete research topics | Implemented |
| Topic listing | Filter by department, search, is_active | Implemented |
| Duplicate detection | Normalized title matching for duplicate topic candidates | Implemented |
| Duplicate candidates | Create, review, list, delete candidate pairs | Implemented |
| Delete guard | Blocked if proposals reference the topic | Implemented |

### 8. Research Proposals

| Feature | Description | Status |
|---------|-------------|--------|
| Proposal CRUD | Create, read, update, delete proposals | Implemented |
| Proposal lifecycle | draft → submitted → under_review → revision_requested → approved/rejected/withdrawn | Implemented |
| Proposal submission | Submit a draft proposal (sets submitted_at) | Implemented |
| Status transitions | Admin-controlled status changes with history tracking | Implemented |
| Proposal filters | department_id, topic_id, submitting_user_id, status, search | Implemented |
| Proposal pagination | Standard paginated envelope | Implemented |
| Participants | Add/remove student participants; one lead per proposal | Implemented |
| Supervisors | Assign/end staff supervisors; one primary per proposal | Implemented |
| Revisions | Create numbered revisions; updates proposal content | Implemented |
| Reviews | Add reviews with decision (approved/rejected/revision_requested/commented) | Implemented |
| Status history | Track all status changes with actor and reason | Implemented |
| Delete guard | Only draft proposals can be deleted | Implemented |

### 9. Research Projects

| Feature | Description | Status |
|---------|-------------|--------|
| Project CRUD | Create, read, update, delete projects | Implemented |
| Project creation | From an approved proposal; one project per proposal (unique constraint) | Implemented |
| Project statuses | active, on_hold, completed, cancelled, archived | Implemented |
| Status transitions | With history tracking | Implemented |
| Project filters | department_id, proposal_id, status, search | Implemented |
| Project pagination | Standard paginated envelope | Implemented |
| Milestones | Create, track sequence numbers, due dates, completion | Implemented |
| Milestone templates | Reusable templates per department | Implemented |
| Participants | Add/remove student participants; one lead per project | Implemented |
| Supervisors | Assign/end staff supervisors; one primary per project | Implemented |
| Status history | Track all status changes | Implemented |

### 10. Progress Reports & Activity

| Feature | Description | Status |
|---------|-------------|--------|
| Progress reports | Create, read, update, delete project progress reports | Implemented |
| Report statuses | draft, submitted, under_review, revision_requested, approved, rejected | Implemented |
| Project comments | Comment on projects, milestones, or reports | Implemented |
| Student activity | Record student activity events with metadata | Implemented |
| Report reviews | Review reports with decision and feedback | Implemented |

### 11. Grants

| Feature | Description | Status |
|---------|-------------|--------|
| Grant opportunities | Create, read, update, delete funding opportunities | Implemented |
| Opportunity statuses | draft, open, closed, awarded, cancelled | Implemented |
| Grant applications | Create, read, update, delete applications | Implemented |
| Application statuses | draft, submitted, under_review, approved, rejected, withdrawn | Implemented |
| Application submission | Submit draft application | Implemented |
| Application reviews | Review with decision and recommended amount | Implemented |
| Grant awards | Create awards (one per application; unique award reference) | Implemented |
| Award statuses | active, closed, cancelled | Implemented |
| Award filters | application_id, status, search | Implemented |
| Grant allocations | Allocate award funds to projects | Implemented |
| Grant expenditures | Record expenditures against awards | Implemented |
| Expenditure statuses | draft, submitted, approved, rejected, paid, voided | Implemented |
| Grant progress reports | Reports against awards with period and financial summary | Implemented |
| Delete guard | Opportunity blocked if applications exist | Implemented |

### 12. Publications

| Feature | Description | Status |
|---------|-------------|--------|
| Publication CRUD | Create, read, update, delete publications | Implemented |
| Publication types | journal, conference, etc. (free text) | Implemented |
| Verification workflow | draft → submitted → under_verification → verified/rejected/withdrawn | Implemented |
| DOI tracking | doi and normalized_doi (unique when present) | Implemented |
| Publication authors | Internal users or external author names | Implemented |
| Publication-project links | Link publications to research projects | Implemented |
| Publication reviews | Review with decision (verified/rejected/revision_requested/commented) | Implemented |

### 13. Approvals

| Feature | Description | Status |
|---------|-------------|--------|
| Approval workflows | Create versioned workflows per type and department scope | Implemented |
| Workflow versions | Draft → published (immutable once published) | Implemented |
| Workflow steps | Numbered steps with required role and approval count | Implemented |
| Approval instances | Create instances targeting entities | Implemented |
| Approval actions | Record step decisions; track instance completion | Implemented |
| Immutability | Published versions cannot be modified (ORM event guard) | Implemented |

### 14. Notifications & Alerts

| Feature | Description | Status |
|---------|-------------|--------|
| Notifications | Create, read, update, delete notifications per recipient | Implemented |
| Notification preferences | Per user, type, channel (in_app), enabled flag | Implemented |
| Alert rules | Define rule types and thresholds | Implemented |
| Alert events | Track detected alerts with severity and status | Implemented |
| Notification delivery | ❌ Not implemented — preferences stored, no delivery provider | Planned |

### 15. Files, Audit & Retention

| Feature | Description | Status |
|---------|-------------|--------|
| Stored files | File metadata (storage key, filename, content type, size, checksum) | Implemented |
| Document attachments | Attach files to proposals, projects, reports, or grant applications | Implemented |
| Audit logs | Log system actions with entity references | Implemented |
| Retention policies | Define retention periods and post-retention actions per category | Implemented |

## Feature Status Summary

| Category | Implemented | Partially Implemented | Not Implemented |
|----------|-------------|----------------------|-----------------|
| Users & Auth | ✅ | Email verification | — |
| Roles & Permissions | ✅ | — | superadmin seeding |
| User Roles (Tenant) | ✅ | — | — |
| Universities | ✅ | — | — |
| Organization | ✅ | — | — |
| Research Topics | ✅ | — | — |
| Research Proposals | ✅ | — | — |
| Research Projects | ✅ | — | — |
| Progress Reports | ✅ | — | — |
| Grants | ✅ | — | — |
| Publications | ✅ | — | — |
| Approvals | ✅ | — | — |
| Notifications & Alerts | ✅ | Notification delivery | — |
| Files, Audit & Retention | ✅ | — | — |

## Related Documents

- [`PRD.md`](../PRD.md) — Product requirements and objectives
- [`WORKFLOWS.md`](WORKFLOWS.md) — Detailed workflows
- [`USER_ROLES.md`](USER_ROLES.md) — Roles and permissions
- [`API.md`](API.md) — API endpoint reference
- [`AGENTS.md`](../AGENTS.md) — API development conventions
