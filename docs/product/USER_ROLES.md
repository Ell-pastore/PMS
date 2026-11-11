# PMS User Roles and Permissions

## Overview

PMS uses role-based access control (RBAC) for global administrative operations, combined with multi-tenant isolation for all domain operations. Roles are assigned to users within a specific university context.

## Role Model

| Table | Purpose |
|-------|---------|
| `roles` | Role definitions (id, code, name, description, is_active) |
| `user_roles` | Assigns a role to a user within a university (composite FK to `university_memberships`) |
| `permissions` | Permission definitions (id, code, description, is_active) |
| `role_permissions` | Junction table linking roles to permissions (role_id, permission_id) |

## Seeded Role Codes

Defined in `backend/app/models/seed.py` (`INITIAL_ROLE_CODES`). These are reference data and must be explicitly seeded via `seed_initial_roles(session)` — the helper is **not** called automatically on application startup.

| Role Code | Name | Typical Responsibilities |
|-----------|------|-------------------------|
| `student` | Student | Enrolled researcher; creates proposals, participates in projects, submits progress reports |
| `supervisor` | Supervisor | Academic staff; reviews proposals, supervises projects, approves milestones |
| `department_head` | Department Head | Manages departments, oversees departmental research activity |
| `research_admin` | Research Admin | Manages research topics, approval workflows, audit logs, retention policies |
| `grant_admin` | Grant Admin | Creates grant opportunities, reviews applications, issues awards |
| `university_admin` | University Admin | Top-level administrator; manages users, roles, permissions, universities, memberships, settings |
| `superadmin` | Superadmin | Cross-tenant bypass for role checks; must be manually assigned |

## Special Roles

### superadmin

- Referenced in `backend/app/core/dependencies.py` as a bypass for `require_roles()` checks.
- `TenantContext.has_role()` returns `True` if `"superadmin"` is in the user's roles.
- Seeded with the other reference roles (part of `INITIAL_ROLE_CODES`), but seeding grants it to no one — it takes effect only once manually assigned to a user.
- Still requires tenant context (`get_tenant_context`) for university-scoped operations.

## Role Assignment

Roles are assigned through the User Roles (Tenant) API (`/api/v1/user-roles`). All mutation endpoints require `university_admin` (or `superadmin`):

- `POST /user-roles` — Assign a role to a user within a university (201; `university_admin`).
- `GET /user-roles` — List user roles (paginated; filter by `user_id`, `role_id`, `active_only`).
- `POST /user-roles/{user_role_id}/revoke` — Revoke a user role (200; `university_admin`).
- `DELETE /user-roles/{user_role_id}` — Delete a user role assignment (200; `university_admin`).

### Constraints

- The user must have an active `UniversityMembership` in the target university.
- The assigner (if provided) must also have an active membership in that university.
- A user cannot have the same role actively assigned twice in the same university (partial unique index on `revoked_at IS NULL`).
- Revoking sets `revoked_at` rather than hard-deleting (soft revoke).

## Permission Model

Permissions are defined in the `permissions` table and linked to roles via `role_permissions`. Permission CRUD and role-permission assignment are restricted to `university_admin`:

- `POST /roles/permissions` — Create permission (201).
- `GET /roles/permissions` — List permissions (paginated).
- `POST /roles/permissions/assign` — Assign permission to role (201).
- `DELETE /roles/permissions/assignments/{assignment_id}` — Remove assignment (200).

## Authorization Enforcement

### Route-Level RBAC (`require_roles`)

Global administrative routes require the `university_admin` role:

| Route Group | Required Role |
|-------------|--------------|
| `GET /users` (list), `DELETE /users/{id}` | `university_admin` |
| `POST/GET/PUT/DELETE /roles` | `university_admin` |
| `POST/GET /roles/permissions` | `university_admin` |
| `POST/DELETE /roles/permissions/assign...` | `university_admin` |
| `POST/GET/PUT/DELETE /universities` | `university_admin` |
| `POST/PATCH/PUT/DELETE /university-memberships` | `university_admin` |
| `PATCH/PUT /settings/university`, `/settings/departments/{id}`, `POST/PATCH/DELETE /settings/system` | `university_admin` |
| `POST/POST revoke/DELETE /user-roles` | `university_admin` |

### Self-Access Exception

`GET/PATCH /users/{user_id}` allows a user to access their own profile without the `university_admin` role. Accessing another user's profile requires `university_admin`.

### Domain-Level Authorization

Mutations on organizational and administrative domain routes are gated by the matching domain role (any listed role passes; `superadmin` passes all):

| Domain | Mutation Routes | Required Roles |
|--------|----------------|----------------|
| Faculties | `POST/PATCH/PUT/DELETE /faculties` | `university_admin` |
| Departments | `POST/PATCH/PUT/DELETE /departments` | `department_head`, `university_admin` |
| Department leadership | `POST .../end/DELETE /department-leadership` | `department_head`, `university_admin` |
| Research topics | `POST/PATCH/PUT/DELETE /research-topics` | `research_admin`, `university_admin` |
| Duplicate-candidate review | `POST /duplicate-topic-candidates/{id}/review` | `research_admin`, `university_admin` |
| Approval workflows/versions/steps | `POST/PATCH/PUT/DELETE` on workflows, versions, steps, publish | `research_admin`, `university_admin` |
| Audit logs | `POST/PATCH/PUT/DELETE /audit-logs` | `research_admin`, `university_admin` |
| Retention policies | `POST/PATCH/DELETE /retention-policies` | `research_admin`, `university_admin` |
| Milestone templates | `POST/PATCH/PUT/DELETE /milestone-templates` | `research_admin`, `university_admin` |
| Grant opportunities | `POST/PATCH/PUT/DELETE /grant-opportunities` | `grant_admin`, `university_admin` |
| Grant awards | `POST/PATCH/PUT/DELETE /grant-awards` | `grant_admin`, `university_admin` |
| Grant allocations | `POST/DELETE /grant-awards/{id}/allocations...` | `grant_admin`, `university_admin` |
| Grant expenditures | `POST/PATCH/PUT/DELETE` on expenditures | `grant_admin`, `university_admin` |

Collaborative research work stays open to any active member (tenant isolation only): proposals, revisions, participants, supervisors, reviews, projects, milestones, progress reports, publications, comments, notifications, preferences, alert rules/events, grant applications (apply/submit/participants/reviews), stored files, document attachments, and staff/student profiles. Reads on all domain routes stay open to members.

- Every query is filtered by `tenant.university_id`.
- Cross-tenant access returns 404 (existence not leaked).
- Deleting entities with dependent data returns 400 `SpecializedOperationError` (see `FEATURES.md`).

## Access Matrix

| Operation | student | supervisor | department_head | research_admin | grant_admin | university_admin | superadmin |
|-----------|---------|------------|-----------------|----------------|-------------|------------------|------------|
| Create proposal | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create project | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create milestone / progress report | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create publication | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Apply for a grant | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create faculty | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create department | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Appoint department leadership | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Create research topic | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Create milestone template | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Manage approval workflows / versions / steps | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Manage audit logs / retention policies | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Create grant opportunity | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Create grant award / allocation / expenditure | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Create role | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create permission | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Assign / revoke user roles | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create university | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage memberships / settings | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| List users | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Access own profile | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Access another user's profile | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cross-tenant access | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ (bypass) |

## Related Documents

- [`AGENTS.md`](../AGENTS.md) — Authorization rules
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Authorization architecture
- [`SECURITY.md`](SECURITY.md) — Authorization and multi-tenancy
- [`PRD.md`](../PRD.md) — User roles and permissions section
